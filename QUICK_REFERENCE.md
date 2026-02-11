# AIME Platform - Quick Reference Card

**One-page reference for common commands and endpoints**

---

## 🚀 Starting Services

```bash
# Terminal 1: AIME Server
cd c:\Users\buyaf\OneDrive\Documents\EZWAI_AIME\EZWAi_Aime
pnpm run dev

# Terminal 2: LiveKit Agent (Local)
cd agents
python voice_agent.py start

# Optional: Ollama (for free T0 inference)
ollama serve
```

---

## 🔑 Essential Commands

### LiveKit CLI

```bash
# Install CLI
winget install LiveKit.LiveKitCLI

# Authenticate
lk cloud auth

# List projects
lk cloud project list

# Deploy agent
cd agents
lk agent create --name aime-voice-agent --file voice_agent.py

# View logs
lk agent logs aime-voice-agent --follow

# List agents
lk agent list

# Set environment variable
lk agent env set KEY=value

# Redeploy after changes
lk agent deploy

# List active rooms
lk room list
```

### Development

```bash
# Install dependencies
pnpm install
cd agents && pip install -r requirements.txt

# Run tests
pnpm test

# Check health
curl http://localhost:3000/health
```

---

## 🌐 API Endpoints

**Base URL**: `http://localhost:3000`

### Health & Status

```http
GET /health
```

### GHL OAuth

```http
GET /auth/ghl/callback?code=...
```

### Webhooks

```http
POST /webhooks/ghl
Headers: x-ghl-signature
```

### Bridge API

```http
# Process call
POST /api/bridge/process-call
{
  "contact_id": "...",
  "location_id": "...",
  "transcript": "...",
  "duration_seconds": 180
}

# Get contact context
GET /api/bridge/memory/context/:contactId

# Lookup contact by phone
POST /api/bridge/contacts/lookup
{ "location_id": "...", "phone": "+1..." }

# Check availability
POST /api/bridge/appointments/availability
{ "location_id": "...", "date": "2026-02-10", "service_type": "..." }

# Book appointment
POST /api/bridge/appointments/book
{
  "date": "2026-02-10",
  "time": "14:00",
  "name": "John Doe",
  "phone": "+1234567890",
  "service": "consultation"
}

# Create task
POST /api/bridge/tasks/create
{
  "location_id": "...",
  "contact_id": "...",
  "title": "Follow up call",
  "description": "...",
  "due_date": "2026-02-15"
}
```

### Model Router

```http
# Get cost report
GET /api/router/cost-report

# Get metrics
GET /api/router/metrics
```

### Contact Memory

```http
# Sync contact from GHL
POST /api/memory/sync/:locationId/:contactId

# Get contact context
GET /api/memory/context/:contactId

# Search contacts
GET /api/memory/search?q=john&limit=10
```

---

## 📁 Key Files

### Configuration

```
.env                        # All API keys and config
```

### Source Code

```
src/aime-server.ts          # Main API server
src/plugins/ghl/            # GHL integration (8 files)
src/memory/contact-memory/  # Contact memory system (6 files)
src/routing/model-router/   # Cost optimization (6 files)
src/bridge/                 # Voice ↔ CRM sync (4 files)
agents/voice_agent.py       # LiveKit voice agent
agents/tools/               # GHL and memory tools
```

### Documentation

```
MORNING_CHECKLIST.md        # Start here!
QUICK_START_LIVEKIT.md      # 15-min LiveKit deploy
LIVEKIT_DEPLOYMENT.md       # Full LiveKit guide
AIME_README.md              # Platform overview
SETUP_GUIDE.md              # Complete setup
BUILD_COMPLETE.md           # Build details
```

---

## 🔧 Environment Variables

### Required

```env
# GoHighLevel
GHL_CLIENT_ID=...
GHL_CLIENT_SECRET=...
GHL_PIT_TOKEN=...
GHL_REDIRECT_URI=http://localhost:3000/auth/ghl/callback

# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Deepgram (for voice)
DEEPGRAM_API_KEY=...
```

### Optional

```env
# Anthropic (for production)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI (alternative)
OPENAI_API_KEY=sk-...

# Infrastructure
REDIS_URL=redis://localhost:6379
DATABASE_PATH=./data/aime.db
PORT=3000
NODE_ENV=development
LOG_LEVEL=debug
```

---

## 💰 Model Tiers (T0-T3)

| Tier | Model | Use Case | Cost |
|------|-------|----------|------|
| **T0** | Ollama Llama 3.1 8B | Simple routing, health checks | $0 (free) |
| **T1** | Claude Haiku 4.5 | Contact lookups, formatting | $0.25/1M tokens |
| **T2** | Claude Sonnet 4.5 | Conversations, task extraction | $3/1M tokens |
| **T3** | Claude Opus 4.5 | Complex reasoning, error recovery | $15/1M tokens |

**Automatic escalation**: Low confidence results retry with higher tier

---

## 🎯 Common Workflows

### Sync a Contact

```bash
curl -X POST http://localhost:3000/api/memory/sync/LOCATION_ID/CONTACT_ID
curl http://localhost:3000/api/memory/context/CONTACT_ID
```

### Test Voice Agent

1. Deploy to LiveKit Cloud
2. Go to https://agents-playground.livekit.io/
3. Enter LiveKit credentials
4. Select **aime-voice-agent**
5. Test voice interaction

### Update and Redeploy Agent

```bash
# Edit agents/voice_agent.py
nano agents/voice_agent.py

# Redeploy
cd agents
lk agent deploy
```

### View Cost Savings

```bash
curl http://localhost:3000/api/router/cost-report
```

---

## 🐛 Troubleshooting

### Check if services are running

```bash
# Check AIME server
curl http://localhost:3000/health

# Check Ollama
curl http://localhost:11434

# Check LiveKit agent
lk agent list
```

### View logs

```bash
# AIME server (stdout in terminal)
# LiveKit agent
lk agent logs aime-voice-agent --follow
```

### Restart services

```bash
# Stop all
pkill node
pkill python

# Restart
pnpm run dev
cd agents && python voice_agent.py start
```

---

## 📊 Testing Checklist

- [ ] Health endpoint responds
- [ ] Cost report shows T0-T3 breakdown
- [ ] GHL OAuth flow works
- [ ] Contact sync successful
- [ ] Contact context retrieval works
- [ ] LiveKit agent deployed
- [ ] Voice interaction works in playground
- [ ] Call transcript saved
- [ ] Tasks auto-created in GHL

---

## 🔗 Important URLs

**Services**:
- AIME Server: http://localhost:3000
- Ollama: http://localhost:11434
- Redis: redis://localhost:6379

**External**:
- LiveKit Cloud: https://cloud.livekit.io/
- LiveKit Playground: https://agents-playground.livekit.io/
- GHL Marketplace: https://marketplace.gohighlevel.com
- Deepgram: https://deepgram.com
- Anthropic Console: https://console.anthropic.com

**Docs**:
- LiveKit Agents: https://docs.livekit.io/agents/
- GHL SDK: https://marketplace.gohighlevel.com/docs/sdk/node/
- LiveKit SIP: https://docs.livekit.io/sip/

---

## 🎓 Quick Tips

1. **Use Ollama for dev** to save costs (T0 tier)
2. **Monitor cost report** regularly to verify savings
3. **Use ngrok** to expose localhost for LiveKit agent in dev
4. **Check logs** when troubleshooting: `lk agent logs aime-voice-agent --follow`
5. **Sync contacts** before testing to populate memory
6. **Use webhooks** instead of polling GHL to avoid rate limits

---

**Keep this page bookmarked for quick reference!** 🚀
