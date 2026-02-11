# EZWAi AIME Platform 🤖

**AI-Powered CRM Agent Platform for GoHighLevel**

Complete voice and text AI agent system with cross-channel context awareness, automatic task creation, and intelligent cost optimization.

---

## 🎯 What is AIME?

AIME (AI Management Engine) is an intelligent agent platform built on OpenClaw that integrates with GoHighLevel CRM to provide:

- **🎙️ Voice AI** - Natural phone conversations using LiveKit
- **💬 Cross-Channel Context** - Remembers all interactions (calls, SMS, email, chat)
- **✅ Auto Task Creation** - Extracts action items from conversations
- **💰 Cost Optimized** - T0-T3 routing reduces AI costs by 90%+

**Target Users**: SMB businesses and agencies using GoHighLevel CRM

---

## ⚡ Quick Start

### Prerequisites

```bash
# Required
- Node.js >= 18.0.0
- Python >= 3.10
- GoHighLevel account
- Anthropic API key (for production)

# Optional but recommended
- Redis (for session storage)
- PostgreSQL (for persistent memory)
- Ollama (for free T0 inference)
```

### 1. Clone and Install

```bash
git clone https://github.com/JoeMachado62/EZWAi_Aime.git
cd EZWAi_Aime

# Install Node.js dependencies
pnpm install

# Install Python dependencies for LiveKit agents
cd agents
pip install -r requirements.txt
cd ..
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```env
# GoHighLevel (required)
GHL_CLIENT_ID=your_client_id
GHL_CLIENT_SECRET=your_client_secret
GHL_REDIRECT_URI=http://localhost:3000/auth/ghl/callback
GHL_PIT_TOKEN=your_private_integration_token  # For dev

# LiveKit (for voice)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret

# Anthropic (for production)
ANTHROPIC_API_KEY=your_api_key

# Deepgram (for voice)
DEEPGRAM_API_KEY=your_api_key

# Optional
REDIS_URL=redis://localhost:6379
DATABASE_PATH=./data/aime.db
```

### 3. Get GHL Credentials

1. Go to https://marketplace.gohighlevel.com
2. Create a Developer App (Private Integration for dev)
3. Configure OAuth scopes:
   - `contacts.readonly`, `contacts.write`
   - `conversations.readonly`, `conversations.write`
   - `calendars.readonly`, `calendars.write`
4. Copy Client ID and Client Secret

### 4. Start the Platform

```bash
# Terminal 1: Start OpenClaw/AIME server
pnpm run dev

# Terminal 2: Start LiveKit voice agent
cd agents
python voice_agent.py start

# Server runs on http://localhost:3000
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│  LiveKit Voice Agent (Python)                        │
│  ├─ STT (Deepgram)                                  │
│  ├─ LLM (OpenAI/Anthropic via Model Router)        │
│  └─ TTS (Cartesia)                                  │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP/WebSocket
┌──────────────────┴──────────────────────────────────┐
│  OpenClaw Bridge Layer (TypeScript)                  │
│  ├─ Transcript Processing                           │
│  ├─ Context Assembly                                │
│  └─ Event Synchronization                           │
└──────────────────┬──────────────────────────────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
┌────┴─────┐ ┌────┴─────┐ ┌────┴──────┐
│ GHL      │ │ Contact  │ │ Model     │
│ Plugin   │ │ Memory   │ │ Router    │
│          │ │ System   │ │ (T0-T3)   │
└────┬─────┘ └──────────┘ └───────────┘
     │
┌────┴─────────────┐
│ GoHighLevel CRM  │
└──────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Voice Agent** | LiveKit + Python | Handles phone calls with real-time STT/TTS |
| **GHL Plugin** | TypeScript + SDK | CRM integration (contacts, conversations, tasks) |
| **Contact Memory** | SQLite/PostgreSQL | Unified cross-channel history |
| **Model Router** | TypeScript | T0-T3 cost optimization (90%+ savings) |
| **Bridge Layer** | TypeScript | Synchronizes voice ↔ CRM data |

---

