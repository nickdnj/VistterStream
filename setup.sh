#!/bin/bash
# VistterStream — Setup Script
# Run after cloning: ./setup.sh
#
# Supports two modes:
#   1. Fresh install — generates .env, builds Docker, starts services
#   2. Restore from backup — pulls latest DB + config from Google Drive

set -euo pipefail

COMPOSE_FILE="docker/docker-compose.rpi.yml"
GDRIVE_REMOTE="gdrive-personal"
GDRIVE_PATH="Backups/VistterStream"

echo "=============================="
echo "  VistterStream — Setup"
echo "=============================="
echo ""

# --- Check prerequisites ---
echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker is not installed."; exit 1; }
command -v docker compose version >/dev/null 2>&1 || { echo "ERROR: Docker Compose is not installed."; exit 1; }
echo "  Docker: $(docker --version | cut -d' ' -f3)"

HAS_RCLONE=false
if command -v rclone >/dev/null 2>&1; then
  HAS_RCLONE=true
  echo "  rclone: $(rclone version | head -1)"
else
  echo "  rclone: not installed (needed for restore/backup)"
fi

echo ""

# --- Choose mode ---
echo "Select setup mode:"
echo "  1) Fresh install (new database)"
echo "  2) Restore from Google Drive backup"
echo ""
read -rp "Choice [1/2]: " MODE

case "$MODE" in
  2)
    if [ "$HAS_RCLONE" = false ]; then
      echo "ERROR: rclone is required for restore. Install with: curl https://rclone.org/install.sh | sudo bash"
      exit 1
    fi

    if ! rclone lsd "${GDRIVE_REMOTE}:" >/dev/null 2>&1; then
      echo "ERROR: rclone remote '${GDRIVE_REMOTE}' is not configured."
      echo "Run 'rclone config' to set up Google Drive access."
      exit 1
    fi

    echo ""
    echo "Available backups:"
    rclone lsf "${GDRIVE_REMOTE}:${GDRIVE_PATH}/db/" 2>/dev/null | sort -r | head -10

    echo ""
    LATEST=$(rclone lsf "${GDRIVE_REMOTE}:${GDRIVE_PATH}/db/" 2>/dev/null | sort -r | head -1)
    read -rp "Which backup to restore? [${LATEST}]: " BACKUP_FILE
    BACKUP_FILE="${BACKUP_FILE:-$LATEST}"

    echo "Downloading ${BACKUP_FILE}..."
    mkdir -p /tmp/vistterstream-restore
    rclone copy "${GDRIVE_REMOTE}:${GDRIVE_PATH}/db/${BACKUP_FILE}" /tmp/vistterstream-restore/

    echo "Downloading uploads..."
    rclone copy "${GDRIVE_REMOTE}:${GDRIVE_PATH}/uploads/" /tmp/vistterstream-restore/uploads/ 2>/dev/null || echo "  No uploads to restore"

    # Restore .env from backup if no local one
    if [ ! -f .env ]; then
      echo "Restoring .env from backup..."
      LATEST_ENV=$(rclone lsf "${GDRIVE_REMOTE}:${GDRIVE_PATH}/config/" 2>/dev/null | sort -r | head -1)
      if [ -n "$LATEST_ENV" ]; then
        rclone copy "${GDRIVE_REMOTE}:${GDRIVE_PATH}/config/${LATEST_ENV}" /tmp/vistterstream-restore/
        cp "/tmp/vistterstream-restore/${LATEST_ENV}" .env
        echo "  .env restored from ${LATEST_ENV}"
      else
        echo "  No .env backup found"
      fi
    fi
    ;;
  *)
    MODE=1
    ;;
esac

# --- Create .env if missing ---
if [ ! -f .env ]; then
  echo ""
  echo "Creating .env file..."
  JWT_SECRET=$(openssl rand -hex 32)
  ENCRYPTION_KEY=$(openssl rand -base64 32)

  read -rp "Admin password [cathie19]: " ADMIN_PASS
  ADMIN_PASS="${ADMIN_PASS:-cathie19}"

  read -rp "Cloudflare tunnel token (from dashboard): " TUNNEL_TOKEN

  cat > .env << EOF
JWT_SECRET_KEY=${JWT_SECRET}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
DEFAULT_ADMIN_PASSWORD=${ADMIN_PASS}
CLOUDFLARE_TUNNEL_TOKEN=${TUNNEL_TOKEN}
TUNNEL_TOKEN=${TUNNEL_TOKEN}
DATABASE_URL=sqlite:////data/vistterstream.db
UPLOADS_DIR=/data/uploads
EOF
  echo "  .env created with generated secrets"
else
  echo "  .env already exists, skipping"
fi

# --- Build and start ---
echo ""
echo "Building Docker images..."
docker compose -f "$COMPOSE_FILE" --env-file .env build

echo "Starting services..."
docker compose -f "$COMPOSE_FILE" --env-file .env up -d

sleep 5

# --- Restore database if mode 2 ---
if [ "$MODE" = "2" ]; then
  echo "Restoring database from backup..."
  docker compose -f "$COMPOSE_FILE" stop backend
  VOLUME_PATH=$(docker volume inspect docker_vistter_data -f '{{.Mountpoint}}' 2>/dev/null | tr -d '\n' || docker volume inspect vistter_data -f '{{.Mountpoint}}' | tr -d '\n')
  sudo cp "/tmp/vistterstream-restore/${BACKUP_FILE}" "${VOLUME_PATH}/vistterstream.db"

  if [ -d /tmp/vistterstream-restore/uploads ]; then
    echo "Restoring uploads..."
    sudo cp -r /tmp/vistterstream-restore/uploads/* "${VOLUME_PATH}/uploads/" 2>/dev/null || true
  fi

  docker compose -f "$COMPOSE_FILE" --env-file .env up -d
  rm -rf /tmp/vistterstream-restore
  echo "Database restored from ${BACKUP_FILE}"
  sleep 5
fi

# --- Verify ---
echo ""
echo "Checking services..."
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'vistter|tagsmart|NAME'

echo ""
echo "=============================="
echo "  Setup complete!"
echo "=============================="
echo ""
echo "  Stream: https://stream.vistter.com"
echo "  Admin:  admin / (your password)"
echo ""
echo "  Deploy updates:  cd docker && docker compose -f docker-compose.rpi.yml --env-file ../.env up -d --build"
echo "  Manual backup:   ./scripts/backup-to-gdrive.sh"
echo "  View logs:       docker logs vistterstream-backend -f"
echo ""
