# LiveKit Cloud Deployment Guide

**Account**: buyaford4lesstoday@gmail.com
**Project**: AIME Voice Agent

---

## ✅ Step 1: Install LiveKit CLI

### Windows (PowerShell as Administrator)

```powershell
winget install LiveKit.LiveKitCLI
```

**Alternative (if winget not available)**:
Download from https://github.com/livekit/livekit-cli/releases

### Verify Installation

```bash
lk --version
```

---

## ✅ Step 2: Authenticate with LiveKit Cloud

```bash
lk cloud auth
```

This will:
1. Open your browser
2. Sign in with: **buyaford4lesstoday@gmail.com**
3. Authorize the CLI
4. Store credentials locally

---

## ✅ Step 3: Get Your Project Credentials

Once authenticated, get your credentials:

```bash
lk cloud project list
```

Copy your project details:
- **LiveKit URL**: `wss://your-project-id.livekit.cloud`
- **API Key**: Will be in the dashboard
- **API Secret**: Will be in the dashboard

### Add to .env

Update your `.env` file:

```env
# LiveKit Cloud Configuration
LIVEKIT_URL=wss://your-project-id.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxx
LIVEKIT_API_SECRET=your_secret_here

# OpenClaw Bridge URL (for agent to call back)
OPENCLAW_BASE_URL=http://localhost:3000
# For production: https://your-domain.com
```

---

## ✅ Step 4: Prepare Agent for Deployment

### 4.1: Update Agent Configuration

Edit `agents/voice_agent.py` and ensure it has:

```python
import os
from livekit.agents import cli

# Configuration from environment
OPENCLAW_BASE_URL = os.getenv("OPENCLAW_BASE_URL", "http://localhost:3000")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
```

### 4.2: Create Agent Manifest

Create `agents/agent.yaml`:

```yaml
name: aime-voice-agent
version: 1.0.0
description: AIME AI Voice Agent for GoHighLevel Integration

# Entry point
entrypoint: voice_agent.py

# Python version
runtime: python3.11

# Dependencies
requirements: requirements.txt

# Environment variables needed
env:
  - OPENCLAW_BASE_URL
  - DEEPGRAM_API_KEY
  - OPENAI_API_KEY
  - ANTHROPIC_API_KEY

# Resource requirements
resources:
  cpu: 1
  memory: 512Mi

# Auto-scaling
scaling:
  min_instances: 1
  max_instances: 5
  target_cpu_percent: 70
```

---

## ✅ Step 5: Deploy Agent to LiveKit Cloud

### Option A: Quick Deploy (Recommended for Testing)

```bash
cd agents

# Create and deploy agent
lk agent create \
  --name aime-voice-agent \
  --file voice_agent.py

# This will:
# 1. Package your agent code
# 2. Upload to LiveKit Cloud
# 3. Deploy and start the agent
# 4. Return deployment URL
```

### Option B: Use Starter Template (For Production)

```bash
# Create from template
lk app create \
  --template agent-starter-python aime-agent

cd aime-agent

# Copy your agent files
cp ../agents/voice_agent.py .
cp ../agents/requirements.txt .
cp -r ../agents/tools .

# Deploy
lk agent deploy
```

---

## ✅ Step 6: Configure Environment Variables

After deploying, set environment variables in LiveKit Cloud:

```bash
# Set OpenClaw bridge URL (use your public URL in production)
lk agent env set OPENCLAW_BASE_URL=https://your-domain.com

# Set API keys
lk agent env set DEEPGRAM_API_KEY=your_key
lk agent env set OPENAI_API_KEY=your_key
lk agent env set ANTHROPIC_API_KEY=your_key
```

**For Development (Local OpenClaw)**:
You'll need to expose your local server using ngrok or similar:

```bash
# In a new terminal
ngrok http 3000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Then set it:
lk agent env set OPENCLAW_BASE_URL=https://abc123.ngrok.io
```

---

## ✅ Step 7: Test Your Deployed Agent

### 7.1: Check Agent Status

```bash
lk agent list

# You should see:
# NAME                STATUS    VERSION    LAST DEPLOYED
# aime-voice-agent    RUNNING   1.0.0      2m ago
```

### 7.2: View Logs

```bash
lk agent logs aime-voice-agent --follow
```

### 7.3: Test with Agents Playground

1. Go to https://agents-playground.livekit.io/
2. Enter your LiveKit credentials
3. Select **aime-voice-agent**
4. Click **Connect**
5. Test voice interaction!

---

## ✅ Step 8: Configure Phone Calls (SIP)

To enable actual phone calls, you need to configure SIP.

### 8.1: Choose SIP Provider

**Recommended**: Twilio (most documented)

1. Go to https://www.twilio.com
2. Create account
3. Get phone number
4. Configure SIP trunk

### 8.2: Create SIP Trunk in LiveKit

