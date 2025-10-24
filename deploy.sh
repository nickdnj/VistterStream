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
  err "Neither docker
