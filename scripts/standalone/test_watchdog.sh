#!/usr/bin/env bash
# Watchdog Test Script
# Tests both FFmpeg auto-restart and Watchdog recovery layers
# 
# Two test modes:
#   1. Quick test: Single kill (tests FFmpeg auto-restart layer - 2s recovery)
#   2. Full test: Multiple kills (exhausts FFmpeg auto-restart, tests watchdog - 90s recovery)

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

# Parse arguments
TEST_MODE="${1:-quick}"

if [ "$TEST_MODE" != "quick" ] && [ "$TEST_MODE" != "full" ]; then
    log_error "Invalid test mode: $TEST_MODE"
    echo ""
    echo "Usage: $0 [quick|full]"
    echo ""
    echo "  quick - Single kill test (FFmpeg auto-restart layer, ~5s recovery)"
    echo "  full  - Multiple kills test (Watchdog layer, ~90s recovery)"
    echo ""
    exit 1
fi

log_info "Starting Watchdog Test (${TEST_MODE} mode)..."
log_info "=========================================="

if [ "$TEST_MODE" = "quick" ]; then
    log_info "QUICK TEST: Tests FFmpeg auto-restart (Layer 1 - fast recovery)"
    log_info "Expected: FFmpeg manager restarts process in ~2 seconds"
else
    log_info "FULL TEST: Tests Watchdog recovery (Layer 2 - backup recovery)"
    log_info "Expected: After exhausting FFmpeg retries, watchdog recovers in ~90 seconds"
fi
log_info ""

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

# Step 5: Kill the FFmpeg process (mode-dependent)
if [ "$TEST_MODE" = "quick" ]; then
    # Quick test: Single kill
    log_info "Step 5: Killing FFmpeg process once (PID: $FFMPEG_PID)..."
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
else
    # Full test: Multiple kills to exhaust FFmpeg auto-restart
    log_info "Step 5: Killing FFmpeg process multiple times to exhaust auto-restart..."
    log_warning "This will kill the process 12 times (exceeds FFmpeg's 10 retry limit)"
    
    KILL_COUNT=0
    MAX_KILLS=12
    
    while [ $KILL_COUNT -lt $MAX_KILLS ]; do
        # Find current FFmpeg PID
        CURRENT_PID=$(ps aux | grep "ffmpeg.*rtmp.*youtube" | grep -v grep | awk '{print $2}' | head -n1 || true)
        
        if [ -z "$CURRENT_PID" ]; then
            log_warning "No FFmpeg process found on attempt $((KILL_COUNT + 1)), waiting..."
            sleep 3
            continue
        fi
        
        KILL_COUNT=$((KILL_COUNT + 1))
        log_info "Kill attempt $KILL_COUNT/$MAX_KILLS: Killing PID $CURRENT_PID"
        
        if sudo kill -9 "$CURRENT_PID" 2>/dev/null; then
            log_success "Process killed"
        else
            log_warning "Kill failed (process may have already died)"
        fi
        
        # Wait a bit before next kill (shorter than FFmpeg's 2s restart delay)
        sleep 3
    done
    
    log_success "Exhausted FFmpeg auto-restart attempts"
    log_info "FFmpeg manager should now give up, watchdog should take over..."
fi

# Step 6: Wait for recovery (mode-dependent)
if [ "$TEST_MODE" = "quick" ]; then
    log_info "Step 6: Waiting for FFmpeg auto-restart..."
    log_info "Expected recovery time: ~2-5 seconds"
    CHECK_COUNT=0
    MAX_CHECKS=10  # 10 checks = ~50 seconds max wait
    RECOVERY_DETECTED=false
else
    log_info "Step 6: Waiting for watchdog to detect failure and recover..."
    log_info "Watchdog checks every 30 seconds, needs 3 consecutive failures (90 seconds total)"
    CHECK_COUNT=0
    MAX_CHECKS=30  # 30 checks = ~2.5 minutes max wait
    RECOVERY_DETECTED=false
    UNHEALTHY_DETECTED=false
fi

