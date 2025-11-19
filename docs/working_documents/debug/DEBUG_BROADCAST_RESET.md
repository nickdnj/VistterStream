# Debugging Broadcast Reset Issue

## Quick Diagnostic Steps

### Step 1: Check Backend Logs When Starting Timeline

When you start a timeline, watch the logs in real-time:

```bash
# On your Raspberry Pi
docker logs -f vistterstream-backend | grep -E "(broadcast|YouTube|destination|timeline)"
```

**What to look for:**
- `Checking YouTube broadcast status for destination X`
- `Broadcast abc123 status: complete`
- `Auto-resetting to allow stream restart...`
- `Broadcast reset successful`

**If you DON'T see these messages:**
- The code isn't executing
- Check requirements below

### Step 2: Verify Requirements

The automatic reset only works if ALL of these are true:

1. **OAuth is connected:**
   ```bash
   docker exec vistterstream-backend python3 -c "
   from models.database import SessionLocal
   from models.destination import StreamingDestination
   db = SessionLocal()
   dest = db.query(StreamingDestination).first()
   print(f'OAuth Connected: {dest.youtube_oauth_connected}')
   print(f'Has Broadcast ID: {bool(dest.youtube_broadcast_id)}')
   print(f'Platform: {dest.platform}')
   db.close()
   "
   ```
   
   Should show:
   ```
   OAuth Connected: True
   Has Broadcast ID: True
   Platform: youtube
   ```

2. **Broadcast ID is configured:**
   - Go to VistterStream UI → Settings → Destinations
   - Edit your YouTube destination
   - Check "YouTube Broadcast ID" field is filled in
   - Should look like: `ab12cd34ef56gh78`

3. **OAuth is connected:**
   - In the destination card, status should show "Connected" (green)
   - Not "Not connected" (red)

### Step 3: Check for Errors

Look for error messages in logs:

```bash
docker logs vistterstream-backend --tail 100 | grep -iE "(error|exception|failed|youtube|broadcast)"
```

Common errors:
- `Failed to check/reset YouTube broadcast` - API error
- `Destination is not connected to YouTube via OAuth` - OAuth not connected
- `Destination does not have a YouTube broadcast ID configured` - Missing broadcast ID

### Step 4: Test Manually

Try calling the reset endpoint directly:

```bash
# Get your destination ID first (probably 1 or 2)
curl -X POST http://localhost:8000/api/destinations/1/youtube/reset
```

If this works, the reset functionality is working, but the automatic check might not be running.

### Step 5: Verify Code is Loaded

Check if the new code is actually in the container:

```bash
docker exec vistterstream-backend grep -A 5 "Auto-reset YouTube broadcasts" /app/backend/routers/timeline_execution.py
```

Should show the code we added. If it doesn't, the container wasn't rebuilt properly.

## Common Issues

### Issue 1: Code Not Executing

**Symptom:** No log messages about broadcast checking

**Possible causes:**
- OAuth not connected (`youtube_oauth_connected = False`)
- Broadcast ID not set (`youtube_broadcast_id = None`)
- Platform not "youtube"
- Code not rebuilt in container

**Fix:**
1. Verify OAuth is connected (green status)
2. Verify broadcast ID is set
3. Rebuild container: `docker compose -f docker-compose.rpi.yml build --no-cache backend`

### Issue 2: Silent Failure

**Symptom:** Code executes but reset fails silently

**Check logs for:**
```
Failed to check/reset YouTube broadcast for destination X: [error message]
```

**Common errors:**
- `invalid_grant` - OAuth token expired, need to reconnect
- `broadcastNotFound` - Broadcast ID is wrong
- `forbidden` - OAuth doesn't have permission

**Fix:**
- Reconnect OAuth if token expired
- Verify broadcast ID is correct
- Check OAuth scopes include YouTube API permissions

### Issue 3: Broadcast ID Wrong

**Symptom:** Reset fails with "broadcastNotFound"

**How to get correct Broadcast ID:**
1. Go to YouTube Studio → Live → Stream
2. Look at the URL: `studio.youtube.com/video/[VIDEO_ID]/livestreaming`
3. The Broadcast ID is different - it's in the API response
4. Or use the API to list broadcasts and find the right one

## Manual Test

To verify the reset works manually:

```bash
# Check current status
curl http://localhost:8000/api/destinations/1/youtube/broadcast-status

# Reset broadcast
curl -X POST http://localhost:8000/api/destinations/1/youtube/reset

# Check status again
curl http://localhost:8000/api/destinations/1/youtube/broadcast-status
```

If manual reset works but automatic doesn't, the issue is in the timeline start code.

## Next Steps

Run these commands and share the output:

1. **Check logs when starting timeline:**
   ```bash
   docker logs -f vistterstream-backend
   ```
   (Then start a timeline and watch what happens)

2. **Verify configuration:**
   ```bash
   docker exec vistterstream-backend python3 -c "
   from models.database import SessionLocal
   from models.destination import StreamingDestination
   db = SessionLocal()
   dest = db.query(StreamingDestination).filter(StreamingDestination.platform == 'youtube').first()
   if dest:
       print(f'ID: {dest.id}')
       print(f'Name: {dest.name}')
       print(f'OAuth Connected: {dest.youtube_oauth_connected}')
       print(f'Broadcast ID: {dest.youtube_broadcast_id}')
       print(f'Stream ID: {dest.youtube_stream_id}')
   else:
       print('No YouTube destination found')
   db.close()
   "
   ```

3. **Check if code is in container:**
   ```bash
   docker exec vistterstream-backend grep -c "Auto-reset YouTube broadcasts" /app/backend/routers/timeline_execution.py
   ```
   Should return `1` if code is present.


