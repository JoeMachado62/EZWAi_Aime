/**
 * Update SIP Trunk with correct phone number
 */

import * as crypto from 'node:crypto';
import * as https from 'node:https';
import * as http from 'node:http';
import dotenv from 'dotenv';

dotenv.config();

const LIVEKIT_URL = process.env.LIVEKIT_URL || '';
const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || '';
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || '';
const LIVEKIT_SIP_TRUNK_ID = process.env.LIVEKIT_SIP_TRUNK_ID || '';
const CORRECT_PHONE_NUMBER = '+13059521569'; // The correct phone number

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
  console.log('🔧 Updating SIP Trunk phone number...\n');
  console.log(`📞 Trunk ID: ${LIVEKIT_SIP_TRUNK_ID}`);
  console.log(`📞 New Phone Number: ${CORRECT_PHONE_NUMBER}\n`);

  const httpUrl = LIVEKIT_URL.replace('wss://', 'https://').replace('ws://', 'http://');
  const token = generateLiveKitToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, { roomCreate: true });

  // First, get the current trunk configuration
  console.log('1️⃣ Getting current trunk configuration...');
  const listUrl = `${httpUrl}/twirp/livekit.SIP/ListSIPTrunk`;
  const listResponse = await postJSON(listUrl, {}, token);

  if (listResponse.status >= 400) {
    console.error('❌ Failed to list trunks:', listResponse.data);
    process.exit(1);
  }

  const currentTrunk = listResponse.data.items.find(t => t.sip_trunk_id === LIVEKIT_SIP_TRUNK_ID);

  if (!currentTrunk) {
    console.error(`❌ Trunk ${LIVEKIT_SIP_TRUNK_ID} not found`);
    process.exit(1);
  }

  console.log(`   Current outbound number: ${currentTrunk.outbound_number}`);
  console.log(`   Current name: ${currentTrunk.name}`);

  // Update the trunk with correct phone number
  console.log('\n2️⃣ Updating trunk with correct phone number...');

  const updatePayload = {
    sip_trunk_id: LIVEKIT_SIP_TRUNK_ID,
    name: currentTrunk.name,
    metadata: currentTrunk.metadata || '',
    outbound_address: currentTrunk.outbound_address,
    outbound_username: currentTrunk.outbound_username || '',
    outbound_password: currentTrunk.outbound_password || '',
    outbound_number: CORRECT_PHONE_NUMBER,  // Update this!
    inbound_addresses: currentTrunk.inbound_addresses || [],
    inbound_numbers_regex: currentTrunk.inbound_numbers_regex || [],
    inbound_username: currentTrunk.inbound_username || '',
    inbound_password: currentTrunk.inbound_password || '',
    headers: currentTrunk.headers || {},
    headers_to_attributes: currentTrunk.headers_to_attributes || {},
    krisp_enabled: currentTrunk.krisp_enabled || false,
    ringing_timeout: currentTrunk.ringing_timeout || 0,
    max_call_duration: currentTrunk.max_call_duration || 0,
  };

  const updateUrl = `${httpUrl}/twirp/livekit.SIP/UpdateSIPTrunk`;
  const updateResponse = await postJSON(updateUrl, updatePayload, token);

  if (updateResponse.status >= 400) {
    console.error('❌ Failed to update trunk:', updateResponse.data);
    process.exit(1);
  }

  console.log('✅ Trunk updated successfully!');
  console.log('\n3️⃣ Verifying update...');

  const verifyResponse = await postJSON(listUrl, {}, token);
  const updatedTrunk = verifyResponse.data.items.find(t => t.sip_trunk_id === LIVEKIT_SIP_TRUNK_ID);

  console.log(`   ✅ Outbound number: ${updatedTrunk.outbound_number}`);
  console.log(`   ✅ Trunk ID: ${updatedTrunk.sip_trunk_id}`);
  console.log(`   ✅ Name: ${updatedTrunk.name}`);

  console.log('\n🎉 Phone number successfully updated!');
  console.log('\n📝 Summary:');
  console.log(`   Old: 13059531569`);
  console.log(`   New: ${CORRECT_PHONE_NUMBER}`);
  console.log('\n💡 Your outbound calls will now use the correct phone number!');
}

main().catch((error) => {
  console.error('❌ Error:', error);
  process.exit(1);
});
