#!/usr/bin/env bash
# =============================================================================
# ZipStore - redeploy the API after pulling new code.
#   sudo bash deploy/oracle/update-app.sh
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_DIR"

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root." >&2
  exit 1
fi

if [[ -z "$(git -C "$REPO_DIR" rev-parse --show-toplevel 2>/dev/null)" ]]; then
  echo "Not inside a git checkout - use deploy/oracle/install-repo.sh to clone first." >&2
  exit 1
fi

echo "==> Pulling latest code..."
git pull --ff-only

echo "==> Backing up MongoDB before deploy..."
bash deploy/oracle/backup-mongo.sh || true

echo "==> Rebuilding and restarting..."
docker compose -f docker-compose.oci.yml -p zipstore up -d --build

echo "==> Verifying health..."
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:5000/api/health >/dev/null 2>&1; then
    echo "==> API healthy."
    exit 0
  fi
  sleep 5
done

echo "WARNING: API did not become healthy. Logs:" >&2
docker compose -f docker-compose.oci.yml -p zipstore logs --tail 100 api >&2
exit 1
