#!/usr/bin/env bash
# Watchdog Test Script
# Kills the monitored FFmpeg process and verifies the watchdog recovers it

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helpers
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

log_info "Starting Watchdog Test..."
log_info "=========================================="

# Step 1: Check if watchdog is running
log_info "Step 1: Checking watchdog status..."
WATCHDOG_STATUS=$(curl -s http://localhost:8000/api/watchdog/status)
WATCHDOG_COUNT=$(echo "$WATCHDOG_STATUS" | grep -o '"watchdog_count":[0-9]*' | grep -o '[0-9]*' || echo "0")

if [ "$WATCHDOG_COUNT" -eq 0 ]; then
    log_error "No watchdog is running! Enable watchdog for a destination first."
    exit 1
fi

log_success "Watchdog is running (monitoring $WATCHDOG_COUNT destination(s))"

# Step 2: Find the FFmpeg process streaming to YouTube
log_info "Step 2: Finding FFmpeg process streaming to YouTube..."
FFMPEG_PIDS=$(ps aux | grep "ffmpeg.*rtmp.*youtube" | grep -v grep | awk '{print $2}' || true)

if [ -z "$FFMPEG_PIDS" ]; then
    log_error "No FFmpeg process found streaming to YouTube!"
    log_info "Make sure a timeline is running and streaming to YouTube."
    exit 1
fi

# Get the first PID (there should only be one)
FFMPEG_PID=$(echo "$FFMPEG_PIDS" | head -n1)
log_success "Found FFmpeg process: PID $FFMPEG_PID"

# Get process details
FFMPEG_CMD=$(ps -p "$FFMPEG_PID" -o cmd= 2>/dev/null || echo "")
if [ -z "$FFMPEG_CMD" ]; then
    log_error "Could not get process details for PID $FFMPEG_PID"
    exit 1
fi

log_info "FFmpeg command: ${FFMPEG_CMD:0:100}..."

# Step 3: Get initial recovery count
log_info "Step 3: Getting initial watchdog state..."
INITIAL_STATUS=$(curl -s http://localhost:8000/api/watchdog/status)
INITIAL_RECOVERY_COUNT=$(echo "$INITIAL_STATUS" | grep -o '"recovery_count":[0-9]*' | grep -o '[0-9]*' || echo "0")
log_info "Initial recovery count: $INITIAL_RECOVERY_COUNT"

# Step 4: Clear recent watchdog logs
log_info "Step 4: Preparing to monitor logs..."
CONTAINER_NAME="vistterstream-backend"
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_error "Backend container '$CONTAINER_NAME' not found!"
    exit 1
fi

# Get current log position
LOG_BEFORE_LINES=$(docker logs "$CONTAINER_NAME" 2>&1 | wc -l)

# Step 5: Kill the FFmpeg process
log_info "Step 5: Killing FFmpeg process (PID: $FFMPEG_PID)..."
if sudo kill -9 "$FFMPEG_PID" 2>/dev/null; then
    log_success "FFmpeg process killed successfully"
else
    log_error "Failed to kill FFmpeg process"
    exit 1
fi

# Verify it's dead
sleep 2
if ps -p "$FFMPEG_PID" >/dev/null 2>&1; then
    log_warning "Process still running, killing again..."
    sudo kill -9 "$FFMPEG_PID" 2>/dev/null
    sleep 1
fi

# Step 6: Wait for watchdog to detect and recover
log_info "Step 6: Waiting for watchdog to detect failure..."
log_info "Watchdog checks every 30 seconds, needs 3 consecutive failures (90 seconds total)"

CHECK_COUNT=0
MAX_CHECKS=20  # 20 checks = ~10 minutes max wait
RECOVERY_DETECTED=false
UNHEALTHY_DETECTED=false

while [ $CHECK_COUNT -lt $MAX_CHECKS ]; do
    sleep 5
    CHECK_COUNT=$((CHECK_COUNT + 1))
    
    # Check new logs for watchdog activity
    NEW_LOGS=$(docker logs "$CONTAINER_NAME" --tail 50 2>&1 | tail -n +$LOG_BEFORE_LINES)
    
    # Look for unhealthy detections
    if echo "$NEW_LOGS" | grep -q "Stream.*unhealthy"; then
        if [ "$UNHEALTHY_DETECTED" = false ]; then
            log_warning "Watchdog detected unhealthy stream!"
            UNHEALTHY_DETECTED=true
        fi
    fi
    
    # Look for recovery attempt
    if echo "$NEW_LOGS" | grep -q "RECOVERY ATTEMPT"; then
        log_success "Watchdog triggered recovery!"
        RECOVERY_DETECTED=true
        break
    fi
    
    # Check if new FFmpeg process started (early recovery detection)
    NEW_PIDS=$(ps aux | grep "ffmpeg.*rtmp.*youtube" | grep -v grep | awk '{print $2}' || true)
    if [ -n "$NEW_PIDS" ] && [ "$NEW_PIDS" != "$FFMPEG_PID" ]; then
        NEW_PID=$(echo "$NEW_PIDS" | head -n1)
        log_success "New FFmpeg process started (PID: $NEW_PID) - recovery may be in progress"
    fi
    
    # Progress indicator
    if [ $((CHECK_COUNT % 6)) -eq 0 ]; then
        log_info "Still waiting... ($((CHECK_COUNT * 5))s elapsed, checking logs...)"
    fi
done

# Step 7: Check final status
log_info "Step 7: Checking final watchdog status..."
sleep 5  # Give it time to update

FINAL_STATUS=$(curl -s http://localhost:8000/api/watchdog/status)
FINAL_RECOVERY_COUNT=$(echo "$FINAL_STATUS" | grep -o '"recovery_count":[0-9]*' | grep -o '[0-9]*' || echo "0")
FINAL_RECOVERY_TIME=$(echo "$FINAL_STATUS" | grep -o '"last_recovery_time":"[^"]*"' | cut -d'"' -f4 || echo "null")

log_info "Final recovery count: $FINAL_RECOVERY_COUNT"
log_info "Last recovery time: $FINAL_RECOVERY_TIME"

# Step 8: Check logs for recovery messages
log_info "Step 8: Analyzing logs..."
RECOVERY_LOGS=$(docker logs "$CONTAINER_NAME" --tail 200 2>&1 | grep -E "(RECOVERY|recovery|Stream.*unhealthy)" | tail -20)

if [ -n "$RECOVERY_LOGS" ]; then
    log_info "Recovery-related log entries:"
    echo "$RECOVERY_LOGS"
fi

# Step 9: Verify new FFmpeg process is running
log_info "Step 9: Verifying stream is running..."
NEW_PIDS=$(ps aux | grep "ffmpeg.*rtmp.*youtube" | grep -v grep | awk '{print $2}' || true)

# Results summary
log_info ""
log_info "=========================================="
log_info "TEST RESULTS"
log_info "=========================================="

if [ "$RECOVERY_DETECTED" = true ] || [ "$FINAL_RECOVERY_COUNT" -gt "$INITIAL_RECOVERY_COUNT" ]; then
    log_success "✓ Watchdog detected failure"
    log_success "✓ Watchdog triggered recovery"
    
    if [ -n "$NEW_PIDS" ]; then
        NEW_PID=$(echo "$NEW_PIDS" | head -n1)
        log_success "✓ New FFmpeg process running (PID: $NEW_PID)"
        log_success "✓ Stream recovered successfully!"
    else
        log_warning "⚠ Recovery triggered but no new FFmpeg process found"
        log_info "Timeline executor may be restarting the stream..."
    fi
    
    log_success ""
    log_success "TEST PASSED: Watchdog is working correctly! ✓"
    exit 0
else
    log_error "✗ Watchdog did not detect failure or trigger recovery"
    log_error ""
    log_error "Possible issues:"
    log_error "  1. Watchdog is not properly monitoring the stream"
    log_error "  2. Stream ID mismatch"
    log_error "  3. Timeline executor may have restarted it before watchdog fired"
    
    if [ "$UNHEALTHY_DETECTED" = true ]; then
        log_warning "Note: Watchdog detected unhealthy state but did not trigger recovery"
        log_warning "This could mean it hasn't reached the threshold yet (needs 3 consecutive failures)"
    fi
    
    exit 1
fi
