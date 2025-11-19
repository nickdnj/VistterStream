# Automatic YouTube Broadcast Reset Fix

## Problem

When a stream is stopped from VistterStream, YouTube marks the broadcast as "complete" (finished). When you try to restart the stream, YouTube won't accept it because the broadcast is in "complete" state. You had to manually go to YouTube Studio and clear the "Stream Finished" dialog before the stream would work again.

## Solution

Added **automatic broadcast reset** when starting a timeline. Now, when you start a timeline that streams to a YouTube destination:

1. **Checks broadcast status** - Before starting the stream, VistterStream checks if the YouTube broadcast is in "complete" state
2. **Auto-resets if needed** - If the broadcast is "complete", it automatically resets it (complete → testing → live)
3. **Transitions to live** - If the broadcast is in "testing", it transitions to "live"
4. **No action if already live** - If already "live", no action needed

## What Changed

**File:** `backend/routers/timeline_execution.py`

Added automatic broadcast status check and reset in the `start_timeline` endpoint, right before starting the timeline execution.

### How It Works

```python
# For each YouTube destination with OAuth connected:
1. Check if OAuth is connected and broadcast ID is configured
2. Query YouTube API for current broadcast status
3. If status is "complete":
   - Reset broadcast (complete → testing → live)
4. If status is "testing":
   - Transition to "live"
5. If status is "live":
   - No action needed
6. Start the stream normally
```

## Requirements

For automatic reset to work, your YouTube destination must have:

- ✅ **OAuth connected** (green "Connected" status)
- ✅ **YouTube Broadcast ID** configured
- ✅ **YouTube Stream ID** configured (optional but recommended)

## Testing

### Test Scenario 1: Stream Restart After Stop

1. **Start a timeline** streaming to YouTube
2. **Stop the timeline** from VistterStream
3. **Wait a moment** (YouTube marks broadcast as "complete")
4. **Start the timeline again**
5. **Expected:** Stream starts automatically without needing to clear "Stream Finished" in YouTube Studio

### Test Scenario 2: Check Logs

Watch backend logs when starting a timeline:

```bash
docker logs -f vistterstream-backend | grep -i "broadcast\|youtube"
```

You should see:
```
Checking YouTube broadcast status for destination X (Vistter 2)
Broadcast abc123 status: complete
Broadcast abc123 is in 'complete' state. Auto-resetting to allow stream restart...
Resetting broadcast abc123 (cycling through states)
Broadcast reset successful. New status: live
```

### Test Scenario 3: Manual Verification

1. Start a timeline
2. Check YouTube Studio - broadcast should be in "live" state
3. Stop the timeline
4. Check YouTube Studio - broadcast should show "Stream Finished"
5. Start timeline again
6. Check YouTube Studio - "Stream Finished" should disappear and stream should be live

## Error Handling

The code is designed to **not fail** if broadcast reset fails:

- If OAuth is not connected → Stream starts anyway (no reset attempted)
- If broadcast ID is missing → Stream starts anyway (no reset attempted)
- If YouTube API fails → Logs warning, stream starts anyway
- If reset fails → Logs error, stream attempts to start anyway

This ensures that even if broadcast reset fails, the stream will still attempt to start. You'll see warnings in logs if something goes wrong.

## Benefits

✅ **No manual intervention** - Streams restart automatically  
✅ **Seamless recovery** - Works with watchdog recovery too  
✅ **24/7 operation** - Perfect for unattended streaming  
✅ **Error resilient** - Won't break if reset fails  

## What This Enables

Now your stream recovery workflow is complete:

1. **Stream stops** (network issue, camera offline, etc.)
2. **Watchdog detects failure** (after 3 consecutive unhealthy checks)
3. **Watchdog restarts FFmpeg** (local recovery)
4. **Broadcast is reset automatically** (when timeline restarts)
5. **Stream resumes** - No manual steps needed!

## Related Features

This works together with:

- **OAuth Connection** - Required for YouTube API access
- **Watchdog Monitoring** - Detects failures and restarts streams
- **Broadcast Management** - Full lifecycle control via API

## Next Steps

1. **Deploy the fix** (restart backend)
2. **Test stream restart** (stop → start)
3. **Verify logs** show automatic reset
4. **Test with watchdog** (simulate failure, verify auto-recovery)

---

**The stream will now automatically recover from interruptions without requiring manual YouTube Studio intervention!** 🎉