```bash
lk sip trunk create \
  --name twilio-trunk \
  --inbound-addresses twilio-sip-uri \
  --outbound-address your-twilio-trunk
```

### 8.3: Create Dispatch Rule

```bash
lk sip dispatch create dispatch-rule.json
```

Where `dispatch-rule.json`:

```json
{
  "rule": {
    "dispatchRuleIndividual": {
      "roomPrefix": "call-"
    }
  },
  "trunks": ["twilio-trunk"],
  "hidePhoneNumber": false,
  "name": "aime-inbound-calls",
  "metadata": "{\"agent\":\"aime-voice-agent\"}"
}
```

### 8.4: Configure Twilio Webhook

In Twilio console, set webhook URL to:
```
https://your-livekit-project.livekit.cloud/sip/inbound
```

---

## 🔄 Update and Redeploy

### Update Agent Code

```bash
cd agents

# Make your changes to voice_agent.py

# Redeploy
lk agent deploy

# Or force rebuild
lk agent deploy --force
```

### View Deployment History

```bash
lk agent versions aime-voice-agent
```

### Rollback if Needed

```bash
lk agent rollback aime-voice-agent --version 1.0.0
```

---

## 📊 Monitor Your Agent

### Real-time Monitoring

```bash
# View logs
lk agent logs aime-voice-agent --follow

# View metrics
lk agent metrics aime-voice-agent

# View active rooms
lk room list
```

### LiveKit Cloud Dashboard

Go to https://cloud.livekit.io/ and view:
- 📞 Active calls
- 📊 Usage metrics
- 💰 Billing
- 🔍 Logs
- ⚙️ Settings

---

## 🔧 Troubleshooting

### Agent won't deploy

**Solution**: Check logs
```bash
lk agent logs aime-voice-agent
```

Common issues:
- Missing dependencies in requirements.txt
- Python version mismatch
- Environment variables not set

### Agent deployed but not answering calls

**Solution**: Check dispatch rules
```bash
lk sip dispatch list
```

Verify:
- SIP trunk is connected
- Dispatch rule points to your agent
- Phone number is configured

### Agent can't reach OpenClaw bridge

**Solution**: Expose local server

For development:
```bash
# Use ngrok or cloudflared
ngrok http 3000

# Update agent env
lk agent env set OPENCLAW_BASE_URL=https://your-ngrok-url.ngrok.io
```

For production:
- Deploy OpenClaw to a public server
- Use the public URL

### High latency or dropped calls

**Solution**: Check region
```bash
lk cloud project show
```

Ensure your LiveKit region is close to:
- Your users (for voice quality)
- Your OpenClaw server (for API calls)

---

## 💰 Cost Optimization

### LiveKit Cloud Pricing

- **Ingress**: $0.01 per minute (phone calls in)
- **Egress**: $0.01 per minute (phone calls out)
- **Compute**: Included in minute pricing
- **First 10,000 minutes/month**: FREE

### Monitor Usage

```bash
lk cloud usage
```

### Tips to Reduce Costs

1. **Use Efficient Models**: T0-T3 routing already saves 90%+
2. **Optimize Response Time**: Faster = fewer billable minutes
3. **Implement Call Screening**: Filter spam calls before agent engages
4. **Use Webhooks**: Don't poll GHL, react to events

---

## 🚀 Production Checklist

Before going live:

- [ ] Agent deployed and tested in playground
- [ ] SIP trunk configured and working
- [ ] Phone number purchased and configured
- [ ] OpenClaw deployed to public server (not localhost)
- [ ] All environment variables set correctly
- [ ] Error handling tested (what happens if GHL is down?)
- [ ] Cost monitoring configured
- [ ] Backup/failover plan in place
- [ ] Logging and monitoring configured
- [ ] Security review completed

---

## 📖 Additional Resources

### LiveKit Documentation
- **Agents**: https://docs.livekit.io/agents/
- **SIP**: https://docs.livekit.io/sip/
- **Deployment**: https://docs.livekit.io/agents/ops/deployment/

### Testing Tools
- **Agents Playground**: https://agents-playground.livekit.io/
- **SIP Tester**: https://docs.livekit.io/sip/testing/

### Support
- **LiveKit Discord**: https://livekit.io/discord
- **Documentation**: https://docs.livekit.io/
- **GitHub**: https://github.com/livekit

---

## 🎯 Quick Reference

### Common Commands

```bash
# Authentication
lk cloud auth

# List projects
lk cloud project list

# Deploy agent
cd agents
lk agent create --name aime-voice-agent --file voice_agent.py

# View logs
lk agent logs aime-voice-agent --follow

# Set environment variable
lk agent env set KEY=value

# List active rooms
lk room list

# Test in playground
# Go to: https://agents-playground.livekit.io/
```

---

**You're now ready to deploy AIME to LiveKit Cloud! 🚀**

Start with Step 1 and work your way through. If you run into issues, check the Troubleshooting section or LiveKit documentation.
