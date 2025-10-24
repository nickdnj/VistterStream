# VistterStream Local Watchdog

## Overview

The Local Watchdog monitors your FFmpeg encoder process health and automatically recovers from failures. This **does not** require YouTube API credentials - it works entirely locally by monitoring your encoder.

## What It Does

✅ **Monitors FFmpeg Process Health**
- Checks if the encoder process is running
- Monitors CPU and memory usage
- Detects zombie/hung processes

✅ **Automatic Recovery**
- Detects failures after 3 consecutive unhealthy checks
- Automatically restarts the stream
- Includes cooldown period to prevent restart loops

✅ **Comprehensive Logging**
- Logs all health checks
- Records recovery attempts
- Tracks process statistics

❌ **What It Doesn't Do (Yet)**
- Check YouTube's side (if YouTube is actually receiving the stream)
- Verify actual video frames are being transmitted
- Manage YouTube broadcast lifecycle

## How to Enable

### 1. In VistterStream UI

1. Go to **Settings** → **Destinations**
2. Create or edit a YouTube destination
3. Scroll to the **"YouTube Watchdog (Optional)"** section
4. Check **"Enable Watchdog Monitoring"**
5. Set your **Check Interval** (default: 30 seconds)
6. Click **Create** or **Update**

### 2. Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| **Enable Watchdog** | Turn watchdog monitoring on/off | `false` |
| **Check Interval** | Seconds between health checks | `30` |

**Note:** YouTube API Key, Stream ID, Broadcast ID, and Watch URL fields are **not required** for the local watchdog and can be left empty.

## How It Works

### Health Check Cycle

```
Every 30 seconds (configurable):
  ├─ Check if FFmpeg process is running
  ├─ Verify process is not zombie/hung
  ├─ Monitor CPU and memory usage
  └─ Log health status

If 3 consecutive checks fail:
  ├─ Stop the existing stream (if running)
  ├─ Wait 2 seconds for cleanup
  ├─ Restart the stream automatically
  └─ Enter 120-second cooldown period
```

### Recovery Strategy

1. **First Check Fails**: Log warning, continue monitoring
2. **Second Check Fails**: Log warning, continue monitoring
3. **Third Check Fails**: Trigger automatic recovery
4. **Recovery**: Stop + restart stream, reset counter
5. **Cooldown**: Wait 120 seconds before allowing another recovery

## Viewing Watchdog Status

### Via API

```bash
# Check all watchdog status
curl http://localhost:8000/api/watchdog/status

# Check specific destination watchdog
curl http://localhost:8000/api/watchdog/1/status
```

### Via Logs

```bash
# On Raspberry Pi
docker logs -f vistterstream-backend | grep watchdog

# Look for entries like:
# [watchdog.dest1] INFO: Stream 5 healthy - PID: 12345, CPU: 5.2%, Memory: 234.5MB
# [watchdog.dest1] WARNING: Stream unhealthy (2/3 checks)
# [watchdog.dest1] WARNING: === RECOVERY ATTEMPT #1 for Stream 5 ===
```

## Testing the Watchdog

1. **Enable the watchdog** for your destination
2. **Start a stream** to YouTube
3. **Verify it's monitoring**:
   ```bash
   curl http://localhost:8000/api/watchdog/1/status
   ```
   You should see `"running": true` and health statistics

4. **Simulate a failure** (optional):
   ```bash
   # Find the FFmpeg process
   ps aux | grep ffmpeg
   
   # Kill it manually (watchdog should restart it)
   kill -9 <pid>
   
   # Watch the logs
   docker logs -f vistterstream-backend | grep watchdog
   ```

## Troubleshooting

### Watchdog Not Starting

**Check if destination has watchdog enabled:**
```bash
curl http://localhost:8000/api/destinations/1
```
Look for `"enable_watchdog": true`

**Check backend logs:**
```bash
docker logs vistterstream-backend | grep -i "watchdog"
```

### False Alarms (Unnecessary Restarts)

If the watchdog is restarting your stream when it's actually healthy:
- **Increase the check interval** (e.g., 60 seconds)
- **Check system resources** - low CPU/memory can cause false failures
- **Review logs** to see what's triggering the unhealthy state

### Stream Keeps Failing

If the watchdog keeps restarting but the stream won't stay up:
- **Check your camera connections** (RTSP URLs, credentials)
- **Verify network stability** to cameras and YouTube
- **Check YouTube stream health** manually in YouTube Studio
- **Review FFmpeg logs** for actual errors

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/watchdog/status` | GET | Get status of all watchdogs |
| `/api/watchdog/{dest_id}/status` | GET | Get status of specific watchdog |
| `/api/watchdog/{dest_id}/start` | POST | Manually start watchdog |
| `/api/watchdog/{dest_id}/stop` | POST | Manually stop watchdog |
| `/api/destinations/{dest_id}/validate-watchdog` | POST | Validate watchdog config |

## Future Enhancements

Potential additions (not yet implemented):
- 🔄 **YouTube API Integration** (requires OAuth2 setup)
  - Check YouTube's side of stream health
  - Verify actual video frames being received
  - Manage broadcast lifecycle

- 📊 **Advanced Monitoring**
  - Bitrate monitoring
  - Frame drop detection
  - Network quality checks

- 🔔 **Notifications**
  - Email alerts on failures
  - Webhook notifications
  - Discord/Slack integration

## FAQ

**Q: Do I need YouTube API credentials?**  
A: No, not for the local watchdog. It works entirely locally.

**Q: Will this prevent my stream from going down?**  
A: It helps with **encoder-side failures** (FFmpeg crashes, process hangs). It cannot prevent issues on YouTube's side, network outages, or camera failures.

**Q: How much overhead does this add?**  
A: Minimal. One health check every 30 seconds uses negligible CPU/memory.

**Q: Can I use this for non-YouTube destinations?**  
A: Yes! The local watchdog works for any streaming destination.

**Q: What happens if the watchdog itself crashes?**  
A: The watchdog runs inside the backend container, so if the backend restarts, the watchdog restarts too. Docker's restart policy ensures the backend stays running.

---

**Need Help?** Check the logs first:
```bash
docker logs -f vistterstream-backend | grep -E "watchdog|ffmpeg|stream"
```

