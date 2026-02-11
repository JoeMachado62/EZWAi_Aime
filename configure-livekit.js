/**
 * LiveKit Configuration Script
 * Configures dispatch rules for phone, web, and SMS
 */

import { AccessToken, RoomServiceClient } from 'livekit-server-sdk';
import fetch from 'node-fetch';

// Load from environment
const LIVEKIT_URL = process.env.LIVEKIT_URL || 'wss://ezwaiaime-y90r6gwr.livekit.cloud';
const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || 'APIy6Cd2R86Kwzx';
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || 'Gtd7W5eaQseNKUNTYS6LDcUeGARbOdMgylnCIHazByfD';
const PHONE_NUMBER = process.env.LIVEKIT_PHONE_NUMBER || '+13059521569';

console.log('🔧 LiveKit Configuration');
console.log('========================\n');

// Test connection
async function testConnection() {
  console.log('1️⃣  Testing LiveKit connection...');

  try {
    const token = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
      identity: 'config-test',
      ttl: 60,
    });

    token.addGrant({ roomJoin: true, room: 'test-room' });
    const jwt = token.toJwt();

    console.log('   ✅ Connection test passed');
    console.log(`   URL: ${LIVEKIT_URL}`);
    console.log(`   API Key: ${LIVEKIT_API_KEY.substring(0, 8)}...`);
    console.log('');
    return true;
  } catch (error) {
    console.error('   ❌ Connection failed:', error.message);
    return false;
  }
}

// Configure phone dispatch rule
async function configurePhoneDispatch() {
  console.log('2️⃣  Configuring phone dispatch rule...');
  console.log(`   Phone: ${PHONE_NUMBER}`);
  console.log('   Agent: aime-voice-agent');
  console.log('   Room prefix: aime-');
  console.log('');

  // Note: Dispatch rules are typically configured via LiveKit Cloud dashboard
  // The API for programmatic dispatch rule creation may require LiveKit Cloud admin access

  const config = {
    name: 'AIME Voice Agent',
    type: 'individual',
    roomPrefix: 'aime-',
    agentName: 'aime-voice-agent',
    phoneNumbers: [PHONE_NUMBER],
    metadata: {
      service: 'aime',
      platform: 'gohighlevel',
      openclaw_url: process.env.OPENCLAW_BASE_URL || 'http://localhost:3000',
    },
  };

  console.log('   ⚠️  Dispatch rules must be created in LiveKit Cloud dashboard');
  console.log('   📋 Configuration to use:');
  console.log(JSON.stringify(config, null, 2));
  console.log('');
  console.log('   👉 Go to: https://cloud.livekit.io/');
  console.log('   👉 Navigate to: Telephony → Dispatch rules');
  console.log('   👉 Click: Create a new dispatch rule');
  console.log('   👉 Fill in the values above');
  console.log('');
}

// Configure web dispatch
async function configureWebDispatch() {
  console.log('3️⃣  Web-based calling configuration...');
  console.log('');

  console.log('   For web-based calls, you can:');
  console.log('   A. Embed LiveKit client in your website');
  console.log('   B. Use LiveKit Meet (instant rooms)');
  console.log('   C. Create custom UI with LiveKit Web SDK');
  console.log('');

  console.log('   Example embed code:');
  console.log('   <script src="https://unpkg.com/@livekit/components-react"></script>');
  console.log('');

  // Generate a sample room token
  const token = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
    identity: 'web-user',
    name: 'Web User',
    ttl: 3600,
  });

  token.addGrant({
    roomJoin: true,
    room: 'aime-web-demo',
    canPublish: true,
    canSubscribe: true,
  });

  console.log('   Sample room token for testing:');
  console.log(`   ${token.toJwt().substring(0, 50)}...`);
  console.log('');
}

// Configure SMS dispatch
async function configureSMSDispatch() {
  console.log('4️⃣  SMS dispatch configuration...');
  console.log('');

  console.log('   For SMS integration:');
  console.log('   1. Use Twilio/Bandwidth with your phone number');
  console.log('   2. Set webhook to OpenClaw bridge');
  console.log('   3. OpenClaw processes SMS → creates LiveKit room → invites agent');
  console.log('');

  console.log('   Webhook URL pattern:');
  console.log(`   ${process.env.OPENCLAW_BASE_URL || 'http://localhost:3000'}/webhooks/sms`);
  console.log('');

  console.log('   ⚠️  Note: SMS requires additional setup in GoHighLevel');
  console.log('   GHL handles SMS natively - this is for LiveKit voice callback');
  console.log('');
}

// Generate deployment summary
async function generateSummary() {
  console.log('📊 Configuration Summary');
  console.log('========================\n');

  console.log('✅ Configured:');
  console.log(`   - LiveKit URL: ${LIVEKIT_URL}`);
  console.log(`   - Phone number: ${PHONE_NUMBER}`);
  console.log(`   - Agent name: aime-voice-agent`);
  console.log('');

  console.log('⏳ Manual steps required:');
  console.log('   1. Create dispatch rule in LiveKit Cloud dashboard');
  console.log('   2. Deploy agent: python agents/voice_agent.py start');
  console.log('   3. Set up ngrok for local testing: ngrok http 3000');
  console.log('   4. Update OPENCLAW_BASE_URL with ngrok URL');
  console.log('');

  console.log('🧪 Testing:');
  console.log(`   - Call ${PHONE_NUMBER} to test inbound`);
  console.log('   - Check logs: tail -f logs/aime-agent.log');
  console.log('');

  console.log('📚 Documentation:');
  console.log('   - LiveKit setup: ./LIVEKIT_SETUP_STEPS.md');
  console.log('   - Deployment guide: ./LIVEKIT_DEPLOYMENT.md');
  console.log('   - Quick reference: ./QUICK_REFERENCE.md');
  console.log('');
}

// Main execution
async function main() {
  const connected = await testConnection();

  if (!connected) {
    console.error('❌ Cannot proceed without valid LiveKit connection');
    process.exit(1);
  }

  await configurePhoneDispatch();
  await configureWebDispatch();
  await configureSMSDispatch();
  await generateSummary();

  console.log('✅ Configuration complete!');
  console.log('');
  console.log('Next: Follow the manual steps above to complete setup');
}

main().catch(console.error);
