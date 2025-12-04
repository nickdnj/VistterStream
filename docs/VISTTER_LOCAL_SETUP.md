# Vistter.local Setup Guide

Access VistterStream at `http://vistter.local:3000` from any device on your network.

---

## Quick Setup

### 1. Set the Hostname on Your Raspberry Pi

```bash
# SSH into your Pi
ssh pi@<your-pi-ip>

# Set hostname to "vistter"
sudo hostnamectl set-hostname vistter

# Restart mDNS service
sudo systemctl restart avahi-daemon

# Verify
hostname
# Output: vistter
```

### 2. Test from Another Device

From your Mac, Windows, or Linux computer:

```bash
ping vistter.local
```

You should see responses from your Pi's IP address.

### 3. Access VistterStream

Open your browser and navigate to:

```
http://vistter.local:3000
```

---

## Why Use vistter.local?

| Benefit | Description |
|---------|-------------|
| **No IP tracking** | Works even if DHCP assigns a new IP |
| **OAuth friendly** | Whitelist one redirect URI for all devices |
| **Multi-device** | Same config works on every Pi |
| **Easy to remember** | `vistter.local` vs `192.168.86.33` |

---

## OAuth Configuration

### Google Cloud Console Setup

Whitelist these redirect URIs in your OAuth 2.0 Client configuration:

```
http://vistter.local:8000/api/destinations/youtube/oauth/callback
http://localhost:8000/api/destinations/youtube/oauth/callback
```

### VistterStream .env Configuration

```bash
# In your .env file on the Pi:
YOUTUBE_OAUTH_REDIRECT_URI=http://vistter.local:8000/api/destinations/youtube/oauth/callback
```

This single URI works for any Pi with the hostname set to `vistter`.

---

## Service URLs

| Service | URL |
|---------|-----|
| Web Interface | `http://vistter.local:3000` |
| Backend API | `http://vistter.local:8000` |
| API Documentation | `http://vistter.local:8000/api/docs` |
| RTMP Ingest | `rtmp://vistter.local:1935/live/<key>` |
| Preview HLS | `http://vistter.local:8888/preview/index.m3u8` |

---

## Troubleshooting

### vistter.local doesn't resolve

**On the Pi:**
```bash
# Check avahi is running
sudo systemctl status avahi-daemon

# If not running, start it
sudo systemctl start avahi-daemon
sudo systemctl enable avahi-daemon

# Check hostname is set
hostname
# Should output: vistter
```

**On your client device:**

| Platform | Solution |
|----------|----------|
| **macOS** | mDNS works out of the box |
| **Linux** | Install `avahi-daemon`: `sudo apt install avahi-daemon` |
| **Windows** | Install [Bonjour Print Services](https://support.apple.com/kb/DL999) or iTunes |
| **iOS/Android** | mDNS works out of the box |

### Multiple Pis on the same network

If you have multiple Raspberry Pis, each needs a unique hostname:

```bash
# On Pi #1
sudo hostnamectl set-hostname vistter1

# On Pi #2  
sudo hostnamectl set-hostname vistter2
```

Access them at `http://vistter1.local:3000` and `http://vistter2.local:3000`.

**Note:** Each Pi will need its own OAuth redirect URI whitelisted if using different hostnames.

### Fallback to IP address

If mDNS isn't working, you can always use the IP address:

```bash
# Find your Pi's IP
hostname -I

# Access via IP
http://192.168.x.x:3000
```

Update your `.env` file to include the IP in CORS:

```bash
CORS_ALLOW_ORIGINS=http://vistter.local:3000,http://192.168.x.x:3000,http://localhost:3000
```

---

## How mDNS Works

mDNS (Multicast DNS) allows devices to discover each other on a local network without a central DNS server.

1. Your Pi broadcasts: "I am `vistter.local` at IP `192.168.x.x`"
2. Other devices on the network hear this broadcast
3. When you request `vistter.local`, your device knows the IP

**Requirements:**
- Both devices must be on the same local network
- The client must support mDNS (most modern devices do)
- The Pi must have `avahi-daemon` running (installed by default on Raspberry Pi OS)

---

## Configuration Files

### .env (on the Pi)

```bash
# Recommended configuration for vistter.local
CORS_ALLOW_ORIGINS=http://vistter.local:3000,http://localhost:3000
YOUTUBE_OAUTH_REDIRECT_URI=http://vistter.local:8000/api/destinations/youtube/oauth/callback

# Leave unset for auto-detection (recommended)
# REACT_APP_API_URL=
```

### docker-compose.rpi.yml

The default configuration already supports `vistter.local`:

```yaml
environment:
  - CORS_ALLOW_ORIGINS=${CORS_ALLOW_ORIGINS:-http://vistter.local:3000,http://localhost:3000}
```

---

## Summary

1. **Set hostname:** `sudo hostnamectl set-hostname vistter`
2. **Restart avahi:** `sudo systemctl restart avahi-daemon`
3. **Access:** `http://vistter.local:3000`
4. **OAuth:** Whitelist `http://vistter.local:8000/api/destinations/youtube/oauth/callback`

That's it! No more tracking IP addresses.

