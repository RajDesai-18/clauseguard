#!/usr/bin/env bash
#
# ClauseGuard production backup.
#
# Creates a single timestamped backup folder in Cloudflare R2 containing:
#   - db.sql.gz      : pg_dump of the Postgres database (gzip compressed)
#   - minio.tar.gz   : tar of the MinIO data volume (all uploaded contract files)
#
# Postgres rows reference MinIO objects, so both halves are backed up together
# under one timestamp. Restore is always "both or neither" (see restore.sh).
#
# Usage (from the repo root on the VPS):
#   ./deploy/backup.sh
#
# Requires: docker compose stack running, rclone remote "r2" configured.

set -euo pipefail

# --- Configuration ---------------------------------------------------------
COMPOSE="docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml"
PG_SERVICE="postgres"
PG_USER="clauseguard"
PG_DB="clauseguard"
MINIO_VOLUME="clauseguard_minio_data"
RCLONE_REMOTE="r2:clauseguard-backups"
RETENTION_DAYS=14   # backups in R2 older than this are pruned at the end

# --- Derived values --------------------------------------------------------
TIMESTAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
STAGING="$(mktemp -d /tmp/clauseguard-backup.XXXXXX)"
REMOTE_DIR="${RCLONE_REMOTE}/${TIMESTAMP}"

# Ensure the staging dir is always cleaned up, even on failure.
cleanup() {
  rm -rf "${STAGING}"
}
trap cleanup EXIT

log() {
  echo "[$(date -u +%H:%M:%S)] $*"
}

# --- Preflight -------------------------------------------------------------
log "Backup starting -> ${REMOTE_DIR}"

if ! rclone lsjson "${RCLONE_REMOTE}" >/dev/null 2>&1; then
  echo "ERROR: cannot reach rclone remote '${RCLONE_REMOTE}'. Is rclone configured?" >&2
  exit 1
fi

# --- 1. Postgres dump ------------------------------------------------------
log "Dumping Postgres database '${PG_DB}'..."
${COMPOSE} exec -T "${PG_SERVICE}" \
  pg_dump -U "${PG_USER}" -d "${PG_DB}" --clean --if-exists \
  | gzip -9 > "${STAGING}/db.sql.gz"

DB_SIZE="$(du -h "${STAGING}/db.sql.gz" | cut -f1)"
log "Postgres dump complete (${DB_SIZE})."

# --- 2. MinIO volume tar ---------------------------------------------------
# Run a throwaway alpine container with the MinIO volume mounted read-only,
# tar its contents to stdout, and capture it on the host. No dependency on
# MinIO being reachable over the network.
log "Archiving MinIO volume '${MINIO_VOLUME}'..."
docker run --rm \
  -v "${MINIO_VOLUME}:/data:ro" \
  alpine:3.20 \
  tar czf - -C /data . \
  > "${STAGING}/minio.tar.gz"

MINIO_SIZE="$(du -h "${STAGING}/minio.tar.gz" | cut -f1)"
log "MinIO archive complete (${MINIO_SIZE})."

# --- 3. Upload to R2 -------------------------------------------------------
log "Uploading to ${REMOTE_DIR}..."
rclone copy "${STAGING}/db.sql.gz"    "${REMOTE_DIR}/" --s3-no-check-bucket
rclone copy "${STAGING}/minio.tar.gz" "${REMOTE_DIR}/" --s3-no-check-bucket
log "Upload complete."

# --- 4. Verify -------------------------------------------------------------
log "Verifying uploaded objects..."
rclone ls "${REMOTE_DIR}"

# --- 5. Prune old backups --------------------------------------------------
# Delete backup folders older than RETENTION_DAYS. rclone's --min-age deletes
# objects whose modtime is older than the cutoff; empty dirs are then cleaned.
log "Pruning backups older than ${RETENTION_DAYS} days..."
rclone delete "${RCLONE_REMOTE}" --min-age "${RETENTION_DAYS}d" --rmdirs || true

log "Backup finished: ${TIMESTAMP}"