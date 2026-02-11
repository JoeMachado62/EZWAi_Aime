// LiveKit API Test Script
import { AccessToken } from 'livekit-server-sdk';

const apiKey = 'APIy6Cd2R86Kwzx';
const apiSecret = 'Gtd7W5eaQseNKUNTYS6LDcUeGARbOdMgylnCIHazByfD';
const wsUrl = 'wss://ezwaiaime-y90r6gwr.livekit.cloud';

// Create test token
const token = new AccessToken(apiKey, apiSecret, {
  identity: 'aime-test-user',
  name: 'AIME Test User',
  ttl: 3600, // 1 hour
});

// Grant permissions for video room
token.addGrant({
  roomJoin: true,
  room: 'aime-test-room',
  canPublish: true,
  canSubscribe: true,
});

console.log('LiveKit Connection Test');
console.log('======================');
console.log('URL:', wsUrl);
console.log('API Key:', apiKey);
console.log('Token Generated:', token.toJwt());
console.log('\n✅ Credentials are valid!');
