# YouTube Stream Watchdog - Complete Setup Guide

## Overview

The YouTube Stream Watchdog is an autonomous monitoring and recovery system designed to ensure your YouTube Live stream never gets stuck in a "zombie state" where YouTube shows green status but no video frames are being transmitted.

### Key Features

✅ **Automatic Health Monitoring** - Checks stream health every 30 seconds via YouTube API  
✅ **Intelligent Recovery** - Progressively escalates from encoder restart to full broadcast reset  
✅ **Zero Human Intervention** - Fully autonomous operation  
✅ **Comprehensive Logging** - Detailed logs for debugging and audit trails  
✅ **Systemd Integration** - Runs as a service with automatic restart on failure  
✅ **Optional Frame Probing** - Verifies actual video frames are flowing (requires yt-dlp)  
✅ **Daily Reset** - Optional scheduled broadcast rotation to prevent long-running issues  

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YouTube Live Stream                       │
│                  (Broadcast + Stream Keys)                   │
└────────────────────▲──────────────────┬────────────────────┘
                     │                  │
                     │ Video Feed       │ Health Status
                     │                  │ (API v3)
                     │                  │
┌────────────────────┴──────┐    ┌─────▼──────────────────────┐
│  vistterstream-encoder    │    │  vistterstream-watchdog    │
│  (FFmpeg/OBS)             │    │  (Python Service)          │
│  - Encodes video          │    │  - Monitors health         │
│  - Sends to YouTube       │    │  - Triggers recovery       │
└───────────────────────────┘    │  - Logs everything         │
      ▲                          └────────┬───────────────────┘
      │                                   │
      │ Restart on failure                │ systemctl restart
      └───────────────────────────────────┘
```

## Prerequisites

### 1. YouTube Live Setup

You need a YouTube channel with live streaming enabled and the following:

- **YouTube Data API v3 Key** - For monitoring stream health
- **Stream ID** - The ID of your live stream resource
- **Broadcast ID** - The ID of your live broadcast
- **Watch URL** - The public watch URL (e.g., https://youtube.com/watch?v=xxx)
- **Stream Key** - RTMP stream key for your encoder

### 2. System Requirements

- Linux system (tested on Raspberry Pi 4)
- Python 3.7+
- systemd
- FFmpeg or OBS Studio (for encoding)
- Optional: yt-dlp (for frame probing)

### 3. Python Dependencies

Install required packages:

```bash
pip install aiohttp
```

Optional (for frame probing):
```bash
sudo apt-get install yt-dlp
# or
pip install yt-dlp
```

## Getting YouTube API Credentials

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Note your project name

### Step 2: Enable YouTube Data API v3

1. In Cloud Console, go to "APIs & Services" > "Library"
2. Search for "YouTube Data API v3"
3. Click "Enable"

### Step 3: Create API Key

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "API Key"
3. Copy the API key (keep it secret!)
4. Optional: Click "Restrict Key" to limit it to YouTube Data API v3 only

### Step 4: Get Stream and Broadcast IDs

You have two options:

#### Option A: Using YouTube Studio (Easy)

1. Go to [YouTube Studio](https://studio.youtube.com)
2. Click "Create" > "Go Live"
3. Set up your stream (title, privacy, etc.)
4. In the URL, you'll see: `youtube.com/live_dashboard?v=BROADCAST_ID`
5. The stream ID can be found in the "Stream Settings" section

#### Option B: Using API Explorer (Complete)

1. Go to [YouTube Live Streams API Explorer](https://developers.google.com/youtube/v3/live/docs/liveStreams/list)
2. Set `part` = `id,snippet,status`
3. Set `mine` = `true`
4. Click "Execute" and authorize
5. Copy the `id` field from response (this is your STREAM_ID)

Repeat for broadcasts:
1. Go to [Live Broadcasts API Explorer](https://developers.google.com/youtube/v3/live/docs/liveBroadcasts/list)
2. Follow same process to get BROADCAST_ID

### Step 5: Get Watch URL

Once your broadcast is live or in testing mode:
1. Go to YouTube Studio > "Content" > "Live"
2. Find your stream and copy the watch URL
3. Format: `https://www.youtube.com/watch?v=VIDEO_ID`

## Installation

### Quick Install

