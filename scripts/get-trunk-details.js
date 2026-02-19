/**
 * Get detailed trunk configuration
 */

import * as crypto from 'node:crypto';
import * as https from 'node:https';
import dotenv from 'dotenv';

dotenv.config();

const LIVEKIT_URL = process.env.LIVEKIT_URL || '';
const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || '';
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || '';
const TRUNK_ID = 'ST_fR8Ls9A2GRtW';  // Inbound trunk

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

function postJSON(url, body, token) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const payload = JSON.stringify(body);

    const req = https.request(
      {
        hostname: parsed.hostname,
        port: parsed.port || 443,
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

async function main() {
  console.log('🔍 Getting trunk details...\n');

  const httpUrl = LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://');
  const token = generateLiveKitToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET);

  const listUrl = `${httpUrl}/twirp/livekit.SIP/ListSIPTrunk`;
  const response = await postJSON(listUrl, {}, token);

  if (response.status >= 400) {
    console.error('❌ Failed to list trunks:', response.data);
    process.exit(1);
  }

  const trunk = response.data.items.find(t => t.sip_trunk_id === TRUNK_ID);

  if (!trunk) {
    console.error(`❌ Trunk ${TRUNK_ID} not found`);
    process.exit(1);
  }

  console.log('📋 Current Trunk Configuration:\n');
  console.log(JSON.stringify(trunk, null, 2));

  console.log('\n\n🔑 Key Fields:');
  console.log(`   Trunk ID: ${trunk.sip_trunk_id}`);
  console.log(`   Name: ${trunk.name}`);
  console.log(`   Outbound Number: ${trunk.outbound_number || 'N/A'}`);
  console.log(`   Inbound Numbers Regex: ${trunk.inbound_numbers_regex || 'N/A'}`);
  console.log(`   Inbound Addresses: ${trunk.inbound_addresses || 'N/A'}`);
}

main().catch((error) => {
  console.error('❌ Error:', error);
  process.exit(1);
});
