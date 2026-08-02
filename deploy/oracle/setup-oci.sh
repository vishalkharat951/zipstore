#!/usr/bin/env bash
# =============================================================================
# ZipStore - one-shot OCI VM provisioning (Oracle Linux 8/9 or Ubuntu 22.04+)
# Run as root on a freshly created Always Free ARM VM (Ampere A1).
#
#   sudo bash deploy/oracle/setup-oci.sh
#
# Before running:
#   1. Point api.yourdomain.com -> the VM public IP (DNS A record).
#   2. Copy & edit the env file:
#        cp deploy/oracle/env.oci.example zipstore-backend/.env
#        nano zipstore-backend/.env
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

echo "==> Working directory: $REPO_DIR"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo bash deploy/oracle/setup-oci.sh" >&2
  exit 1
fi

if [[ ! -f docker-compose.oci.yml ]]; then
  echo "docker-compose.oci.yml not found in $REPO_DIR - run this script from the repo root." >&2
  exit 1
fi

# --- Detect distro ----------------------------------------------------------
. /etc/os-release
echo "==> Detected: $PRETTY_NAME"

install_basics() {
  export DEBIAN_FRONTEND=noninteractive
  if command -v dnf >/dev/null 2>&1; then
    dnf -y install curl git nginx certbot python3-certbot-nginx
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y curl git nginx certbot python3-certbot-nginx
  else
    echo "Unsupported distro. Install docker, compose, nginx and certbot manually." >&2
    exit 1
  fi
}

# --- Docker + Compose plugin ------------------------------------------------
install_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "==> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
  fi
  systemctl enable --now docker
  if ! docker compose version >/dev/null 2>&1; then
    echo "==> Installing docker compose plugin..."
    mkdir -p /usr/local/lib/docker/cli-plugins
    ARCH="$(uname -m | sed 's/aarch64/arm64/; s/x86_64/amd64/')"
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  fi
  docker compose version
}

# --- Firewall (host-level). OCI Security Lists must also allow 22/80/443 ---
configure_firewall() {
  if command -v ufw >/dev/null 2>&1; then
    ufw allow OpenSSH
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
  fi
  if command -v firewall-cmd >/dev/null 2>&1; then
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
  fi
}

# --- Environment ------------------------------------------------------------
prepare_env() {
  if [[ ! -f zipstore-backend/.env ]]; then
    echo "==> zipstore-backend/.env missing - creating from example."
    cp deploy/oracle/env.oci.example zipstore-backend/.env
    echo "    EDIT IT NOW: nano zipstore-backend/.env"
    echo "    (JWT_SECRET, PHONEPE_MERCHANT_ID, PHONEPE_SALT_KEY, PHONEPE_CALLBACK_URL)"
  fi
}

# --- Build & start ----------------------------------------------------------
start_stack() {
  echo "==> Building and starting containers..."
  docker compose -f docker-compose.oci.yml -p zipstore up -d --build
  echo "==> Waiting for API health..."
  for i in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:5000/api/health >/dev/null 2>&1; then
      echo "==> API is healthy."
      return 0
    fi
    sleep 5
  done
  echo "WARNING: API did not become healthy in time. Check logs: docker compose -f docker-compose.oci.yml -p zipstore logs api" >&2
}

# --- TLS via certbot --------------------------------------------------------
get_cert() {
  local domain="${1:-}"
  if [[ -z "$domain" ]]; then
    echo "==> Skipping certbot (no domain given). Run manually:"
    echo "    certbot --nginx -d api.yourdomain.com"
    return 0
  fi
  sed -i "s/api\.yourdomain\.com/${domain}/g" deploy/oracle/nginx/zipstore.conf
  cp deploy/oracle/nginx/zipstore.conf /etc/nginx/conf.d/zipstore.conf
  nginx -t
  systemctl reload nginx || systemctl restart nginx
  certbot --nginx -d "$domain" --non-interactive --agree-tos --register-unsafely-without-email --redirect
  systemctl reload nginx
}

install_basics
install_docker
configure_firewall
prepare_env
start_stack
get_cert "${1:-}"

echo
echo "======================================================================"
echo " Done. Next steps:"
echo "   1. TLS:    certbot --nginx -d api.yourdomain.com  (if not done above)"
echo "   2. Data:   deploy/oracle/migrate-data.md  (dump from Render/Atlas -> OCI)"
echo "   3. Frontend: set js/config.js __API_BASE__ to https://api.yourdomain.com/api"
echo "      and re-deploy to GitHub Pages."
echo "   4. Deploy: sudo bash deploy/oracle/update-app.sh  (after future git pulls)"
echo "   5. Backup: sudo bash deploy/oracle/backup-mongo.sh"
echo "======================================================================"
