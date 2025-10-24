#!/usr/bin/env bash
# VistterStream Deployment Script
# - Pull latest from GitHub
# - Stop running containers
# - Rebuild images
# - Start containers
# Supports both docker compose v2 (docker compose) and legacy (docker-compose)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

# Helpers
log() { echo "[deploy] $*"; }
err() { echo "[deploy][ERROR] $*" >&2; }

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

# Ensure .env exists (used by compose)
if [[ ! -f .env ]]; then
  if [[ -f env.sample ]]; then
    log ".env not found. Creating from env.sample (edit as needed)."
    cp env.sample .env
  else
    err "No .env or env.sample found. Create .env before deploying."
    exit 1
  fi
fi

# Pull latest from git
log "Pulling latest changes from Git..."
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo master)
log "Current branch: ${current_branch}"

# Stash any local changes to avoid conflicts
STASHED=0
if ! git diff-index --quiet HEAD --; then
  log "Stashing local changes..."
  git stash push -u -m "deploy.sh auto-stash $(date +%Y%m%d-%H%M%S)" || true
  STASHED=1
fi

git fetch --all --prune
git pull --rebase origin "${current_branch}"

# Restore stashed changes if we stashed
if [[ "$STASHED" -eq 1 ]]; then
  log "Restoring stashed changes..."
  git stash pop || log "Warning: Could not restore stashed changes (check 'git stash list')"
fi

# Stop containers
log "Stopping containers..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" down --remove-orphans || true

# Optional: Run DB migration if script exists
MIGRATION_SCRIPT="backend/migrations/add_youtube_watchdog_fields.py"
if [[ -f "$MIGRATION_SCRIPT" ]]; then
  log "Running database migration (if needed)..."
  # Use host python if available or run inside backend container after build
  if command -v python3 >/dev/null 2>&1; then
    python3 "$MIGRATION_SCRIPT" || log "Migration script failed (will run inside container after start)"
  else
    log "Host python3 not found. Will run migration inside container after start."
    RUN_MIGRATION_IN_CONTAINER=1
  fi
fi

# Rebuild images
log "Building images..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" build --no-cache

# Start containers
log "Starting containers..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d

# If requested, run migration inside backend container
if [[ "${RUN_MIGRATION_IN_CONTAINER:-0}" -eq 1 ]]; then
  log "Running migration inside backend container..."
  # Try both service names (vistterstream-backend and vistterstream-backend-host)
  for svc in vistterstream-backend vistterstream-backend-host; do
    if docker ps --format '{{.Names}}' | grep -q "^${svc}$"; then
      docker exec -it "$svc" python3 /app/backend/migrations/add_youtube_watchdog_fields.py && RUN_MIGRATION_IN_CONTAINER=0 && break
    fi
  done
  if [[ "$RUN_MIGRATION_IN_CONTAINER" -ne 0 ]]; then
    err "Failed to run migration in container. Run manually inside backend container."
  fi
fi

# Show status
log "Deployment complete. Current container status:"
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps

log "Done."