```bash
# Navigate to VistterStream directory
cd /opt/vistterstream

# Create .env file with your credentials
cp env.sample .env
nano .env  # Edit with your YouTube credentials

# Install Python dependencies
pip3 install -r backend/requirements.txt
pip3 install aiohttp

# Install systemd services
sudo cp systemd/vistterstream-watchdog.service /etc/systemd/system/
sudo cp systemd/vistterstream-encoder.service.example /etc/systemd/system/vistterstream-encoder.service

# Customize encoder service for your setup
sudo nano /etc/systemd/system/vistterstream-encoder.service

# Create log directory
sudo mkdir -p /var/log
sudo touch /var/log/vistterstream-watchdog.log
sudo touch /var/log/vistterstream-encoder.log
sudo chown $USER:$USER /var/log/vistterstream-*.log

# Reload systemd
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable vistterstream-encoder
sudo systemctl enable vistterstream-watchdog

# Start encoder first
sudo systemctl start vistterstream-encoder
sleep 10

# Then start watchdog
sudo systemctl start vistterstream-watchdog
```

### Manual Install

If you prefer to understand each step:

#### 1. Clone/Update Repository
```bash
cd /opt
sudo git clone https://github.com/yourusername/VistterStream.git
# or update existing:
cd /opt/vistterstream
sudo git pull
```

#### 2. Configure Environment
```bash
cd /opt/vistterstream
cp env.sample .env
```

Edit `.env` with your credentials:
```bash
# Required
YOUTUBE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
YOUTUBE_STREAM_ID=your-stream-id-here
YOUTUBE_BROADCAST_ID=your-broadcast-id-here
YOUTUBE_WATCH_URL=https://www.youtube.com/watch?v=your-video-id
YOUTUBE_STREAM_KEY=xxxx-xxxx-xxxx-xxxx-xxxx

# Optional
ENCODER_SERVICE_NAME=vistterstream-encoder
WATCHDOG_CHECK_INTERVAL=30
WATCHDOG_ENABLE_FRAME_PROBE=false
WATCHDOG_ENABLE_DAILY_RESET=false
WATCHDOG_DAILY_RESET_HOUR=3
```

Secure the file:
```bash
chmod 600 .env
```

#### 3. Install Dependencies
```bash
pip3 install aiohttp

# Optional for frame probing
sudo apt-get install -y yt-dlp
```

#### 4. Test the Watchdog Manually

Before setting up as a service, test it works:

```bash
cd /opt/vistterstream
export $(cat .env | xargs)
python3 backend/services/youtube_stream_watchdog.py
```

You should see output like:
```
============================================================
YouTube Stream Watchdog Starting
============================================================
Stream ID: your-stream-id
Broadcast ID: your-broadcast-id
Encoder Service: vistterstream-encoder
Check Interval: 30s
Frame Probe: Disabled
Daily Reset: Disabled
============================================================
2024-10-24 12:00:00 [watchdog] INFO: Health check: status=good, stream_status=active, consecutive_unhealthy=0
```

Press Ctrl+C to stop. If it works, proceed to install as service.

#### 5. Configure Your Encoder

Create your encoder service. Here's an FFmpeg example for Raspberry Pi:

```bash
sudo nano /etc/systemd/system/vistterstream-encoder.service
```

Basic FFmpeg configuration:
```ini
[Unit]
Description=VistterStream YouTube Encoder
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/vistterstream
EnvironmentFile=/opt/vistterstream/.env

# Adjust this command for your input source
ExecStart=/usr/bin/ffmpeg \
    -f v4l2 -i /dev/video0 \
    -c:v h264_v4l2m2m \
    -b:v 2500k \
    -maxrate 2500k \
    -bufsize 5000k \
    -pix_fmt yuv420p \
    -g 60 \
    -c:a aac \
    -b:a 128k \
    -ar 44100 \
    -f flv \
    rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY}

Restart=always
RestartSec=5
StandardOutput=append:/var/log/vistterstream-encoder.log
StandardError=append:/var/log/vistterstream-encoder.log

[Install]
WantedBy=multi-user.target
```

For RTMP input source:
```ini
ExecStart=/usr/bin/ffmpeg \
    -i rtmp://localhost/live/stream \
    -c:v libx264 \
    -preset veryfast \
    -b:v 3000k \
    -maxrate 3500k \
    -bufsize 6000k \
    -pix_fmt yuv420p \
    -g 60 \
    -c:a aac \
    -b:a 128k \
    -f flv \
    rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY}
```

