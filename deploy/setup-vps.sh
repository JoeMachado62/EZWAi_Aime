#!/bin/bash
set -euo pipefail

# =============================================================================
# AIME VPS Setup Script — Ubuntu 24.04
# Run as root: sudo bash deploy/setup-vps.sh
# =============================================================================

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  echo "Usage: sudo bash deploy/setup-vps.sh <your-domain.com>"
  echo "Example: sudo bash deploy/setup-vps.sh aime.ezwai.com"
  exit 1
fi

echo "=== AIME VPS Setup (domain: $DOMAIN) ==="

# --- System updates ---
echo "[1/9] System updates..."
apt update && apt upgrade -y

# --- Node.js 22 LTS ---
echo "[2/9] Installing Node.js 22..."
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs build-essential libsqlite3-dev libvips-dev

# --- pnpm via corepack ---
echo "[3/9] Setting up pnpm..."
corepack enable
corepack prepare pnpm@10.23.0 --activate

# --- Bun (required by OpenClaw build) ---
echo "[4/9] Installing Bun..."
if ! command -v bun &> /dev/null; then
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
fi

# --- Python 3 ---
echo "[5/9] Installing Python 3..."
apt install -y python3 python3-pip python3-venv

# --- Caddy ---
echo "[6/9] Installing Caddy..."
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg 2>/dev/null || true
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy

# --- PM2 ---
echo "[7/9] Installing PM2..."
npm install -g pm2

# --- App user + directory ---
echo "[8/9] Creating aime user..."
useradd -m -s /bin/bash aime 2>/dev/null || true
mkdir -p /opt/aime
chown -R aime:aime /opt/aime

# --- Firewall ---
echo "[9/9] Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# --- Configure Caddy ---
echo "=== Configuring Caddy for $DOMAIN ==="
cat > /etc/caddy/Caddyfile <<CADDYEOF
$DOMAIN {
    # OpenClaw Gateway (WebSocket + HTTP)
    handle /ws* {
        reverse_proxy localhost:18789
    }
    handle /api/* {
        reverse_proxy localhost:18789
    }

    # Telnyx voice webhook
    handle /voice/* {
        reverse_proxy localhost:3334
    }

    # AIME HTTP server (default)
    handle {
        reverse_proxy localhost:3000
    }
}
CADDYEOF
systemctl reload caddy

# --- Create systemd service ---
echo "=== Creating systemd service ==="
cp /opt/aime/app/deploy/openclaw-gateway.service /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Clone the repo:    sudo -u aime git clone https://github.com/JoeMachado62/EZWAi_Aime.git /opt/aime/app"
echo "  2. Build:             cd /opt/aime/app && sudo -u aime pnpm install && sudo -u aime pnpm build"
echo "  3. Create .env:       cp /opt/aime/app/deploy/.env.vps.example /opt/aime/app/.env && nano /opt/aime/app/.env"
echo "  4. Create config:     sudo -u aime mkdir -p /home/aime/.openclaw/workspace"
echo "                        cp /opt/aime/app/deploy/openclaw.json.template /home/aime/.openclaw/openclaw.json"
echo "  5. Start:             sudo systemctl enable --now openclaw-gateway"
echo "  6. Verify:            curl https://$DOMAIN/api/health"
echo "  7. Set Telnyx webhook: (see deploy/README.md)"
echo ""
