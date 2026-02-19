# AIME VPS Deployment

Deploy OpenClaw AIME to an Ubuntu 24.04 VPS with Caddy reverse proxy.

## Quick Start

```bash
# 1. Run setup (as root)
sudo bash deploy/setup-vps.sh aime.yourdomain.com

# 2. Clone and build (as aime user)
sudo -u aime git clone https://github.com/JoeMachado62/EZWAi_Aime.git /opt/aime/app
cd /opt/aime/app
sudo -u aime pnpm install
sudo -u aime pnpm build

# 3. Configure
cp deploy/.env.vps.example .env
nano .env  # Fill in API keys from Windows .env

sudo -u aime mkdir -p /home/aime/.openclaw/workspace
sudo -u aime cp deploy/openclaw.json.template /home/aime/.openclaw/openclaw.json
# Edit the gateway token: openssl rand -hex 24

# 4. Copy workspace files
sudo -u aime cp /path/to/SOUL.md /home/aime/.openclaw/workspace/

# 5. Start
sudo systemctl enable --now openclaw-gateway
```

## Set Telnyx Webhook URL

Once Caddy is serving HTTPS, update the Telnyx Call Control App to use
your permanent domain instead of ngrok:

```bash
curl -X PATCH "https://api.telnyx.com/v2/call_control_applications/2898506008273880267" \
  -H "Authorization: Bearer $TELNYX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"webhook_event_url": "https://aime.yourdomain.com/voice/webhook"}'
```

## Rollback to Windows/ngrok

If you need to revert the phone number back to the Windows setup:

```bash
# The watchdog.py on Windows will auto-update the webhook URL
# Just restart the Windows OpenClaw gateway
```

## Port Map

| Service           | Port  | Access                          |
|-------------------|-------|---------------------------------|
| OpenClaw Gateway  | 18789 | Caddy reverse proxy             |
| Voice Webhook     | 3334  | Caddy `/voice/*`                |
| AIME Server       | 3000  | Caddy (default handler)         |
| Caddy             | 80/443| Public (auto HTTPS)             |

## Logs

```bash
journalctl -u openclaw-gateway -f     # Gateway logs
journalctl -u caddy -f                # Caddy logs
```

## Upstream Updates

```bash
cd /opt/aime/app
git fetch upstream && git merge upstream/main
pnpm install && pnpm build
sudo systemctl restart openclaw-gateway
```
