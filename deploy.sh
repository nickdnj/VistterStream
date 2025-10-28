#!/usr/bin/env bash
# VistterStream Smart Deployment Script
# - Pull latest from GitHub
# - Detect which files changed
# - Only rebuild containers affected by changes
# - Keep unchanged containers running
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

# Store current commit for change detection
BEFORE_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
log "Current commit: ${BEFORE_COMMIT:0:8}"

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

AFTER_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# Detect changed files
if [[ "$BEFORE_COMMIT" == "$AFTER_COMMIT" ]]; then
  log "No changes detected (commit ${AFTER_COMMIT:0:8}). Nothing to rebuild."
  log "All containers are up to date."
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps
  exit 0
fi

# Force rebuild if watchdog files exist but containers might be outdated
if [[ -f "backend/services/watchdog_manager.py" ]] && [[ -f "backend/services/local_stream_watchdog.py" ]]; then
  log "Watchdog files detected - ensuring containers are up to date"
  FORCE_REBUILD_BACKEND=1
fi

log "Changes detected: ${BEFORE_COMMIT:0:8} → ${AFTER_COMMIT:0:8}"
log "Analyzing changed files..."

# Get list of changed files
CHANGED_FILES=$(git diff --name-only "${BEFORE_COMMIT}" "${AFTER_COMMIT}" 2>/dev/null || echo "")

if [[ -z "$CHANGED_FILES" ]]; then
  log "No file changes detected. All containers are up to date."
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps
  exit 0
fi

# Map changed files to services
SERVICES_TO_REBUILD=()

# Check backend changes
if echo "$CHANGED_FILES" | grep -qE '^backend/' || [[ "${FORCE_REBUILD_BACKEND:-0}" -eq 1 ]]; then
  log "✓ Backend changes detected"
  SERVICES_TO_REBUILD+=("backend")
  # Also include backend-host if it's in the compose file
  if grep -q "backend-host:" "$COMPOSE_FILE"; then
    SERVICES_TO_REBUILD+=("backend-host")
  fi
fi

# Check frontend changes
if echo "$CHANGED_FILES" | grep -qE '^frontend/'; then
  log "✓ Frontend changes detected"
  SERVICES_TO_REBUILD+=("frontend")
fi

# Check RTMP relay changes
if echo "$CHANGED_FILES" | grep -qE '^docker/nginx-rtmp/'; then
  log "✓ RTMP relay changes detected"
  SERVICES_TO_REBUILD+=("rtmp-relay")
fi

# Check preview server config changes (MediaMTX)
if echo "$CHANGED_FILES" | grep -qE '^docker/mediamtx/'; then
  log "✓ Preview server config changes detected"
  SERVICES_TO_REBUILD+=("preview-server")
fi

# Check compose file changes (rebuild all if compose file changed)
if echo "$CHANGED_FILES" | grep -qE '^docker/docker-compose'; then
  log "✓ Docker Compose configuration changed - will rebuild all services"
  SERVICES_TO_REBUILD=("backend" "frontend" "rtmp-relay" "preview-server")
  if grep -q "backend-host:" "$COMPOSE_FILE"; then
    SERVICES_TO_REBUILD+=("backend-host")
  fi
fi

# Remove duplicates
SERVICES_TO_REBUILD=($(echo "${SERVICES_TO_REBUILD[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))

if [[ ${#SERVICES_TO_REBUILD[@]} -eq 0 ]]; then
  log "No service changes detected (changes in docs/scripts/tests only)."
  log "All containers are up to date."
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps
  exit 0
fi

log "Services to rebuild: ${SERVICES_TO_REBUILD[*]}"

# Optional: Run DB migration if backend changed and script exists
if [[ " ${SERVICES_TO_REBUILD[*]} " =~ " backend " ]]; then
  MIGRATION_SCRIPT="backend/migrations/add_youtube_watchdog_fields.py"
  if [[ -f "$MIGRATION_SCRIPT" ]]; then
    log "Running database migration (if needed)..."
    if command -v python3 >/dev/null 2>&1; then
      python3 "$MIGRATION_SCRIPT" || log "Migration script failed (will run inside container after start)"
    else
      log "Host python3 not found. Will run migration inside container after start."
      RUN_MIGRATION_IN_CONTAINER=1
    fi
  fi
fi

# Stop only the services that need rebuilding
log "Stopping affected services: ${SERVICES_TO_REBUILD[*]}"
for service in "${SERVICES_TO_REBUILD[@]}"; do
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" stop "$service" 2>/dev/null || log "Service $service not running"
done

# Rebuild only the affected services
log "Rebuilding affected services..."
for service in "${SERVICES_TO_REBUILD[@]}"; do
  log "  → Building $service..."
  "${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" build --no-cache "$service" || {
    err "Failed to build $service"
    exit 1
  }
done

# Start all services (this will restart rebuilt ones and ensure others are running)
log "Starting services..."
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" up -d

# If requested, run migration inside backend container
if [[ "${RUN_MIGRATION_IN_CONTAINER:-0}" -eq 1 ]]; then
  log "Running migration inside backend container..."
  sleep 3  # Give container time to start
  for svc in vistterstream-backend vistterstream-backend-host; do
    if docker ps --format '{{.Names}}' | grep -q "^${svc}$"; then
      docker exec "$svc" python3 /app/backend/migrations/add_youtube_watchdog_fields.py && RUN_MIGRATION_IN_CONTAINER=0 && break
    fi
  done
  if [[ "$RUN_MIGRATION_IN_CONTAINER" -ne 0 ]]; then
    err "Failed to run migration in container. Run manually inside backend container."
  fi
fi

# Show status
log "Deployment complete. Current container status:"
"${COMPOSE_CMD[@]}" -f "$COMPOSE_FILE" ps

# Show summary of what was done
log ""
log "Summary:"
log "  Changed commit: ${BEFORE_COMMIT:0:8} → ${AFTER_COMMIT:0:8}"
log "  Rebuilt services: ${SERVICES_TO_REBUILD[*]}"
log "  Unchanged services: kept running without interruption"
log ""
log "Done."