## 📚 Core Features

### 1. Cross-Channel Context Awareness

**Problem**: Customer calls after emailing yesterday, but agent doesn't remember the email conversation.

**AIME Solution**: Maintains complete history across all channels:
- ☎️ Phone calls (LiveKit)
- 💬 SMS (GHL)
- ✉️ Email (GHL)
- 🌐 Web chat (GHL)
- 📱 WhatsApp, Facebook, Instagram (GHL)

**Example**:
```
Customer calls: "Following up on the email I sent yesterday about pricing"
AIME: "Yes, I see you asked about our enterprise plan. Let me address those questions..."
```

### 2. Automatic Task Creation

**After every conversation, AIME automatically creates follow-up tasks in GHL:**

| Pattern Detected | Task Created |
|-----------------|--------------|
| "I'll call you next week" | "Follow up call - Customer requested callback" |
| "Send me that information" | "Send requested information - Pricing details" |
| "I need to think about it" | "Check-in - Customer considering proposal" (3 days) |

### 3. Cost-Optimized Model Router (T0-T3)

**Reduces AI costs by 90%+ through intelligent routing:**

| Tier | Model | Use Case | Cost |
|------|-------|----------|------|
| **T0** | Ollama Llama 3.1 8B (local) | Health checks, simple routing | $0 (free) |
| **T1** | Claude Haiku 4.5 | Contact lookups, data formatting | $0.25/1M tokens |
| **T2** | Claude Sonnet 4.5 | Conversations, task extraction | $3/1M tokens |
| **T3** | Claude Opus 4.5 | Complex reasoning, error recovery | $15/1M tokens |

**Auto-escalation**: If T1 returns low confidence, automatically retries with T2.

**Estimated savings**: $1,450/month → $50/month (97% reduction)

---

## 📖 Usage Examples

### Voice Call Flow

```python
# 1. Customer calls
# 2. LiveKit agent identifies caller by phone number
# 3. Bridge loads context from Contact Memory:
{
  "summary": "John Smith last contacted 3 days ago via email",
  "recent_interactions": [
    "Email: Asked about enterprise pricing",
    "Call: Discussed implementation timeline"
  ],
  "key_facts": [
    "Preference: Needs WhatsApp integration",
    "Commitment: Will make decision by end of month"
  ],
  "recommendations": [
    "Reference pricing discussion from email",
    "Check if WhatsApp integration question was answered"
  ]
}

# 4. Agent greets with context:
AIME: "Hi John! Good to hear from you. I see you had some questions
about our enterprise pricing in your email. Happy to help with that."

# 5. Conversation proceeds naturally
# 6. After call ends:
#    - Transcript saved to Contact Memory
#    - Summary note created in GHL
#    - Follow-up tasks auto-created:
#      ✅ "Send enterprise pricing breakdown"
#      ✅ "Schedule demo for next Tuesday"
```

### API Integration

```typescript
// Sync contact from GHL to memory
await memoryManager.syncContactFromGHL(locationId, contactId);

// Get enriched context
const context = await memoryManager.getContactContext(contactId);

// Format for AI prompt
const prompt = memoryManager.formatContextForAI(contactId, verbose: true);

// Route task to appropriate model tier
const decision = modelRouter.route(prompt, {
  taskType: 'conversation_handling',
  requiresTools: true,
});

// Execute with auto-escalation
const result = await modelRouter.execute(prompt);
console.log(`Used ${result.toTier} (${result.response.cost})`);
```

---

## 🔌 API Reference

### Bridge Endpoints

```http
# Process completed call
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

# Check appointment availability
POST /api/bridge/appointments/availability
{ "location_id": "...", "date": "2026-02-10", "service_type": "consultation" }

# Book appointment
POST /api/bridge/appointments/book
{
  "date": "2026-02-10",
  "time": "14:00",
  "name": "John Doe",
  "phone": "+1234567890",
  "service": "consultation"
}
```

### Model Router Endpoints

```http
# Get cost report
GET /api/router/cost-report

# Get metrics
GET /api/router/metrics
```

