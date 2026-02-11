# LiveKit Setup - Step by Step

**Your Phone Number**: +13059521569 (NORTH DADE, FL)
**SIP URI**: sip:178s68bcjty.sip.livekit.cloud

---

## ✅ Step 1: Create Dispatch Rule (IN PROGRESS)

Fill out the form in LiveKit Cloud:

### Form Fields:

**Rule name**
```
AIME Voice Agent
```

**Rule type**
✅ Individual (keep as-is)

**Room prefix**
```
aime-
```

**Agent name** (CRITICAL - must match deployment)
```
aime-voice-agent
```

**Dispatch metadata** (optional but recommended)
```json
{
  "service": "aime",
  "platform": "gohighlevel",
  "openclaw_url": "http://localhost:3000"
}
```

**Phone numbers** (check the box)
✅ **+13059521569**

**Trunks**
Leave empty

### Then Click: **"Create"**

---

## 📋 Step 2: Get LiveKit API Credentials

After creating the dispatch rule:

1. Go to **Settings** (left sidebar)
2. Click **Keys**
3. Click **Create API Key**
4. You'll get:
   - **LiveKit URL**: `wss://your-project-id.livekit.cloud`
   - **API Key**: `APIxxxxxxxxxx`
   - **API Secret**: `your_secret_here`

5. **IMPORTANT**: Copy these immediately - the secret is only shown once!

---

## ⚙️ Step 3: Update Your .env File

Replace these values in your `.env` file:

```env
# Replace this:
LIVEKIT_URL=wss://your-project.livekit.cloud
# With the actual URL you got above

# Replace these:
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here
# With the actual API Key and Secret
```

**Already configured** ✅:
- `LIVEKIT_SIP_URI=sip:178s68bcjty.sip.livekit.cloud`
- `LIVEKIT_PHONE_NUMBER=+13059521569`
- `ANTHROPIC_API_KEY=sk-ant-api03-...` (you have this)

---

## 🚀 Step 4: Deploy Your Agent

### Option A: Quick Deploy (Recommended)

```bash
# Navigate to agents directory
cd c:\Users\buyaf\OneDrive\Documents\EZWAI_AIME\EZWAi_Aime\agents

# Install LiveKit CLI (if not already installed)
winget install LiveKit.LiveKitCLI

# Authenticate
lk cloud auth
# (will open browser - sign in with buyaford4lesstoday@gmail.com)

# Deploy the agent
lk agent create --name aime-voice-agent --file voice_agent.py
```

**IMPORTANT**: The agent name `aime-voice-agent` MUST match what you entered in the dispatch rule!

### Option B: Manual Python Deployment (if CLI fails)

```bash
cd agents

# Install requirements
pip install -r requirements.txt

# Set environment variables
set LIVEKIT_URL=wss://your-project.livekit.cloud
set LIVEKIT_API_KEY=your_api_key
set LIVEKIT_API_SECRET=your_secret
set OPENCLAW_BASE_URL=http://localhost:3000

# Start the agent locally
python voice_agent.py start
```

---

## 🧪 Step 5: Test Your Setup

### Test 1: Check Dispatch Rule

1. Go to **Telephony → Dispatch rules** in LiveKit Cloud
2. You should see: **"AIME Voice Agent"** with status **Active**
3. Phone number **+13059521569** should be listed

### Test 2: Check Agent Status

```bash
lk agent list
```

You should see:
```
NAME                STATUS    VERSION
aime-voice-agent    RUNNING   1.0.0
```

### Test 3: Make a Test Call

**Call your number**: **+1 (305) 952-1569**

What should happen:
1. Agent answers
2. Speaks greeting: "Hello, this is AIME..."
3. Listens to your voice
4. Responds with context from GHL (if contact exists)

### View logs during call:

```bash
lk agent logs aime-voice-agent --follow
```

---

## 🔧 Environment Variables Status

Check what you still need:

### ✅ Have (Already Configured)
- `ANTHROPIC_API_KEY` ✅
- `LIVEKIT_SIP_URI` ✅
- `LIVEKIT_PHONE_NUMBER` ✅

### ⚠️ Need to Get
- `LIVEKIT_URL` - Get from Settings → Keys
- `LIVEKIT_API_KEY` - Get from Settings → Keys
- `LIVEKIT_API_SECRET` - Get from Settings → Keys
- `DEEPGRAM_API_KEY` - Get from https://deepgram.com
- `GHL_CLIENT_ID` - Get from https://marketplace.gohighlevel.com
- `GHL_CLIENT_SECRET` - Get from https://marketplace.gohighlevel.com
- `GHL_PIT_TOKEN` - Get from https://marketplace.gohighlevel.com

### 📝 Optional (can skip for testing)
- `OPENAI_API_KEY` - For alternative TTS/STT
- `REDIS_URL` - Use in-memory for now
- `DATABASE_URL` - Use SQLite for now (default)

---

## 🎯 What Happens When Someone Calls

1. **Phone rings** → LiveKit receives call on +13059521569
2. **Dispatch rule** → Routes call to `aime-voice-agent`
3. **Agent creates room** → `aime-{call-id}`
4. **Agent answers** → Starts voice conversation
5. **Speech-to-Text** → Deepgram converts voice to text
6. **Context lookup** → Queries OpenClaw bridge for contact info
7. **LLM processes** → Anthropic generates response
8. **Text-to-Speech** → Cartesia/OpenAI speaks response
9. **Call ends** → Transcript saved to GHL via bridge

---

## 📞 Dispatch Rule Details

Here's what your dispatch rule does:

- **Incoming calls to +13059521569** → Routed to agent
- **Creates room** → `aime-{unique-id}` for each call
- **Launches agent** → `aime-voice-agent` joins the room
- **Metadata passed** → Agent knows it's an AIME/GHL call
- **Agent handles** → Full conversation flow

---

## 🆘 Troubleshooting

### Issue: "Agent not found" when testing

**Solution**: Make sure you deployed the agent with exact name:
```bash
lk agent list
# Should show: aime-voice-agent
```

### Issue: Call doesn't connect

**Check**:
1. Dispatch rule is **Active**
2. Phone number is selected in rule
3. Agent is **RUNNING** (`lk agent list`)

### Issue: Agent can't reach OpenClaw

**Solution**: For local testing, use ngrok:
```bash
ngrok http 3000
# Copy HTTPS URL and update:
lk agent env set OPENCLAW_BASE_URL=https://abc123.ngrok.io
```

### Issue: No speech recognition

**Check**: Deepgram API key is set:
```bash
lk agent env set DEEPGRAM_API_KEY=your_key
```

---

## ✨ Next Steps After Setup

Once everything works:

1. **Test call flow** - Call and verify full conversation
2. **Check GHL sync** - Verify transcript saved to contact
3. **Test task creation** - Agent should create tasks in GHL
4. **Monitor costs** - Check LiveKit dashboard for usage
5. **Configure routing** - Set up business hours, IVR, etc.

---

## 📚 Documentation References

- **Quick Start**: [QUICK_START_LIVEKIT.md](QUICK_START_LIVEKIT.md)
- **Full Deployment**: [LIVEKIT_DEPLOYMENT.md](LIVEKIT_DEPLOYMENT.md)
- **API Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Platform Overview**: [AIME_README.md](AIME_README.md)

---

**Current Progress**:
- ✅ Phone number purchased
- ✅ SIP URI configured
- ⏳ Dispatch rule (in progress - fill form and click Create)
- ⏳ API credentials (next - go to Settings → Keys)
- ⏳ Agent deployment (after credentials)
- ⏳ Test call (final step)

**You're almost there!** 🚀