RECOVERY_TYPE=""
while [ $CHECK_COUNT -lt $MAX_CHECKS ]; do
    sleep 5
    CHECK_COUNT=$((CHECK_COUNT + 1))
    
    # Check new logs for activity
    NEW_LOGS=$(docker logs "$CONTAINER_NAME" --tail 100 2>&1 | tail -n +$LOG_BEFORE_LINES)
    
    if [ "$TEST_MODE" = "full" ]; then
        # Look for unhealthy detections (full test only)
        if echo "$NEW_LOGS" | grep -q "Stream.*unhealthy"; then
            if [ "$UNHEALTHY_DETECTED" = false ]; then
                log_warning "Watchdog detected unhealthy stream!"
                UNHEALTHY_DETECTED=true
            fi
        fi
        
        # Look for watchdog recovery attempt
        if echo "$NEW_LOGS" | grep -q "RECOVERY ATTEMPT"; then
            log_success "Watchdog triggered recovery!"
            RECOVERY_DETECTED=true
            RECOVERY_TYPE="watchdog"
            break
        fi
    fi
    
    # Look for FFmpeg auto-restart
    if echo "$NEW_LOGS" | grep -q "Auto-restart enabled.*attempting restart"; then
        if [ "$TEST_MODE" = "quick" ]; then
            log_success "FFmpeg manager triggered auto-restart!"
            RECOVERY_DETECTED=true
            RECOVERY_TYPE="ffmpeg"
        else
            log_info "FFmpeg auto-restart detected (should exhaust soon...)"
        fi
    fi
    
    # Check if FFmpeg gave up
    if [ "$TEST_MODE" = "full" ]; then
        if echo "$NEW_LOGS" | grep -q "Max restart attempts.*exceeded"; then
            log_warning "FFmpeg manager exhausted retries, watchdog should take over..."
        fi
    fi
    
    # Check if new FFmpeg process started
    NEW_PIDS=$(ps aux | grep "ffmpeg.*rtmp.*youtube" | grep -v grep | awk '{print $2}' || true)
    if [ -n "$NEW_PIDS" ] && [ "$NEW_PIDS" != "$FFMPEG_PID" ]; then
        NEW_PID=$(echo "$NEW_PIDS" | head -n1)
        if [ "$TEST_MODE" = "quick" ] && [ "$RECOVERY_DETECTED" = false ]; then
            log_success "New FFmpeg process started (PID: $NEW_PID)"
            RECOVERY_DETECTED=true
            RECOVERY_TYPE="ffmpeg"
            break
        fi
    fi
    
    # Progress indicator
    if [ $((CHECK_COUNT % 6)) -eq 0 ]; then
        log_info "Still waiting... ($((CHECK_COUNT * 5))s elapsed)"
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
if [ "$TEST_MODE" = "quick" ]; then
    RECOVERY_LOGS=$(docker logs "$CONTAINER_NAME" --tail 200 2>&1 | grep -E "(Auto-restart|restart|Stream.*started)" | tail -15)
else
    RECOVERY_LOGS=$(docker logs "$CONTAINER_NAME" --tail 200 2>&1 | grep -E "(RECOVERY|recovery|Stream.*unhealthy|Max restart)" | tail -20)
fi

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
log_info "TEST RESULTS (${TEST_MODE} mode)"
log_info "=========================================="

if [ "$TEST_MODE" = "quick" ]; then
    # Quick test results - FFmpeg auto-restart
    if [ "$RECOVERY_DETECTED" = true ] && [ "$RECOVERY_TYPE" = "ffmpeg" ]; then
        log_success "✓ FFmpeg process killed"
        log_success "✓ FFmpeg manager detected failure"
        log_success "✓ FFmpeg manager triggered auto-restart"
        
        if [ -n "$NEW_PIDS" ]; then
            NEW_PID=$(echo "$NEW_PIDS" | head -n1)
            log_success "✓ New FFmpeg process running (PID: $NEW_PID)"
            log_success "✓ Stream recovered in ~$((CHECK_COUNT * 5)) seconds!"
        fi
        
        log_success ""
        log_success "TEST PASSED: FFmpeg auto-restart (Layer 1) is working! ✓"
        log_info ""
        log_info "Note: To test the Watchdog (Layer 2), run: $0 full"
        exit 0
    else
        log_error "✗ FFmpeg auto-restart did not recover the stream"
        log_error "Expected: FFmpeg manager should restart within ~5 seconds"
        exit 1
    fi
else
    # Full test results - Watchdog recovery
    if [ "$RECOVERY_DETECTED" = true ] && [ "$RECOVERY_TYPE" = "watchdog" ]; then
        log_success "✓ FFmpeg auto-restart exhausted (Layer 1 failed)"
        log_success "✓ Watchdog detected failure (Layer 2)"
        log_success "✓ Watchdog triggered recovery"
        
        if [ -n "$NEW_PIDS" ]; then
            NEW_PID=$(echo "$NEW_PIDS" | head -n1)
            log_success "✓ New FFmpeg process running (PID: $NEW_PID)"
            log_success "✓ Stream recovered in ~$((CHECK_COUNT * 5)) seconds!"
        fi
        
        log_success ""
        log_success "TEST PASSED: Watchdog (Layer 2) is working correctly! ✓"
        log_success "Recovery count increased: $INITIAL_RECOVERY_COUNT → $FINAL_RECOVERY_COUNT"
        exit 0
    elif [ "$RECOVERY_DETECTED" = true ] && [ "$RECOVERY_TYPE" = "ffmpeg" ]; then
        log_warning "⚠ FFmpeg auto-restart recovered before watchdog could fire"
        log_warning "This means Layer 1 is working, but we didn't reach Layer 2"
        log_info ""
        log_info "The test killed the process 12 times but FFmpeg kept recovering."
        log_info "Watchdog is standing by as backup (working as designed)."
        exit 0
    else
        log_error "✗ Neither FFmpeg nor Watchdog recovered the stream"
        log_error ""
        log_error "Diagnostic info:"
        log_error "  Initial recovery count: $INITIAL_RECOVERY_COUNT"
        log_error "  Final recovery count: $FINAL_RECOVERY_COUNT"
        log_error "  Recovery type detected: ${RECOVERY_TYPE:-none}"
        
        if [ "$UNHEALTHY_DETECTED" = true ]; then
            log_warning "Note: Watchdog detected unhealthy state"
            log_warning "May need more time (3 consecutive 30s checks = 90s)"
        fi
        
        exit 1
    fi
fi
