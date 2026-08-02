#!/usr/bin/env bash
# =============================================================================
# ZipStore - restore a MongoDB backup on the OCI VM.
#   sudo bash deploy/oracle/restore-mongo.sh /path/to/mongo-dump-XXXX.tar.gz
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_FILE="${1:-}"

if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "Usage: $0 /path/to/mongo-dump-YYYYMMDD-HHMMSS.tar.gz" >&2
  exit 1
fi

echo "==> Restoring $BACKUP_FILE into mongo (db=zipstore)..."
docker compose -f "${REPO_DIR}/docker-compose.oci.yml" -p zipstore exec -T mongo \
  mongorestore --archive --gzip --db zipstore --drop < "$BACKUP_FILE"

echo "==> Restore complete."
