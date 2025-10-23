# Raspberry Pi Setup Guide

This guide walks you through deploying VistterStream on a Raspberry Pi 5 using Docker.

---

## Prerequisites

### On Your Raspberry Pi
- Raspberry Pi 5 (or Pi 4 with 4GB+ RAM)
- Raspberry Pi OS (64-bit) - Bookworm or later
- Docker and Docker Compose installed
- Internet connection
- Access to your local network

### Check Your Pi
```bash
# Check OS architecture (should show aarch64)
uname -m

# Check Docker is installed
docker --version
docker compose version

# Check video device (Pi 5 only)
ls -l /dev/video11
```

---

## Step 1: Install Docker (if not installed)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Log out and back in for group changes to take effect
```

---

## Step 2: Clone Repository from GitHub

```bash
# Navigate to your home directory
cd ~

# Clone the repository
git clone https://github.com/nickdnj/VistterStream.git

# Enter the directory
cd VistterStream
```

**That's it!** All the Docker files are now on your Pi.

---

## Step 3: Configure Environment

```bash
# Copy the sample environment file
cp env.sample .env

# Edit the environment file
nano .env
```

**Important:** Update `CORS_ALLOW_ORIGINS` with your Pi's IP address:

```bash
# Find your Pi's IP address
hostname -I

# In .env, change this line:
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:5173

# To include your Pi's IP (example: 192.168.1.100):
CORS_ALLOW_ORIGINS=http://192.168.1.100:3000,http://localhost:3000
```

Save and exit (Ctrl+X, Y, Enter).

---

## Step 4: Build Docker Images

This will take 30-60 minutes on Raspberry Pi due to ARM compilation.

```bash
cd docker
docker compose -f docker-compose.rpi.yml build
```

**What's being built:**
- Backend: Python + FFmpeg + dependencies (~45 min)
- RTMP Relay: nginx with RTMP module (~5 min)
- Preview: Downloaded pre-built (MediaMTX)
- Frontend: Node build + nginx (~10 min)

**Coffee break time!** ☕

---

## Step 5: Start Services

```bash
docker compose -f docker-compose.rpi.yml up -d
```

Check status:
```bash
docker compose -f docker-compose.rpi.yml ps
```

You should see 4 services running:
- `vistterstream-backend`
- `vistterstream-rtmp-relay`
- `vistterstream-preview`
- `vistterstream-frontend`

---

## Step 6: Verify Deployment

### Backend API
```bash
curl http://localhost:8000/api/health
# Should return: {"status":"healthy","service":"VistterStream API","version":"1.0.0"}
```

### Frontend
```bash
curl -I http://localhost:3000
# Should return: HTTP/1.1 200 OK
```

### From Another Computer
Open a browser and navigate to:
```
http://<pi-ip-address>:3000
```

Example: `http://192.168.1.100:3000`

---

## Step 7: Add Cameras

1. Open the web interface at `http://<pi-ip>:3000`
2. Log in (default credentials if first time)
3. Go to **Cameras** section
4. Click **Add Camera**
5. Enter camera details:
   - Name
   - RTSP URL
   - Credentials
6. Test the camera connection

---

## Troubleshooting

### Services Won't Start

**Check logs:**
```bash
cd ~/VistterStream/docker
docker compose -f docker-compose.rpi.yml logs backend
docker compose -f docker-compose.rpi.yml logs frontend
```

### Frontend Can't Connect to Backend

**Check CORS configuration:**
```bash
docker exec vistterstream-backend env | grep CORS
```

Should include your Pi's IP. If not, edit `.env` and restart:
```bash
nano ../.env
docker compose -f docker-compose.rpi.yml restart backend
```

### Hardware Encoder Not Detected

**Check video device:**
```bash
ls -l /dev/video11
```

**Check backend logs:**
```bash
docker compose -f docker-compose.rpi.yml logs backend | grep -i "hardware\|encoder"
```

Should see: `"Hardware capabilities: h264_v4l2m2m on pi5"`

### Camera Relays Not Starting

**Check camera connectivity from Pi:**
```bash
# Test RTSP stream
ffmpeg -rtsp_transport tcp -i rtsp://username:password@camera-ip:554/path -frames:v 1 -f null -
```

### Port Conflicts

If ports 8000, 3000, 1935, etc. are already in use:
```bash
# Check what's using a port
sudo lsof -i :8000

# Stop conflicting service or change ports in docker-compose.rpi.yml
```

---

## Updating the Application

### Pull Latest Changes
```bash
cd ~/VistterStream
git pull origin master
```

### Rebuild and Restart
```bash
cd docker
docker compose -f docker-compose.rpi.yml down
docker compose -f docker-compose.rpi.yml build
docker compose -f docker-compose.rpi.yml up -d
```

---

## Managing Services

### View Logs
```bash
cd ~/VistterStream/docker

# All services
docker compose -f docker-compose.rpi.yml logs -f

# Specific service
docker compose -f docker-compose.rpi.yml logs -f backend
```

### Restart Services
```bash
# All services
docker compose -f docker-compose.rpi.yml restart

# Specific service
docker compose -f docker-compose.rpi.yml restart backend
```

### Stop Services
```bash
docker compose -f docker-compose.rpi.yml down
```

### Start Services
```bash
docker compose -f docker-compose.rpi.yml up -d
```

---

## Data Persistence

Your data is stored in Docker volumes:
- Database: `/data/vistterstream.db` (inside `vistter_data` volume)
- Uploads: `/data/uploads` (inside `vistter_data` volume)

**To backup:**
```bash
docker run --rm -v vistter_data:/data -v $(pwd):/backup alpine tar czf /backup/vistter-backup.tar.gz /data
```

**To restore:**
```bash
docker run --rm -v vistter_data:/data -v $(pwd):/backup alpine tar xzf /backup/vistter-backup.tar.gz -C /
```

---

## Performance Notes

### Pi 5 Hardware Encoding
- Supports 3x concurrent 1080p30 streams
- V4L2 encoder via `/dev/video11`
- Lower CPU usage vs software encoding

### Pi 4 Considerations
- Software encoding only (no V4L2)
- Limit to 1-2 concurrent 720p streams
- Higher CPU usage

---

## Security Recommendations

1. **Change default credentials** immediately
2. **Use strong passwords** for cameras
3. **Keep Pi updated**: `sudo apt update && sudo apt upgrade`
4. **Enable firewall** if exposing to internet
5. **Use HTTPS** in production (add reverse proxy)

---

## Support

- **Documentation**: See `docs/` folder
- **Issues**: GitHub Issues
- **Full Docker testing report**: `docs/Docker-Testing-Complete.md`

---

## Quick Reference

| Service | Port | Access |
|---------|------|--------|
| Frontend | 3000 | `http://<pi-ip>:3000` |
| Backend API | 8000 | `http://<pi-ip>:8000` |
| API Docs | 8000 | `http://<pi-ip>:8000/api/docs` |
| RTMP Relay | 1935 | `rtmp://<pi-ip>:1935/live/<key>` |
| Preview RTMP | 1936 | `rtmp://<pi-ip>:1936/` |
| Preview HLS | 8888 | `http://<pi-ip>:8888/` |
| MediaMTX API | 9997 | `http://<pi-ip>:9997` |

---

**You're ready to stream!** 🎬