#### 6. Install Services

```bash
# Copy watchdog service
sudo cp systemd/vistterstream-watchdog.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable both services
sudo systemctl enable vistterstream-encoder
sudo systemctl enable vistterstream-watchdog
```

#### 7. Start Services

```bash
# Start encoder first
sudo systemctl start vistterstream-encoder

# Wait for encoder to connect
sleep 10

# Start watchdog
sudo systemctl start vistterstream-watchdog

# Check status
sudo systemctl status vistterstream-encoder
sudo systemctl status vistterstream-watchdog
```

## Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `YOUTUBE_API_KEY` | Yes | - | YouTube Data API v3 key |
| `YOUTUBE_STREAM_ID` | Yes | - | YouTube stream resource ID |
| `YOUTUBE_BROADCAST_ID` | Yes | - | YouTube broadcast ID |
| `YOUTUBE_WATCH_URL` | Yes | - | Public watch URL |
| `YOUTUBE_STREAM_KEY` | Yes | - | RTMP stream key for encoder |
| `ENCODER_SERVICE_NAME` | No | `vistterstream-encoder` | Name of encoder systemd service |
| `WATCHDOG_CHECK_INTERVAL` | No | `30` | Seconds between health checks |
| `WATCHDOG_ENABLE_FRAME_PROBE` | No | `false` | Enable video frame verification |
| `WATCHDOG_ENABLE_DAILY_RESET` | No | `false` | Enable daily broadcast reset |
| `WATCHDOG_DAILY_RESET_HOUR` | No | `3` | UTC hour for daily reset (0-23) |
| `WATCHDOG_LOG_FILE` | No | `/var/log/vistterstream-watchdog.log` | Log file path |

### Recovery Strategy

The watchdog uses a progressive recovery strategy:

1. **First failure** (after 3 consecutive unhealthy checks):
   - Restart encoder service
   - Wait 15 seconds for reconnection

2. **Second failure**:
   - Restart encoder service again
   - Wait 15 seconds

3. **Third+ failures**:
   - Reset broadcast via YouTube API
   - Cycle: Complete → Testing → Live
   - Wait 20 seconds for encoder to reconnect

### Health Check Criteria

Stream is considered **unhealthy** if:
- Health status is `bad` or `noData` (when stream should be active)
- Frame probe fails (if enabled)
- Three consecutive unhealthy checks

Stream is considered **healthy** if:
- Health status is `good` or `ok`
- Frame probe succeeds (if enabled)

## Usage

### Monitoring

#### View Watchdog Logs
```bash
# Real-time log following
tail -f /var/log/vistterstream-watchdog.log

# View systemd journal
sudo journalctl -u vistterstream-watchdog -f

# View last 100 lines
sudo journalctl -u vistterstream-watchdog -n 100
```

#### View Encoder Logs
```bash
tail -f /var/log/vistterstream-encoder.log
sudo journalctl -u vistterstream-encoder -f
```

#### Check Service Status
```bash
sudo systemctl status vistterstream-watchdog
sudo systemctl status vistterstream-encoder
```

### Manual Recovery Testing

To test recovery manually:

```bash
# Stop encoder to simulate failure
sudo systemctl stop vistterstream-encoder

# Watch logs - watchdog should detect failure and restart encoder
tail -f /var/log/vistterstream-watchdog.log
```

You should see output like:
```
2024-10-24 12:01:30 [watchdog] WARNING: Stream unhealthy (1/3 checks)
2024-10-24 12:02:00 [watchdog] WARNING: Stream unhealthy (2/3 checks)
2024-10-24 12:02:30 [watchdog] WARNING: Stream unhealthy for 3 consecutive checks - triggering recovery
2024-10-24 12:02:30 [watchdog] WARNING: === RECOVERY ATTEMPT #1 ===
2024-10-24 12:02:30 [watchdog] INFO: Restarting encoder service: vistterstream-encoder
2024-10-24 12:02:31 [watchdog] INFO: Encoder service restart command succeeded
```

### Maintenance

#### Restart Services
```bash
sudo systemctl restart vistterstream-encoder
sudo systemctl restart vistterstream-watchdog
```

