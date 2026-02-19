/**
 * AI-Powered Call Initiator
 * Initiates outbound calls via LiveKit SIP
 */

import * as crypto from 'node:crypto';
import * as https from 'node:https';
import * as http from 'node:http';
import * as fs from 'node:fs';
import * as path from 'node:path';

/**
 * Load .env file manually (no external dependency)
 */
function loadEnvFile(): void {
  // Walk up from current file to find .env
  let dir = typeof __dirname !== 'undefined' ? __dirname : process.cwd();
  for (let i = 0; i < 6; i++) {
    const envPath = path.join(dir, '.env');
    if (fs.existsSync(envPath)) {
      const content = fs.readFileSync(envPath, 'utf8');
      for (const line of content.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx < 0) continue;
        const key = trimmed.slice(0, eqIdx).trim();
        const val = trimmed.slice(eqIdx + 1).trim();
        if (!process.env[key]) {
          process.env[key] = val;
        }
      }
      return;
    }
    dir = path.dirname(dir);
  }
}

interface CallInitiateParams {
  phoneNumber: string;
  contactId?: string;
  purpose: string;
  script?: string;
  contactContext?: unknown;
}

interface CallResult {
  roomName: string;
  sipCallId?: string;
  phoneNumber: string;
  status: string;
}

/**
 * Generate a LiveKit API JWT access token
 */
function generateLiveKitToken(apiKey: string, apiSecret: string, grants: Record<string, unknown>, ttlSeconds = 600): string {
  const header = { alg: 'HS256', typ: 'JWT' };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iss: apiKey,
    sub: apiKey,
    iat: now,
    nbf: now,
    exp: now + ttlSeconds,
    video: grants,
    sip: { admin: true, call: true },
  };

  const encode = (obj: unknown) => Buffer.from(JSON.stringify(obj)).toString('base64url');
  const headerB64 = encode(header);
  const payloadB64 = encode(payload);
  const signature = crypto
    .createHmac('sha256', apiSecret)
    .update(`${headerB64}.${payloadB64}`)
    .digest('base64url');

  return `${headerB64}.${payloadB64}.${signature}`;
}

/**
 * Make an HTTPS POST request (no external dependencies)
 */
function postJSON(url: string, body: unknown, token: string): Promise<{ status: number; data: unknown }> {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const payload = JSON.stringify(body);
    const mod = parsed.protocol === 'https:' ? https : http;

    const req = mod.request(
      {
        hostname: parsed.hostname,
        port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
        path: parsed.pathname + parsed.search,
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload),
          Authorization: `Bearer ${token}`,
        },
      },
      (res) => {
        let data = '';
        res.on('data', (chunk: string) => (data += chunk));
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode ?? 0, data: JSON.parse(data) });
          } catch {
            resolve({ status: res.statusCode ?? 0, data });
          }
        });
      },
    );

    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

export class AICallInitiator {
  private livekitUrl: string;
  private apiKey: string;
  private apiSecret: string;
  private sipTrunkId: string;
  private fromNumber: string;

  constructor() {
    loadEnvFile();
    this.livekitUrl = process.env.LIVEKIT_URL || '';
    this.apiKey = process.env.LIVEKIT_API_KEY || '';
    this.apiSecret = process.env.LIVEKIT_API_SECRET || '';
    this.sipTrunkId = process.env.LIVEKIT_SIP_TRUNK_ID || '';
    this.fromNumber = process.env.LIVEKIT_PHONE_NUMBER || '';

    if (!this.livekitUrl || !this.apiKey || !this.apiSecret || !this.sipTrunkId) {
      console.warn('[AICallInitiator] Missing LiveKit env vars — calls will fail');
    }
  }

  /**
   * Initiate an outbound call via LiveKit SIP.
   *
   * Flow:
   * 1. Create room with agent dispatch → voice agent gets dispatched
   * 2. Voice agent reads metadata, connects, starts session
   * 3. Voice agent creates SIP participant (places the phone call)
   * 4. Person answers → audio flows through the voice agent
   */
  async initiateCall(params: CallInitiateParams): Promise<CallResult> {
    const { phoneNumber, contactId, purpose, script } = params;

    if (!phoneNumber.startsWith('+')) {
      throw new Error('Phone number must be in E.164 format (e.g., +12398881006)');
    }

    if (!this.livekitUrl || !this.apiKey || !this.apiSecret || !this.sipTrunkId) {
      throw new Error('LiveKit SIP not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_SIP_TRUNK_ID');
    }

    // Create unique room name
    const timestamp = Date.now();
    const roomName = `aime-outbound-${contactId || 'unknown'}-${timestamp}`;

    // Build the REST API URL (wss:// → https://)
    const httpUrl = this.livekitUrl.replace('wss://', 'https://').replace('ws://', 'http://');

    // Build metadata — the voice agent reads this to know it's outbound
    const metadata = JSON.stringify({
      contact_id: contactId,
      custom_prompt: script || purpose,
      direction: 'outbound',
      initiated_at: new Date().toISOString(),
      phone_number: phoneNumber,
    });

    // Generate access token
    const token = generateLiveKitToken(this.apiKey, this.apiSecret, {
      roomCreate: true,
      roomJoin: true,
      room: roomName,
      canPublish: true,
      canSubscribe: true,
    });

    console.log(`[AICallInitiator] Creating room ${roomName} with agent dispatch for call to ${phoneNumber}`);

    // Step 1: Create room WITH agent dispatch
    // The voice agent (aime-voice-agent) will be dispatched to this room,
    // read the metadata, and place the SIP call from within the room.
    const createRoomUrl = `${httpUrl}/twirp/livekit.RoomService/CreateRoom`;
    const roomBody = {
      name: roomName,
      metadata,
      empty_timeout: 120,   // auto-delete after 2 min if empty
      max_participants: 3,   // agent + SIP participant + buffer
      agents: [
        {
          agent_name: 'aime-voice-agent',
          metadata,
        },
      ],
    };

    const roomResponse = await postJSON(createRoomUrl, roomBody, token);

    if (roomResponse.status >= 400) {
      const errMsg = typeof roomResponse.data === 'object' && roomResponse.data !== null
        ? JSON.stringify(roomResponse.data)
        : String(roomResponse.data);
      throw new Error(`LiveKit CreateRoom error (${roomResponse.status}): ${errMsg}`);
    }

    console.log(`[AICallInitiator] Room created with agent dispatch: ${roomName}`);
    console.log(`[AICallInitiator] Voice agent will place SIP call to ${phoneNumber} from within room`);

    return {
      roomName,
      phoneNumber,
      status: 'initiated',
    };
  }
}
