# VistterStream Systemd Services

This directory contains systemd service files for running VistterStream components as system services on Linux (especially Raspberry Pi).

## Services

### 1. vistterstream-watchdog.service
The YouTube stream health monitor and auto-recovery service. This service:
- Monitors YouTube Live stream health every 30 seconds
- Detects zombie streams (green status but no video)
- Automatically restarts the encoder or resets the broadcast
- Logs all activity for debugging

### 2. vistterstream-encoder.service.example
Template for the encoder service (FFmpeg or OBS). You need to customize this for your setup.

## Installation

### Step 1: Install the Service Files

```bash
# Copy service files to systemd directory
sudo cp systemd/vistterstream-watchdog.service /etc/systemd/system/
sudo cp systemd/vistterstream-encoder.service.example /etc/systemd/system/vistterstream-encoder.service

# Reload systemd to recognize new services
sudo systemctl daemon-reload
```

### Step 2: Customize the Encoder Service

Edit `/etc/systemd/system/vistterstream-encoder.service` to match your streaming setup:

```bash
sudo nano /etc/systemd/system/vistterstream-encoder.service
```

**Important:** Customize the `ExecStart` command with:
- Your video input source (camera, RTMP feed, etc.)
- Encoding settings appropriate for your hardware
- Your YouTube stream key

### Step 3: Configure Environment Variables

Ensure your `.env` file at `/opt/vistterstream/.env` contains all required variables:

```bash
# YouTube API Configuration
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_STREAM_ID=your_stream_id
YOUTUBE_BROADCAST_ID=your_broadcast_id
YOUTUBE_WATCH_URL=https://www.youtube.com/watch?v=your_video_id
YOUTUBE_STREAM_KEY=your_stream_key

# Encoder Configuration
RTMP_SOURCE_URL=rtmp://localhost/live/stream
ENCODER_SERVICE_NAME=vistterstream-encoder

# Watchdog Configuration
WATCHDOG_CHECK_INTERVAL=30
WATCHDOG_ENABLE_FRAME_PROBE=false
WATCHDOG_ENABLE_DAILY_RESET=false
WATCHDOG_DAILY_RESET_HOUR=3
WATCHDOG_LOG_FILE=/var/log/vistterstream-watchdog.log
```

### Step 4: Create Log Directory

```bash
sudo mkdir -p /var/log
sudo chown pi:pi /var/log/vistterstream-*.log
```

### Step 5: Enable and Start Services

```bash
# Enable services to start on boot
sudo systemctl enable vistterstream-encoder
sudo systemctl enable vistterstream-watchdog

# Start the encoder first
sudo systemctl start vistterstream-encoder

# Wait a few seconds, then start the watchdog
sleep 5
sudo systemctl start vistterstream-watchdog
```

## Managing Services

### Check Service Status
```bash
sudo systemctl status vistterstream-encoder
sudo systemctl status vistterstream-watchdog
```

### View Logs
```bash
# View recent logs
sudo journalctl -u vistterstream-encoder -n 50
sudo journalctl -u vistterstream-watchdog -n 50

# Follow logs in real-time
sudo journalctl -u vistterstream-watchdog -f

# View watchdog log file
tail -f /var/log/vistterstream-watchdog.log
```

### Restart Services
```bash
sudo systemctl restart vistterstream-encoder
sudo systemctl restart vistterstream-watchdog
```

### Stop Services
```bash
sudo systemctl stop vistterstream-watchdog
sudo systemctl stop vistterstream-encoder
```

### Disable Auto-Start
```bash
sudo systemctl disable vistterstream-encoder
sudo systemctl disable vistterstream-watchdog
```

## Troubleshooting

### Watchdog Not Starting
1. Check configuration:
   ```bash
   sudo systemctl status vistterstream-watchdog
   ```
2. Verify environment variables are set correctly
3. Check log file for errors:
   ```bash
   tail -50 /var/log/vistterstream-watchdog.log
   ```

### Encoder Keeps Restarting
1. Check encoder logs:
   ```bash
   sudo journalctl -u vistterstream-encoder -n 100
   ```
2. Verify stream key and YouTube configuration
3. Test FFmpeg command manually before using in service

### Watchdog Can't Restart Encoder
The watchdog needs permission to restart services. Ensure:
1. Watchdog is running as a user with systemctl restart permissions
2. Consider using sudo without password for service restart:
   ```bash
   sudo visudo
   # Add line:
   pi ALL=(ALL) NOPASSWD: /bin/systemctl restart vistterstream-encoder
   ```

### YouTube API Errors
1. Verify API key is valid and has YouTube Data API v3 enabled
2. Check that stream ID and broadcast ID are correct
3. Ensure API quota hasn't been exceeded
4. Review watchdog logs for specific error messages

## Advanced Configuration

### Hardware-Accelerated Encoding

For Raspberry Pi 4 with H.264 hardware encoder:

```ini
ExecStart=/usr/bin/ffmpeg \
    -re \
    -i ${RTMP_SOURCE_URL} \
    -c:v h264_v4l2m2m \
    -b:v 3000k \
    -maxrate 3500k \
    -bufsize 6000k \
    -g 60 \
    -c:a aac \
    -b:a 128k \
    -f flv \
    rtmp://a.rtmp.youtube.com/live2/${YOUTUBE_STREAM_KEY}
```

### Multiple Stream Support

To monitor multiple YouTube streams, create separate service files:
- `vistterstream-watchdog-stream1.service`
- `vistterstream-watchdog-stream2.service`

Each should reference different environment files with unique stream IDs.

### Email Alerts on Recovery

Add email notification by modifying the watchdog service:

```ini
[Service]
OnFailure=email-alert@%n.service
```

Then create an email alert service using `sendmail` or similar.

## Performance Notes

- Watchdog uses minimal resources (< 50MB RAM, negligible CPU)
- Check interval of 30s provides good balance between responsiveness and API quota
- Frame probe (if enabled) adds ~5-10s per check and requires yt-dlp installation
- Daily reset is optional but recommended for 24/7 streams

## Security Considerations

- Store `.env` file with restricted permissions: `chmod 600 /opt/vistterstream/.env`
- Never commit `.env` file to version control
- Rotate YouTube API keys periodically
- Consider using systemd DynamicUser for additional isolation
- Review firewall rules to allow only necessary ports

## References

- [systemd.service documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [YouTube Live Streaming API](https://developers.google.com/youtube/v3/live/docs)
- [FFmpeg documentation](https://ffmpeg.org/documentation.html)