### Memory Endpoints

```http
# Sync contact
POST /api/memory/sync/:locationId/:contactId

# Get context
GET /api/memory/context/:contactId

# Search contacts
GET /api/memory/search?q=john&limit=10
```

---

## 🚀 Deployment

### Development (Local)

```bash
# Already covered in Quick Start
pnpm run dev
```

### Production (Docker)

```bash
# Build image
docker build -t aime-platform .

# Run with environment
docker run -p 3000:3000 \
  -e GHL_CLIENT_ID=... \
  -e GHL_CLIENT_SECRET=... \
  -e ANTHROPIC_API_KEY=... \
  aime-platform
```

### Production (VPS)

See `docs/DEPLOYMENT.md` for complete guide including:
- Fly.io deployment
- Render deployment
- Self-hosted with PM2
- LiveKit Cloud vs self-hosted

---

## 💰 Cost Estimates

### MVP (Single Business)

| Service | Cost/Month |
|---------|-----------|
| OpenClaw Server (VPS) | $20-50 |
| LiveKit Cloud | $0.01-0.05/min (usage) |
| Claude API (with T0-T3 routing) | $50-200 |
| Deepgram STT | $0.0043/min |
| Redis/PostgreSQL (managed) | $0-25 |
| **Total** | **$100-350/month** |

### SaaS (Multi-Tenant)

Scale up with self-hosted LiveKit and shared infrastructure.
Per-customer cost: ~$10-30/month

---

## 🛠️ Development

### Project Structure

```
EZWAi_Aime/
├── src/
│   ├── plugins/ghl/          # GHL SDK integration
│   ├── memory/contact-memory/  # Unified memory system
│   ├── routing/model-router/   # T0-T3 cost optimization
│   ├── bridge/                 # LiveKit ↔ OpenClaw sync
│   └── aime-server.ts          # Main server
├── agents/                     # LiveKit Python agents
│   ├── voice_agent.py          # Main voice agent
│   └── tools/                  # GHL/memory tools
├── docs/                       # Documentation
└── .env                        # Configuration
```

### Running Tests

```bash
# Unit tests
pnpm test

# Integration tests
pnpm test:e2e

# LiveKit agent tests
cd agents
pytest
```

---

## 📝 Documentation

| Document | Description |
|----------|-------------|
| [GHL Plugin README](src/plugins/ghl/README.md) | Complete GHL integration guide |
| [Model Router Guide](docs/MODEL_ROUTER.md) | T0-T3 system explained |
| [LiveKit Integration](docs/LIVEKIT.md) | Voice agent setup |
| [Deployment Guide](docs/DEPLOYMENT.md) | Production deployment |
| [API Reference](docs/API.md) | Complete API documentation |

---

## 🐛 Troubleshooting

### "No tokens found"
- Complete OAuth flow or set `GHL_PIT_TOKEN` for development

### "Database not initialized"
- Ensure `DATABASE_PATH` directory exists
- Run `mkdir -p ./data` before starting server

### "LiveKit connection failed"
- Verify `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- Check LiveKit Cloud dashboard for project status

### "Rate limit exceeded"
- GHL enforces aggressive rate limits (~100 req/min)
- Implement caching and use webhooks instead of polling
- Contact GHL support to increase limits

---

## 🤝 Contributing

This is a private project. For issues or feature requests, contact the development team.

---

## 📄 License

MIT License - See LICENSE file

---

## 🌟 Status

**Current Status**: ✅ **BUILD COMPLETE - READY FOR TESTING**

All core components implemented:
- ✅ GHL Plugin with OAuth
- ✅ Unified Contact Memory
- ✅ Model Router (T0-T3)
- ✅ LiveKit Voice Agent
- ✅ Bridge Layer
- ✅ Auto Task Creation
- ✅ API Server

**Next Steps**:
1. Add your API keys to `.env`
2. Test GHL OAuth flow
3. Test voice agent with LiveKit
4. Run end-to-end call scenario

---

**Built with ❤️ by the EZWAi team**

For support: See documentation or contact your team lead.
