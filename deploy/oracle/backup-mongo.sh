#!/usr/bin/env bash
# =============================================================================
# ZipStore - MongoDB backup on the OCI VM.
#   sudo bash deploy/oracle/backup-mongo.sh
#
# Dumps the mongo volume as a tar.gz archive and keeps the last N files.
# Default location: <repo>/backups  (override with BACKUP_DIR=/some/path).
#
# Scheduled via cron, e.g. (daily 02:30). Run: crontab -e
#   30 2 * * * /usr/bin/bash /opt/zipstore/deploy/oracle/backup-mongo.sh >/dev/null 2>&1
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${REPO_DIR}/backups}"
KEEP="${KEEP:-7}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${BACKUP_DIR}/mongo-dump-${STAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "==> Dumping MongoDB (db=zipstore)..."
docker compose -f "${REPO_DIR}/docker-compose.oci.yml" -p zipstore exec -T mongo \
  mongodump --archive --gzip --db zipstore > "$OUT"

echo "==> Backup written: $OUT ($(du -h "$OUT" | cut -f1))"

echo "==> Cleaning up backups older than $KEEP days..."
find "$BACKUP_DIR" -name 'mongo-dump-*.tar.gz' -mtime +"$KEEP" -delete

ls -lh "$BACKUP_DIR"
