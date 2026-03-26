#!/bin/bash
# VistterStream Backup — Daily SQLite DB + uploads to Google Drive (personal account)
#
# Cron: 0 3 * * * /home/nickd/VistterStream/scripts/backup-to-gdrive.sh

set -euo pipefail

GDRIVE_REMOTE="gdrive-personal"
GDRIVE_PATH="Backups/VistterStream"
BACKUP_DIR="/tmp/vistterstream-backup"
RETENTION_DAYS=30
LOG_FILE="/var/log/vistterstream-backup.log"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() {
  echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

cleanup() {
  rm -rf "$BACKUP_DIR"
}
trap cleanup EXIT

mkdir -p "$BACKUP_DIR"

# --- 1. Backup SQLite database ---
log "Starting VistterStream database backup..."

VOLUME_PATH=$(docker volume inspect docker_vistter_data -f '{{.Mountpoint}}' 2>/dev/null | tr -d '\n' || docker volume inspect vistter_data -f '{{.Mountpoint}}' | tr -d '\n')
sudo sqlite3 "${VOLUME_PATH}/vistterstream.db" ".backup '${BACKUP_DIR}/vistterstream-${DATE}.db'"

DB_SIZE=$(du -h "$BACKUP_DIR/vistterstream-${DATE}.db" | cut -f1)
log "Database snapshot: $DB_SIZE"

# Upload DB snapshot
rclone copy "$BACKUP_DIR/vistterstream-${DATE}.db" "${GDRIVE_REMOTE}:${GDRIVE_PATH}/db/" --log-file="$LOG_FILE" --log-level=INFO
log "Database uploaded to ${GDRIVE_PATH}/db/vistterstream-${DATE}.db"

# --- 2. Sync uploads (preset thumbnails, etc.) ---
log "Syncing uploads..."

UPLOADS_PATH="${VOLUME_PATH}/uploads"
if [ -d "$UPLOADS_PATH" ]; then
  UPLOAD_COUNT=$(find "$UPLOADS_PATH" -type f | wc -l | tr -d ' ')
  log "Found $UPLOAD_COUNT upload files"
  sudo rclone sync "$UPLOADS_PATH/" "${GDRIVE_REMOTE}:${GDRIVE_PATH}/uploads/" --log-file="$LOG_FILE" --log-level=INFO
  log "Uploads synced to ${GDRIVE_PATH}/uploads/"
else
  log "No uploads directory found, skipping"
fi

# --- 3. Backup .env (contains tunnel token, secrets) ---
log "Backing up environment config..."
if [ -f /home/nickd/VistterStream/.env ]; then
  cp /home/nickd/VistterStream/.env "$BACKUP_DIR/env-${DATE}.txt"
  rclone copy "$BACKUP_DIR/env-${DATE}.txt" "${GDRIVE_REMOTE}:${GDRIVE_PATH}/config/" --log-file="$LOG_FILE" --log-level=INFO
  log "Environment config backed up"
fi

# --- 4. Prune old DB snapshots ---
log "Pruning backups older than ${RETENTION_DAYS} days..."

CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)
rclone lsf "${GDRIVE_REMOTE}:${GDRIVE_PATH}/db/" 2>/dev/null | while read -r file; do
  FILE_DATE=$(echo "$file" | grep -oP '\d{4}-\d{2}-\d{2}' || true)
  if [ -n "$FILE_DATE" ] && [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
    rclone deletefile "${GDRIVE_REMOTE}:${GDRIVE_PATH}/db/${file}" --log-file="$LOG_FILE"
    log "Pruned old backup: $file"
  fi
done

log "VistterStream backup complete."
