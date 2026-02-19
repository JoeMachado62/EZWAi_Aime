/**
 * Configure LiveKit SIP Dispatch Rules
 * This script sets up dispatch rules to route incoming/outbound SIP calls to the voice agent
 */

import * as crypto from 'node:crypto';
import * as https from 'node:https';
import * as http from 'node:http';

// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

const LIVEKIT_URL = process.env.LIVEKIT_URL || '';
const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || '';
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || '';
const LIVEKIT_SIP_TRUNK_ID = process.env.LIVEKIT_SIP_TRUNK_ID || '';
const LIVEKIT_PHONE_NUMBER = process.env.LIVEKIT_PHONE_NUMBER || '';

if (!LIVEKIT_URL || !LIVEKIT_API_KEY || !LIVEKIT_API_SECRET || !LIVEKIT_SIP_TRUNK_ID) {
  console.error('Missing required environment variables');
  process.exit(1);
}

/**
 * Generate a LiveKit API JWT access token
 */
function generateLiveKitToken(apiKey, apiSecret, grants = {}, ttlSeconds = 600) {
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

  const encode = (obj) => Buffer.from(JSON.stringify(obj)).toString('base64url');
  const headerB64 = encode(header);
  const payloadB64 = encode(payload);
  const signature = crypto
    .createHmac('sha256', apiSecret)
    .update(`${headerB64}.${payloadB64}`)
    .digest('base64url');

  return `${headerB64}.${payloadB64}.${signature}`;
}

/**
 * Make an HTTPS POST request
 */
function postJSON(url, body, token) {
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
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, data: JSON.parse(data) });
          } catch {
            resolve({ status: res.statusCode, data });
          }
        });
      },
    );

    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

/**
 * Make an HTTPS GET request
 */
function getJSON(url, token) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const mod = parsed.protocol === 'https:' ? https : http;

    const req = mod.request(
      {
        hostname: parsed.hostname,
        port: parsed.port || (parsed.protocol === 'https:' ? 443 : 80),
        path: parsed.pathname + parsed.search,
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, data: JSON.parse(data) });
          } catch {
            resolve({ status: res.statusCode, data });
          }
        });
      },
    );

    req.on('error', reject);
    req.end();
  });
}

async function main() {
  console.log('🔧 Configuring LiveKit SIP Dispatch Rules...\n');
  console.log(`📞 Phone Number: ${LIVEKIT_PHONE_NUMBER}`);
  console.log(`🔗 SIP Trunk ID: ${LIVEKIT_SIP_TRUNK_ID}`);
  console.log(`🌐 LiveKit URL: ${LIVEKIT_URL}\n`);

  const httpUrl = LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://');
  const token = generateLiveKitToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, { roomCreate: true });

  // Step 1: List existing dispatch rules
  console.log('📋 Listing existing dispatch rules...');
  const listUrl = `${httpUrl}/twirp/livekit.SIP/ListSIPDispatchRule`;
  const listResponse = await postJSON(listUrl, {}, token);

  if (listResponse.status >= 400) {
    console.error('❌ Failed to list dispatch rules:', listResponse.data);
  } else {
    console.log('✅ Current dispatch rules:', JSON.stringify(listResponse.data, null, 2));
  }

  // Step 2: Create inbound dispatch rule (for receiving calls)
  console.log('\n📥 Creating inbound dispatch rule...');
  const inboundRule = {
    rule: {
      name: 'aime-inbound-calls',
      trunk_ids: [LIVEKIT_SIP_TRUNK_ID],
      rule: {
        dispatchRuleIndividual: {
          room_prefix: 'aime-inbound-',
          pin: '',
        },
      },
      attributes: {
        agent_name: 'aime-voice-agent',
        dispatch_type: 'inbound',
      },
    },
  };

  const createInboundUrl = `${httpUrl}/twirp/livekit.SIP/CreateSIPDispatchRule`;
  const inboundResponse = await postJSON(createInboundUrl, inboundRule, token);

  if (inboundResponse.status >= 400) {
    if (inboundResponse.data?.msg?.includes('already exists')) {
      console.log('⚠️  Inbound rule already exists');
    } else {
      console.error('❌ Failed to create inbound rule:', inboundResponse.data);
    }
  } else {
    console.log('✅ Inbound dispatch rule created successfully');
  }

  // Step 3: Create outbound dispatch rule (for making calls)
  console.log('\n📤 Creating outbound dispatch rule...');
  const outboundRule = {
    rule: {
      name: 'aime-outbound-calls',
      trunk_ids: [LIVEKIT_SIP_TRUNK_ID],
      rule: {
        dispatchRuleIndividual: {
          room_prefix: 'aime-outbound-',
          pin: '',
        },
      },
      attributes: {
        agent_name: 'aime-voice-agent',
        dispatch_type: 'outbound',
      },
    },
  };

  const createOutboundUrl = `${httpUrl}/twirp/livekit.SIP/CreateSIPDispatchRule`;
  const outboundResponse = await postJSON(createOutboundUrl, outboundRule, token);

  if (outboundResponse.status >= 400) {
    if (outboundResponse.data?.msg?.includes('already exists')) {
      console.log('⚠️  Outbound rule already exists');
    } else {
      console.error('❌ Failed to create outbound rule:', outboundResponse.data);
    }
  } else {
    console.log('✅ Outbound dispatch rule created successfully');
  }

  // Step 4: List dispatch rules again to confirm
  console.log('\n📋 Final dispatch rules:');
  const finalListResponse = await postJSON(listUrl, {}, token);

  if (finalListResponse.status >= 400) {
    console.error('❌ Failed to list dispatch rules:', finalListResponse.data);
  } else {
    console.log(JSON.stringify(finalListResponse.data, null, 2));
  }

  console.log('\n✅ SIP dispatch configuration complete!');
  console.log('\n📝 Summary:');
  console.log('  - Phone number:', LIVEKIT_PHONE_NUMBER);
  console.log('  - SIP Trunk ID:', LIVEKIT_SIP_TRUNK_ID);
  console.log('  - Agent Name: aime-voice-agent');
  console.log('  - Inbound calls will route to rooms: aime-inbound-*');
  console.log('  - Outbound calls will route to rooms: aime-outbound-*');
}

main().catch((error) => {
  console.error('❌ Error:', error);
  process.exit(1);
});
