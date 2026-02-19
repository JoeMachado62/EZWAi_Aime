/**
 * List all SIP trunks to find the correct trunk ID for phone number +13059521569
 */

import * as crypto from 'node:crypto';
import * as https from 'node:https';
import * as http from 'node:http';
import dotenv from 'dotenv';

dotenv.config();

const LIVEKIT_URL = process.env.LIVEKIT_URL || '';
const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || '';
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || '';

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

async function main() {
  console.log('🔧 Listing SIP Trunks...\n');

  const httpUrl = LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://');
  const token = generateLiveKitToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, { roomCreate: true });

  const listUrl = `${httpUrl}/twirp/livekit.SIP/ListSIPTrunk`;
  const response = await postJSON(listUrl, {}, token);

  if (response.status >= 400) {
    console.error('❌ Failed to list trunks:', response.data);
    process.exit(1);
  }

  console.log('📋 SIP Trunks:\n');
  const trunks = response.data.items || [];

  trunks.forEach((trunk, index) => {
    console.log(`\n${index + 1}. Trunk ID: ${trunk.sip_trunk_id}`);
    console.log(`   Name: ${trunk.name || 'N/A'}`);
    console.log(`   Outbound Number: ${trunk.outbound_number || 'N/A'}`);
    console.log(`   Outbound Address: ${trunk.outbound_address || 'N/A'}`);
    console.log(`   Inbound Numbers: ${trunk.inbound_numbers_regex?.join(', ') || 'N/A'}`);
    console.log(`   Inbound Addresses: ${trunk.inbound_addresses?.join(', ') || 'N/A'}`);
  });

  console.log('\n\n📞 Looking for trunk with phone number +13059521569...');
  const matchingTrunk = trunks.find(t =>
    t.outbound_number === '+13059521569' ||
    t.inbound_numbers_regex?.some(regex => regex.includes('13059521569'))
  );

  if (matchingTrunk) {
    console.log('\n✅ Found matching trunk!');
    console.log(`   Trunk ID: ${matchingTrunk.sip_trunk_id}`);
    console.log('\n💡 Update your .env file:');
    console.log(`   LIVEKIT_SIP_TRUNK_ID=${matchingTrunk.sip_trunk_id}`);
  } else {
    console.log('\n⚠️  No trunk found with phone number +13059521569');
    console.log('   You may need to create or update a trunk in LiveKit Cloud dashboard');
  }
}

main().catch((error) => {
  console.error('❌ Error:', error);
  process.exit(1);
});
