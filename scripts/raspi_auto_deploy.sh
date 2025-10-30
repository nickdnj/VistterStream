#!/usr/bin/env bash
# Automated deploy helper for Raspberry Pi hosts.
# - Checks remote instructions for target branch/script
# - Supports host-specific overrides so multiple agents can coordinate
# - Keeps repo in sync with GitHub
# - Delegates build logic to deploy.sh (or custom script)

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

log() { echo "[auto-deploy] $*"; }
err() { echo "[auto-deploy][ERROR] $*" >&2; }

trim() {
  local var="$1"
  var="${var#${var%%[![:space:]]*}}"
  var="${var%${var##*[![:space:]]}}"
  printf '%s' "$var"
}

apply_instruction_stream() {
  local context="$1" allow_branch_override="$2" line raw_key value base target should_apply
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line=$(trim "$line")
    [[ -z "$line" ]] && continue
    [[ "$line" != *=* ]] && continue

    raw_key=$(trim "${line%%=*}")
    value=$(trim "${line#*=}")

    if [[ "$raw_key" =~ ^([A-Za-z0-9_-]+)(\[(.+)\])?$ ]]; then
      base="${BASH_REMATCH[1]}"
      target="${BASH_REMATCH[3]}"
    else
      base="$raw_key"
      target=""
    fi

    should_apply=1
    if [[ -n "$target" && "$target" != "$HOST_ID" ]]; then
      should_apply=0
    fi
    if [[ "$should_apply" -eq 0 ]]; then
      continue
    fi

    case "$base" in
      branch)
        if [[ -z "$value" ]]; then
          continue
        fi
        if [[ "$allow_branch_override" == "1" ]]; then
          TARGET_BRANCH="$value"
        elif [[ "$value" != "$TARGET_BRANCH" ]]; then
          log "Note: $context branch directive '$value' ignored (currently on '$TARGET_BRANCH')"
        fi
        ;;
      script)
        if [[ -n "$value" ]]; then
          DEPLOY_SCRIPT="$value"
        fi
        ;;
      args)
        if [[ -n "$value" ]]; then
          # shellcheck disable=SC2206
          DEPLOY_ARGS=(${value})
        fi
        ;;
      instruction_file)
        if [[ -n "$value" ]]; then
          if [[ "$allow_branch_override" == "1" ]]; then
            INSTRUCTION_FILE="$value"
          else
            log "Note: $context instruction_file directive ignored after checkout"
          fi
        fi
        ;;
      *)
        log "Ignoring unknown $context instruction key: $raw_key"
        ;;
    esac
  done
}

REMOTE="${AUTO_DEPLOY_REMOTE:-origin}"
INSTRUCTION_FILE="${AUTO_DEPLOY_INSTRUCTION_FILE:-deploy/auto-deploy.conf}"
HOST_ID="${AUTO_DEPLOY_ID:-$(hostname -s 2>/dev/null || hostname)}"

if ! command -v git >/dev/null 2>&1; then
  err "git is required on the host"
  exit 1
fi

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [[ -z "$CURRENT_BRANCH" || "$CURRENT_BRANCH" == "HEAD" ]]; then
  err "Repository is in a detached HEAD state. Check out a branch before running auto deploy."
  exit 1
fi

TARGET_BRANCH="$CURRENT_BRANCH"
DEPLOY_SCRIPT="./deploy.sh"
DEPLOY_ARGS=()

log "Repository root: $REPO_DIR"
log "Host identifier: $HOST_ID"
log "Current branch: $CURRENT_BRANCH"
log "Checking remote '$REMOTE' for updates..."

git fetch "$REMOTE" --prune

CONTROL_BRANCH="${AUTO_DEPLOY_CONTROL_BRANCH:-}"
if [[ -z "$CONTROL_BRANCH" ]]; then
  CONTROL_BRANCH=$(git symbolic-ref --quiet --short "refs/remotes/${REMOTE}/HEAD" 2>/dev/null || echo "")
  CONTROL_BRANCH="${CONTROL_BRANCH#${REMOTE}/}"
fi
if [[ -z "$CONTROL_BRANCH" ]]; then
  CONTROL_BRANCH="$CURRENT_BRANCH"
fi

REMOTE_CONTROL_REF="$REMOTE/$CONTROL_BRANCH:$INSTRUCTION_FILE"
if git cat-file -e "$REMOTE_CONTROL_REF" 2>/dev/null; then
  log "Applying remote instructions from $REMOTE_CONTROL_REF"
  apply_instruction_stream "remote" 1 < <(git show "$REMOTE_CONTROL_REF") || true
else
  log "No remote instruction file found at $REMOTE_CONTROL_REF; using defaults."
fi

if [[ "$TARGET_BRANCH" != "$CURRENT_BRANCH" ]]; then
  log "Switching to target branch '$TARGET_BRANCH'"
  if ! git ls-remote --exit-code "$REMOTE" "refs/heads/$TARGET_BRANCH" >/dev/null 2>&1; then
    err "Target branch '$TARGET_BRANCH' not found on remote '$REMOTE'"
    exit 1
  fi
  if git show-ref --verify --quiet "refs/heads/$TARGET_BRANCH"; then
    git checkout "$TARGET_BRANCH"
  else
    git checkout -t "$REMOTE/$TARGET_BRANCH"
  fi
else
  log "Staying on branch '$TARGET_BRANCH'"
fi

log "Pulling latest commits for '$TARGET_BRANCH' from '$REMOTE'"
if ! git pull --ff-only "$REMOTE" "$TARGET_BRANCH"; then
  err "git pull failed. Resolve issues and rerun."
  exit 1
fi

if [[ -f "$INSTRUCTION_FILE" ]]; then
  log "Applying local instructions from $INSTRUCTION_FILE"
  apply_instruction_stream "local" 0 < "$INSTRUCTION_FILE"
else
  log "No local instruction file present; using defaults."
fi

if [[ ! -e "$DEPLOY_SCRIPT" ]]; then
  err "Deploy script '$DEPLOY_SCRIPT' not found"
  exit 1
fi
if [[ ! -x "$DEPLOY_SCRIPT" ]]; then
  log "Making deploy script executable: $DEPLOY_SCRIPT"
  chmod +x "$DEPLOY_SCRIPT"
fi

log "Final target branch: $TARGET_BRANCH"
log "Executing on host '$HOST_ID' using: $DEPLOY_SCRIPT ${DEPLOY_ARGS[*]}"

log "Invoking $DEPLOY_SCRIPT ${DEPLOY_ARGS[*]}"
"$DEPLOY_SCRIPT" "${DEPLOY_ARGS[@]}"