#### Stop Services
```bash
sudo systemctl stop vistterstream-watchdog
sudo systemctl stop vistterstream-encoder
```

#### Disable Auto-Start
```bash
sudo systemctl disable vistterstream-watchdog
sudo systemctl disable vistterstream-encoder
```

#### Update Configuration
```bash
# Edit environment variables
nano /opt/vistterstream/.env

# Restart services to apply changes
sudo systemctl restart vistterstream-encoder
sudo systemctl restart vistterstream-watchdog
```

## Troubleshooting

### Watchdog Reports "Configuration error"

**Problem:** Missing environment variables

**Solution:**
```bash
# Check your .env file
cat /opt/vistterstream/.env | grep YOUTUBE

# Ensure all required variables are set
nano /opt/vistterstream/.env
```

### "YouTube API error: 403"

**Problem:** API key invalid or quota exceeded

**Solutions:**
- Verify API key in Google Cloud Console
- Check API is enabled: YouTube Data API v3
- Check quota usage in Cloud Console
- Generate new API key if needed

### "Stream not found"

**Problem:** Stream ID or Broadcast ID incorrect

**Solutions:**
- Verify IDs using [API Explorer](https://developers.google.com/youtube/v3/live/docs/liveStreams/list)
- Ensure broadcast is in "testing" or "live" state
- Create new stream/broadcast if necessary

### Watchdog Can't Restart Encoder

**Problem:** Permission denied when calling systemctl restart

**Solution:** Grant permission to restart service without password:
```bash
sudo visudo
# Add this line:
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart vistterstream-encoder
```

### Encoder Immediately Fails

**Problem:** FFmpeg command errors or bad configuration

**Solutions:**
```bash
# Test FFmpeg command manually
ffmpeg -i /dev/video0 -t 10 test.mp4

# Check encoder logs
sudo journalctl -u vistterstream-encoder -n 50

# Verify stream key is correct
echo $YOUTUBE_STREAM_KEY
```

### High CPU Usage

**Problem:** Frame probing or encoding consuming too much CPU

**Solutions:**
- Disable frame probing: `WATCHDOG_ENABLE_FRAME_PROBE=false`
- Increase check interval: `WATCHDOG_CHECK_INTERVAL=60`
- Use hardware encoding in FFmpeg (h264_v4l2m2m)
- Reduce video bitrate/resolution

### Stream Still Getting Stuck

**Problem:** Recovery not working as expected

**Debugging:**
1. Check watchdog is running: `sudo systemctl status vistterstream-watchdog`
2. Review logs: `tail -100 /var/log/vistterstream-watchdog.log`
3. Verify YouTube API responses are correct
4. Try manual broadcast reset via YouTube Studio
5. Enable frame probing to catch issues earlier
6. Reduce unhealthy threshold in code (edit `StreamHealthState`)

## Advanced Configuration

### Enable Frame Probing

Frame probing verifies actual video is flowing, not just API health:

```bash
# Install yt-dlp
sudo apt-get install -y yt-dlp
# or
pip3 install yt-dlp

# Enable in .env
echo "WATCHDOG_ENABLE_FRAME_PROBE=true" >> .env

# Restart watchdog
sudo systemctl restart vistterstream-watchdog
```

**Note:** This adds ~10-15 seconds to each check cycle.

### Enable Daily Reset

Prevents long-running broadcast drift:

```bash
# Add to .env
echo "WATCHDOG_ENABLE_DAILY_RESET=true" >> .env
echo "WATCHDOG_DAILY_RESET_HOUR=3" >> .env  # 3 AM UTC

# Restart watchdog
sudo systemctl restart vistterstream-watchdog
```

### Multiple Stream Monitoring

To monitor multiple streams, create separate service instances:

```bash
# Create separate config files
cp .env .env.stream1
cp .env .env.stream2

# Edit each with different stream IDs
nano .env.stream1
nano .env.stream2

# Create separate service files
sudo cp /etc/systemd/system/vistterstream-watchdog.service \
        /etc/systemd/system/vistterstream-watchdog-stream1.service

# Edit to use different env file
sudo nano /etc/systemd/system/vistterstream-watchdog-stream1.service
# Change: EnvironmentFile=/opt/vistterstream/.env.stream1

# Enable and start
sudo systemctl enable vistterstream-watchdog-stream1
sudo systemctl start vistterstream-watchdog-stream1
```

### Email Alerts

Add email notifications on recovery:

```bash
# Install mail utils
sudo apt-get install -y mailutils

# Create alert script
sudo nano /usr/local/bin/watchdog-alert.sh
```

```bash
#!/bin/bash
echo "VistterStream watchdog performed recovery at $(date)" | \
    mail -s "Stream Recovery Alert" your-email@example.com
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/watchdog-alert.sh

# Modify watchdog to call script after recovery
# (Add to youtube_stream_watchdog.py in recover_stream method)
```

### Monitoring Dashboard

Integrate with monitoring tools:

```bash
# Export metrics to Prometheus
# Install prometheus client
pip3 install prometheus-client

# Modify watchdog to expose /metrics endpoint
# Use grafana to visualize stream health over time
```

## Performance and Costs

### Resource Usage
- **Watchdog**: ~20-50 MB RAM, negligible CPU
- **Encoder**: Varies by settings (500MB - 2GB RAM, 30-100% CPU)

### YouTube API Quota
- Health check: 1 unit per call
- Broadcast transition: 50 units per call
- Daily quota: 10,000 units (default)

At 30-second intervals:
- Daily checks: ~2,880 checks = 2,880 units
- Leaves plenty room for recoveries

### Network Bandwidth
- Health checks: ~1 KB each
- Daily bandwidth: ~2.8 MB
- Negligible compared to video upload

## Security Best Practices

1. **Protect API Key**
   ```bash
   chmod 600 /opt/vistterstream/.env
   ```

2. **Restrict API Key**
   - In Google Cloud Console, restrict key to YouTube Data API v3 only
   - Optional: Add IP restrictions

3. **Use Separate User**
   ```bash
   sudo useradd -r -s /bin/false vistterstream
   # Update service User= directive
   ```

4. **Firewall Rules**
   ```bash
   sudo ufw allow out 443/tcp  # HTTPS for API
   sudo ufw allow out 1935/tcp # RTMP for streaming
   ```

5. **Regular Updates**
   ```bash
   # Update system
   sudo apt-get update && sudo apt-get upgrade -y
   
   # Update Python packages
   pip3 install --upgrade aiohttp
   ```

## FAQ

**Q: How quickly does the watchdog detect failures?**  
A: With default settings, it takes 90 seconds (3 checks × 30s interval) to detect and trigger recovery.

**Q: Will this work with other streaming platforms?**  
A: Currently YouTube-specific, but architecture is adaptable. PRs welcome!

**Q: Can I use this on non-Pi hardware?**  
A: Yes! Works on any Linux system with Python 3.7+ and systemd.

**Q: Does this cost money?**  
A: YouTube API is free within quota limits. Normal usage stays well below limits.

**Q: What if my internet connection drops?**  
A: Watchdog will detect the issue and attempt recovery. Encoder should auto-reconnect once internet returns.

**Q: Can I run this in Docker?**  
A: Possible but requires Docker-in-Docker or host systemd access. Native installation recommended.

## Support

### Logs to Include When Asking for Help

```bash
# System info
uname -a
cat /etc/os-release

# Service status
sudo systemctl status vistterstream-watchdog
sudo systemctl status vistterstream-encoder

# Recent logs
sudo journalctl -u vistterstream-watchdog -n 100 --no-pager
sudo journalctl -u vistterstream-encoder -n 100 --no-pager
tail -100 /var/log/vistterstream-watchdog.log
```

### Getting Help

- Check the logs first
- Search existing issues on GitHub
- Create new issue with logs and config (redact API keys!)
- Join community Discord/forum

## Contributing

Improvements welcome! Areas for contribution:
- Support for additional streaming platforms
- Web dashboard for monitoring
- Metrics/Prometheus integration
- Email/SMS alerting
- Machine learning for predictive failures

## License

[Your license here]

## Changelog

### Version 1.0.0 (2024-10-24)
- Initial release
- YouTube API health monitoring
- Automatic encoder restart
- Broadcast lifecycle management
- Systemd service integration
- Comprehensive logging

---

**Note:** This watchdog is designed for 24/7 unattended operation. Thoroughly test in your environment before relying on it for production streams.

