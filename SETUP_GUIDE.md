# AIME Platform - Complete Setup Guide

**Step-by-step guide to get AIME running from scratch**

---

## 📋 Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Node.js >= 18.0.0** installed ([Download](https://nodejs.org/))
- [ ] **Python >= 3.10** installed ([Download](https://www.python.org/))
- [ ] **pnpm** installed (`npm install -g pnpm`)
- [ ] **Git** installed
- [ ] **GoHighLevel account** (trial or paid)
- [ ] **Text editor** (VS Code recommended)

**Optional but recommended:**
- [ ] **Redis** for session storage
- [ ] **Ollama** for free T0 inference ([Download](https://ollama.ai/))

---

## Step 1: Clone Repository

```bash
cd ~/Documents  # or your preferred location
git clone https://github.com/JoeMachado62/EZWAi_Aime.git
cd EZWAi_Aime
```

---

## Step 2: Install Dependencies

### Node.js Dependencies

```bash
# Install with pnpm
pnpm install

# This installs:
# - OpenClaw framework
# - @gohighlevel/api-client
# - All other TypeScript dependencies
```

**Note**: You may see a warning about `node-llama-cpp` - this is optional and can be ignored for now.

### Python Dependencies

```bash
cd agents
pip install -r requirements.txt

# This installs:
# - LiveKit agents framework
# - Deepgram, OpenAI, Cartesia plugins
# - HTTP clients for bridge communication
```

---

## Step 3: Get GoHighLevel Credentials

### 3.1: Create GHL Marketplace App

1. Go to https://marketplace.gohighlevel.com
2. Sign in with your GHL account
3. Click **"Create App"**
4. Choose **"Private Integration"** (for development)

### 3.2: Configure App Settings

**App Information:**
- **Name**: AIME Voice Agent (or your choice)
- **Description**: AI-powered voice and text agent

**OAuth Configuration:**
- **Redirect URI**: `http://localhost:3000/auth/ghl/callback`
- **Scopes** (select these):
  - ✅ `contacts.readonly`
  - ✅ `contacts.write`
  - ✅ `conversations.readonly`
  - ✅ `conversations.write`
  - ✅ `calendars.readonly`
  - ✅ `calendars.write`
  - ✅ `opportunities.readonly`
  - ✅ `opportunities.write`
  - ✅ `locations.readonly`

### 3.3: Get Credentials

After creating the app:
1. Copy **Client ID**
2. Copy **Client Secret**
3. Go to **"API Keys"** tab
4. Generate and copy **Private Integration Token** (for development)

---

## Step 4: Get LiveKit Credentials

### 4.1: Create LiveKit Account

1. Go to https://livekit.io/cloud
2. Sign up for free account
3. Create a new project: **"AIME Voice"**

### 4.2: Get Credentials

From your LiveKit dashboard:
1. Copy **LiveKit URL** (looks like: `wss://your-project.livekit.cloud`)
2. Go to **Settings → Keys**
3. Create new API key
4. Copy **API Key** and **API Secret**

### 4.3: Test Connection (Optional)

Visit https://agents-playground.livekit.io/ and test with your credentials.

---

## Step 5: Get AI Service Credentials

### 5.1: Anthropic (Claude)

**For Production:**
1. Go to https://console.anthropic.com
2. Create API key
3. Copy key (starts with `sk-ant-`)

**For Development:**
You can skip this and use Ollama (free local inference) for testing.

### 5.2: Deepgram (Speech-to-Text)

1. Go to https://deepgram.com
2. Sign up (free tier available)
3. Create API key
4. Copy key

### 5.3: OpenAI (Optional)

If you prefer OpenAI models:
1. Go to https://platform.openai.com
2. Create API key
3. Copy key

---

## Step 6: Configure Environment

### 6.1: Create .env File

```bash
# From project root
cp .env .env.local  # Backup template
# Now edit .env with your credentials
```

### 6.2: Fill in Credentials

Edit `.env` file:

```env
# ===== REQUIRED =====

# GoHighLevel
GHL_CLIENT_ID=your_client_id_here
GHL_CLIENT_SECRET=your_client_secret_here
GHL_REDIRECT_URI=http://localhost:3000/auth/ghl/callback
GHL_PIT_TOKEN=your_private_integration_token_here

# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxx
LIVEKIT_API_SECRET=your_secret_here

# Deepgram (Speech-to-Text)
DEEPGRAM_API_KEY=your_deepgram_key_here

# ===== FOR PRODUCTION =====

# Anthropic (Claude) - Optional for development
ANTHROPIC_API_KEY=sk-ant-your_key_here

# OpenAI - Optional
OPENAI_API_KEY=sk-your_key_here

# ===== OPTIONAL =====

# Redis (for production session storage)
REDIS_URL=redis://localhost:6379

# Database
DATABASE_PATH=./data/aime.db

# Server
PORT=3000
NODE_ENV=development
LOG_LEVEL=debug
```

**Security Note**: Never commit `.env` to git! It's already in `.gitignore`.

---

## Step 7: Install Ollama (Optional - Free T0 Inference)

### 7.1: Install Ollama

**macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download

### 7.2: Download Model

```bash
# Download Llama 3.1 8B (used for T0 tier)
ollama pull llama3.1:8b

# Test it
ollama run llama3.1:8b "Hello"
```

### 7.3: Start Ollama Server

```bash
# Start Ollama (if not auto-started)
ollama serve

# Should run on http://localhost:11434
```

---

## Step 8: Initialize Database

```bash
# Create data directory
mkdir -p data

# Database will be auto-created on first run
# Location: ./data/aime.db
```

---

## Step 9: Start AIME Platform

### Terminal 1: OpenClaw/AIME Server

```bash
# From project root
pnpm run dev

# Or for production:
# pnpm start

# You should see:
# 🚀 Initializing AIME Platform...
# ✅ GHL Plugin initialized
# ✅ Database initialized
# ✅ Contact Memory initialized
# ✅ Model Router initialized
# ✅ Bridge Layer initialized
# 🎉 AIME Platform ready!
# 🌟 AIME Server running on http://localhost:3000
```

### Terminal 2: LiveKit Voice Agent

```bash
# Open new terminal
cd agents
python voice_agent.py start

# You should see:
# Starting AIME Voice Agent...
# Connected to LiveKit
# Agent ready for calls
```

---

## Step 10: Test the Setup

### 10.1: Test Health Check

```bash
curl http://localhost:3000/health

# Expected response:
# {"status":"healthy","timestamp":1234567890}
```

### 10.2: Test GHL OAuth (Browser)

1. Open browser
2. Go to: `http://localhost:3000/auth/ghl/callback?code=test`
3. You should see OAuth flow (or error if code invalid - that's OK!)

### 10.3: Test API Endpoints

```bash
# Get cost report (should show T0-T3 metrics)
curl http://localhost:3000/api/router/cost-report

# Test contact lookup (will fail without real data - that's OK!)
curl -X POST http://localhost:3000/api/bridge/contacts/lookup \
  -H "Content-Type: application/json" \
  -d '{"location_id":"test","phone":"+1234567890"}'
```

---

## Step 11: Complete GHL OAuth

### 11.1: Get Authorization URL

The GHL plugin has a method to generate the auth URL. For now, manually construct:

```
https://marketplace.gohighlevel.com/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:3000/auth/ghl/callback&response_type=code&scope=contacts.readonly contacts.write conversations.readonly conversations.write calendars.readonly calendars.write
```

Replace `YOUR_CLIENT_ID` with your actual client ID.

### 11.2: Authorize

1. Visit the URL in your browser
2. Sign in to GHL if needed
3. Click **"Authorize"**
4. You'll be redirected to localhost with a code
5. Server will exchange code for tokens
6. Tokens are stored in memory/Redis

---

## Step 12: Test Voice Call (Optional)

### 12.1: Setup SIP (if you have phone access)

See LiveKit documentation for SIP trunk setup:
- https://docs.livekit.io/sip/

### 12.2: Or Test with LiveKit Playground

1. Go to https://agents-playground.livekit.io/
2. Enter your LiveKit credentials
3. Select your agent
4. Test voice interaction

---

## 🎉 Setup Complete!

Your AIME platform is now running!

### What You Can Do Now:

1. **Sync a contact from GHL**:
```bash
curl -X POST http://localhost:3000/api/memory/sync/LOCATION_ID/CONTACT_ID
```

2. **Get contact context**:
```bash
curl http://localhost:3000/api/memory/context/CONTACT_ID
```

3. **View cost metrics**:
```bash
curl http://localhost:3000/api/router/metrics
```

4. **Test voice agent** (if phone/SIP configured):
   - Call your LiveKit SIP number
   - Agent should answer and greet you
   - Have a conversation
   - Check GHL for auto-created tasks

---

## 🔧 Troubleshooting

### Issue: "Connection refused" on startup

**Solution**: Check that ports 3000 (server) and 11434 (Ollama) are not in use.

```bash
# Check ports
lsof -i :3000
lsof -i :11434

# Kill if needed
kill -9 PID
```

### Issue: "GHL OAuth failed"

**Solutions**:
1. Verify Client ID and Secret are correct
2. Check redirect URI matches exactly
3. Ensure scopes are approved in GHL app settings
4. For dev testing, use PIT token instead

### Issue: "LiveKit connection failed"

**Solutions**:
1. Verify LIVEKIT_URL format (should start with `wss://`)
2. Check API Key and Secret are correct
3. Ensure LiveKit project is active
4. Test credentials in LiveKit Playground first

### Issue: "Ollama not found"

**Solutions**:
1. Check Ollama is running: `curl http://localhost:11434`
2. Restart Ollama: `ollama serve`
3. For now, the system will fallback to paid APIs if Ollama unavailable

### Issue: "Database locked"

**Solution**: Stop all running servers and restart:
```bash
# Kill all node processes
pkill node

# Restart
pnpm run dev
```

---

## 📚 Next Steps

Now that setup is complete:

1. **Read the main README**: `AIME_README.md`
2. **Explore the codebase**: Start with `src/aime-server.ts`
3. **Test integrations**: Try syncing contacts and making calls
4. **Review cost optimization**: Check `src/routing/model-router/`
5. **Customize voice agent**: Edit `agents/voice_agent.py`

---

## 🆘 Need Help?

- **Documentation**: Check `docs/` folder
- **GHL Plugin**: See `src/plugins/ghl/README.md`
- **Issues**: Check GitHub issues or contact team

---

**Setup complete! Happy building! 🚀**
