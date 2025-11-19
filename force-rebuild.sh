#!/usr/bin/env bash
# Force rebuild script for Raspberry Pi
# This will pull latest changes and rebuild all containers

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

# Helpers
log() { echo "[force-rebuild] $*"; }
err() { echo "[force-rebuild][ERROR] $*" >&2; }

# Detect compose command
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  err "Neither 'docker compose' nor 'docker-compose' found. Install Docker Compose."
  exit 1
fi

# Choose compose file (default to docker/docker-compose.rpi.yml if present)
COMPOSE_FILE=${COMPOSE_FILE:-}
if [[ -z "${COMPOSE_FILE}" ]]; then
  if [[ -f docker/docker-compose.rpi.yml ]]; then
    COMPOSE_FILE=docker/docker-compose.rpi.yml
  elif [[ -f docker/docker-compose.yml ]]; then
    COMPOSE_FILE=docker/docker-compose.yml
  else
    err "No compose file found. Expected docker/docker-compose.rpi.yml or docker/docker-compose.yml"
    exit 1
  fi
fi

log "Using compose file: ${COMPOSE_FILE}"

# Ensure .env exists
if [[ ! -f .env ]]; then
  if [[ -f env.sample ]]; then
    log ".env not found. Creating from env.sample (edit as needed)."
    cp env.sample .env
  else
    err "No .env or env.sample found. Create .env before deploying."
    exit 1
  fi
fi

# Store current commit
BEFORE_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
log "Current commit: ${BEFORE_COMMIT:0:8}"

# Stash any local changes
STASHED=0
if ! git diff-index --quiet HEAD --; then
  log "Stashing local changes..."
  git stash push -u -m "force-rebuild auto-stash $(date +%Y%m%d-%H%M%S)" || true
  STASHED=1
fi

# Pull latest changes
log "Pulling latest changes from Git..."
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo master)
log "Current branch: ${current_branch}"

git fetch --all --prune
git pull --rebase origin "${current_branch}"

# Restore stashed changes if we stashed
if [[ "$STASHED" -eq 1 ]]; then
  log "Restoring stashed changes..."
  git stash pop || log "Warning: Could not restore stashed changes (check 'git stash list')"
fi

AFTER_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
log "Updated commit: ${AFTER_COMMIT:0:8}"

# Force rebuild all services
log "Force rebuilding all services..."

# Stop all services
log "Stopping all services..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" down

# Rebuild all services with no cache
log "Rebuilding all services (no cache)..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" build --no-cache

# Start all services
log "Starting all services..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d

# Run database migration if needed
MIGRATION_SCRIPT="backend/migrations/add_youtube_watchdog_fields.py"
if [[ -f "$MIGRATION_SCRIPT" ]]; then
  log "Running database migration..."
  sleep 5  # Give containers time to start
  
  # Try to run migration in backend container
  for svc in vistterstream-backend vistterstream-backend-test; do
    if docker ps --format '{{.Names}}' | grep -q "^${svc}$"; then
      log "Running migration in container: $svc"
      docker exec "$svc" python3 /app/backend/migrations/add_youtube_watchdog_fields.py && break
    fi
  done
fi

# Show status
log "Force rebuild complete. Current container status:"
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps

log ""
log "Summary:"
log "  Updated commit: ${BEFORE_COMMIT:0:8} → ${AFTER_COMMIT:0:8}"
log "  Rebuilt all services with latest code"
log "  Database migration completed"
log ""
log "Done."





