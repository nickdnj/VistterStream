# OAuth with Localhost (Google IP Restriction Fix)

## The Problem

Google OAuth doesn't allow private IP addresses (e.g., `http://192.168.12.107:8000`) as redirect URIs. You'll get:

```
Error 400: invalid_request
device_id and device_name are required for private IP
```

## Solution 1: Use Localhost (Simplest)

### Step 1: Update Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Go to APIs & Services → Credentials
3. Click your OAuth 2.0 Client ID
4. Under "Authorized redirect URIs", **remove** the IP-based URI and **add**:
   ```
   http://localhost:8000/api/destinations/youtube/oauth/callback
   ```
5. Click "Save"

### Step 2: Update VistterStream Destination

1. In VistterStream UI, go to Settings → Destinations
2. Edit "Vistter 2"
3. Scroll to "YouTube OAuth Credentials"
4. Set **OAuth Redirect URI** to:
   ```
   http://localhost:8000/api/destinations/youtube/oauth/callback
   ```
5. Save the destination

### Step 3: Access VistterStream via Localhost

**Important:** When using OAuth, you must access VistterStream through `localhost`, not the IP address.

**From the Raspberry Pi itself** (if you have a monitor/keyboard connected):
```
http://localhost:3000
```

**From your Mac/PC on the same network:**

You need to set up SSH port forwarding to make the Pi's localhost accessible from your machine.

On your Mac/PC, run:
```bash
# Forward Pi's port 3000 (frontend) and 8000 (backend) to your local machine
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 vistter2@192.168.12.107
```

Then open your browser to:
```
http://localhost:3000
```

This will work because:
- Your browser connects to `localhost:3000` (which tunnels to the Pi)
- Backend is at `localhost:8000` (which tunnels to the Pi)
- OAuth redirect goes to `localhost:8000/api/destinations/youtube/oauth/callback` ✅
- Everything is on the same origin, so postMessage works

### Step 4: Test OAuth

1. Open `http://localhost:3000` (via SSH tunnel)
2. Go to Settings → Destinations
3. Edit "Vistter 2"
4. Click "Connect OAuth"
5. Complete Google authorization
6. Should see "✅ Authorization Complete!" and popup auto-closes
7. Status should turn green

## Solution 2: Use Ngrok (Public URL)

If SSH tunneling is too cumbersome, use ngrok to create a public URL:

### Step 1: Install Ngrok on Raspberry Pi

```bash
# On Raspberry Pi
cd ~
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz
tar xvzf ngrok-v3-stable-linux-arm.tgz
sudo mv ngrok /usr/local/bin/
```

### Step 2: Create Ngrok Account

1. Sign up at https://ngrok.com
2. Get your auth token from dashboard
3. Run: `ngrok config add-authtoken YOUR_TOKEN`

### Step 3: Expose Backend

```bash
ngrok http 8000
```

This will give you a URL like: `https://abc123.ngrok-free.app`

### Step 4: Update Google Cloud Console

Add the ngrok URL as redirect URI:
```
https://abc123.ngrok-free.app/api/destinations/youtube/oauth/callback
```

### Step 5: Update VistterStream

Set OAuth Redirect URI to:
```
https://abc123.ngrok-free.app/api/destinations/youtube/oauth/callback
```

**Note:** Free ngrok URLs change every time you restart, so you'll need to update the redirect URI each time.

## Solution 3: Use a Real Domain (Production)

For production, use a real domain with HTTPS:

1. Get a domain (e.g., from Cloudflare, GoDaddy)
2. Point it to your Pi's public IP or use Cloudflare Tunnel
3. Set up HTTPS with Let's Encrypt
4. Use the domain in OAuth redirect URI:
   ```
   https://yourstream.example.com/api/destinations/youtube/oauth/callback
   ```

## Recommended Approach

**For local testing/development:**
- ✅ **Use Solution 1 (SSH tunnel + localhost)**
  - Most reliable
  - Free
  - Secure
  - Permanent (no URL changes)

**For production:**
- ✅ **Use Solution 3 (real domain + HTTPS)**
  - Professional
  - Stable
  - Required for YouTube API quota increase

## Current Configuration

Based on your setup:

**Google Cloud Console:**
- Authorized redirect URI: `http://localhost:8000/api/destinations/youtube/oauth/callback`

**VistterStream Destination:**
- OAuth Redirect URI: `http://localhost:8000/api/destinations/youtube/oauth/callback`

**Access VistterStream:**
- From Mac: SSH tunnel, then `http://localhost:3000`
- From Pi: `http://localhost:3000`

## Troubleshooting

### "OAuth still fails with localhost"

Make sure you're accessing VistterStream via `localhost`, not the IP address.

### "Can't access Pi at localhost from my computer"

Set up SSH port forwarding:
```bash
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 vistter2@192.168.12.107
```

Keep this SSH session open while using VistterStream.

### "PostMessage not working"

This happens when frontend and backend are on different origins. Solutions:
- Use SSH tunnel so everything is on `localhost`
- Or use ngrok for both frontend and backend
- The polling fallback should still work (takes up to 60 seconds)

### "SSH tunnel is annoying"

Use ngrok (Solution 2) or set up a proper domain (Solution 3).

## Why This Happens

Google OAuth has security restrictions:
- ❌ Private IPs blocked: `192.168.x.x`, `10.x.x.x`, `172.16.x.x`
- ✅ Localhost allowed: `localhost`, `127.0.0.1`
- ✅ Public domains allowed: Any public domain with HTTPS

This prevents malicious apps from stealing OAuth tokens on local networks.

## Summary

**Quick fix for now:**
1. Change redirect URI to `http://localhost:8000/api/destinations/youtube/oauth/callback` in both Google Cloud Console and VistterStream
2. Use SSH port forwarding to access Pi via localhost
3. OAuth will work perfectly

**Long-term solution:**
- Get a domain and use HTTPS for production deployment


