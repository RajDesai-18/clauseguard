#!/usr/bin/env bash
#
# ClauseGuard production restore.
#
# Restores a backup created by backup.sh from Cloudflare R2. Downloads the
# chosen timestamped folder (db.sql.gz + minio.tar.gz) and restores BOTH:
#   - Postgres database (dropped/recreated objects via the dump's --clean)
#   - MinIO data volume (wiped and repopulated from the tar)
#
# Because Postgres rows reference MinIO objects, this restores both together.
# It never restores one without the other.
#
# Usage (from the repo root on the VPS):
#   ./deploy/restore.sh                 # lists available backups, then prompts
#   ./deploy/restore.sh 2026-07-22T17-43-43Z   # restore a specific backup
#
# WARNING: this OVERWRITES the current database and MinIO volume. Destructive.

set -euo pipefail

# --- Configuration ---------------------------------------------------------
COMPOSE="docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml"
PG_SERVICE="postgres"
PG_USER="clauseguard"
PG_DB="clauseguard"
MINIO_SERVICE="minio"
MINIO_VOLUME="clauseguard_minio_data"
RCLONE_REMOTE="r2:clauseguard-backups"

log() {
  echo "[$(date -u +%H:%M:%S)] $*"
}

# --- Select which backup to restore ---------------------------------------
BACKUP_ID="${1:-}"

if [[ -z "${BACKUP_ID}" ]]; then
  echo "Available backups:"
  rclone lsf "${RCLONE_REMOTE}" --dirs-only | sed 's:/$::' | sort
  echo
  read -rp "Enter the backup timestamp to restore: " BACKUP_ID
fi

if [[ -z "${BACKUP_ID}" ]]; then
  echo "ERROR: no backup selected." >&2
  exit 1
fi

REMOTE_DIR="${RCLONE_REMOTE}/${BACKUP_ID}"

# Verify the backup exists and has both files.
if ! rclone lsf "${REMOTE_DIR}/" | grep -q "db.sql.gz"; then
  echo "ERROR: '${REMOTE_DIR}' does not contain db.sql.gz. Aborting." >&2
  exit 1
fi
if ! rclone lsf "${REMOTE_DIR}/" | grep -q "minio.tar.gz"; then
  echo "ERROR: '${REMOTE_DIR}' does not contain minio.tar.gz. Aborting." >&2
  exit 1
fi

# --- Confirm (destructive) -------------------------------------------------
echo
echo "About to restore backup: ${BACKUP_ID}"
echo "This will OVERWRITE the current Postgres database AND MinIO volume."
read -rp "Type 'yes' to proceed: " CONFIRM
if [[ "${CONFIRM}" != "yes" ]]; then
  echo "Aborted."
  exit 0
fi

# --- Download --------------------------------------------------------------
STAGING="$(mktemp -d /tmp/clauseguard-restore.XXXXXX)"
cleanup() {
  rm -rf "${STAGING}"
}
trap cleanup EXIT

log "Downloading backup ${BACKUP_ID}..."
rclone copy "${REMOTE_DIR}/db.sql.gz"    "${STAGING}/" --s3-no-check-bucket
rclone copy "${REMOTE_DIR}/minio.tar.gz" "${STAGING}/" --s3-no-check-bucket

# --- 1. Restore Postgres ---------------------------------------------------
# The dump was created with --clean --if-exists, so it drops existing objects
# before recreating them. Piping into psql applies it in one transaction-ish
# pass. We restore into the maintenance DB connection to the target db.
log "Restoring Postgres database '${PG_DB}'..."
gunzip -c "${STAGING}/db.sql.gz" \
  | ${COMPOSE} exec -T "${PG_SERVICE}" psql -U "${PG_USER}" -d "${PG_DB}"
log "Postgres restore complete."

# --- 2. Restore MinIO volume ----------------------------------------------
# Stop MinIO so nothing is writing to the volume, wipe it, untar the backup
# into it via a throwaway alpine container, then start MinIO again.
log "Stopping MinIO..."
${COMPOSE} stop "${MINIO_SERVICE}"

log "Wiping and repopulating MinIO volume '${MINIO_VOLUME}'..."
docker run --rm \
  -v "${MINIO_VOLUME}:/data" \
  -v "${STAGING}:/backup:ro" \
  alpine:3.20 \
  sh -c "rm -rf /data/* /data/..?* /data/.[!.]* 2>/dev/null; tar xzf /backup/minio.tar.gz -C /data"

log "Starting MinIO..."
${COMPOSE} start "${MINIO_SERVICE}"

log "Restore finished: ${BACKUP_ID}"
echo
echo "Recommend restarting the API and worker so they reconnect cleanly:"
echo "  ${COMPOSE} restart api worker"