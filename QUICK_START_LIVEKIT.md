# LiveKit Cloud - Quick Start Guide

**15-minute setup to get your voice agent deployed**

**Account**: buyaford4lesstoday@gmail.com
**Project**: AIME Voice Agent

---

## ✅ Step 1: Install LiveKit CLI (2 min)

### Windows

```powershell
# Open PowerShell as Administrator
winget install LiveKit.LiveKitCLI

# Verify installation
lk --version
```

**Alternative**: Download from https://github.com/livekit/livekit-cli/releases

---

## ✅ Step 2: Authenticate (2 min)

```bash
# Start authentication
lk cloud auth

# This will:
# 1. Open your browser
# 2. Sign in with: buyaford4lesstoday@gmail.com
# 3. Authorize the CLI
# 4. Store credentials locally
```

---

## ✅ Step 3: Get Your Credentials (3 min)

```bash
# List your projects
lk cloud project list

# You should see your project with:
# - Project Name: AIME Voice Agent (or similar)
# - LiveKit URL: wss://your-project-id.livekit.cloud
```

### Add to .env

Update your `.env` file:

```env
LIVEKIT_URL=wss://your-project-id.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxx
LIVEKIT_API_SECRET=your_secret_here
```

**Get API Key and Secret**:
1. Go to https://cloud.livekit.io/
2. Select your project
3. Go to **Settings → Keys**
4. Create new API key
5. Copy Key and Secret to `.env`

---

## ✅ Step 4: Deploy Agent (5 min)

```bash
# Navigate to agents directory
cd agents

# Deploy to LiveKit Cloud
lk agent create \
  --name aime-voice-agent \
  --file voice_agent.py

# This will:
# 1. Package your agent code and dependencies
# 2. Upload to LiveKit Cloud
# 3. Deploy and start the agent
# 4. Return deployment URL
```

---

## ✅ Step 5: Configure Environment Variables (2 min)

```bash
# Set OpenClaw bridge URL
# For development (use ngrok to expose localhost):
ngrok http 3000
# Then set the HTTPS URL:
lk agent env set OPENCLAW_BASE_URL=https://your-ngrok-url.ngrok.io

# Set API keys
lk agent env set DEEPGRAM_API_KEY=your_key
lk agent env set OPENAI_API_KEY=your_key
lk agent env set ANTHROPIC_API_KEY=your_key
```

---

## ✅ Step 6: Test Your Agent (1 min)

```bash
# Check agent status
lk agent list

# You should see:
# NAME                STATUS    VERSION
# aime-voice-agent    RUNNING   1.0.0

# View logs
lk agent logs aime-voice-agent --follow
```

### Test with Agents Playground

1. Go to https://agents-playground.livekit.io/
2. Enter your LiveKit credentials
3. Select **aime-voice-agent**
4. Click **Connect**
5. Test voice interaction!

---

## 🎉 You're Done!

Your voice agent is now deployed to LiveKit Cloud!

### What You Can Do Now:

1. **Test voice interaction** in the Agents Playground
2. **View logs** with `lk agent logs aime-voice-agent --follow`
3. **Monitor usage** at https://cloud.livekit.io/

### Next Steps:

- **Configure SIP** for actual phone calls (see [LIVEKIT_DEPLOYMENT.md](LIVEKIT_DEPLOYMENT.md#step-8-configure-phone-calls-sip))
- **Update agent code** and redeploy with `lk agent deploy`
- **Monitor costs** in LiveKit Cloud dashboard

---

## 🔧 Common Issues

### Issue: "lk: command not found"

**Solution**: Restart terminal or add to PATH manually

### Issue: "Authentication failed"

**Solution**:
```bash
lk cloud auth --force
```

### Issue: "Agent deployment failed"

**Solution**: Check logs
```bash
lk agent logs aime-voice-agent
```

Common causes:
- Missing dependencies in requirements.txt
- Environment variables not set
- Python version mismatch (need 3.10+)

### Issue: "Agent can't reach OpenClaw"

**Solution**: For development, use ngrok to expose localhost:
```bash
# In new terminal
ngrok http 3000

# Copy the HTTPS URL and set it:
lk agent env set OPENCLAW_BASE_URL=https://abc123.ngrok.io
```

---

## 📚 More Information

- **Full deployment guide**: See [LIVEKIT_DEPLOYMENT.md](LIVEKIT_DEPLOYMENT.md)
- **LiveKit docs**: https://docs.livekit.io/agents/
- **Support**: https://livekit.io/discord

---

**Total time**: ~15 minutes
**Next**: Configure phone calls with SIP (optional)
