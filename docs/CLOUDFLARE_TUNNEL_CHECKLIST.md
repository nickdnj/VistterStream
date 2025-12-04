# Cloudflare Tunnel Setup Checklist

Use this checklist to verify your Cloudflare Tunnel setup is complete and working.

## Cloudflare Dashboard Setup

### ✅ Step 1: Domain Added to Cloudflare
- [ ] Domain `vistter.com` is added to Cloudflare
- [ ] Nameservers are updated at your registrar
- [ ] Domain shows as "Active" in Cloudflare Dashboard

**How to check:**
- Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
- Your domain should appear in the list
- Status should be "Active"

### ✅ Step 2: Tunnel Created
- [ ] Tunnel created in Zero Trust Dashboard
- [ ] Tunnel has a name (e.g., `vistterstream-tunnel`)
- [ ] Tunnel shows as "Healthy" or "Connecting" status

**How to check:**
- Go to [Zero Trust Dashboard](https://one.dash.cloudflare.com/)
- Navigate to **Networks** > **Tunnels**
- Your tunnel should be listed

### ✅ Step 3: Tunnel Token Retrieved
- [ ] Tunnel token copied from Cloudflare Dashboard
- [ ] Token is saved securely (will add to .env file)

**How to get:**
- In Zero Trust > Networks > Tunnels
- Click on your tunnel
- Click **"Configure"**
- Look for the token in the installation command or in the tunnel details
- Format: Long string starting with something like `eyJ...` or similar

### ✅ Step 4: DNS Configuration
- [ ] Public hostname added for frontend
  - Subdomain: `stream`
  - Domain: `vistter.com`
  - Service: `http://frontend:80` (or `http://localhost:80` if not using Docker networking)
- [ ] Public hostname added for backend API
  - Subdomain: `stream` (same)
  - Domain: `vistter.com`
  - Service: `http://backend:8000` (or `http://localhost:8000`)
  - Path: `/api/*`
- [ ] CNAME record created automatically by Cloudflare

**How to check:**
- In Zero Trust > Networks > Tunnels > Your Tunnel > Configure
- Under **Public Hostnames**, you should see entries for:
  - `stream.vistter.com` → `http://frontend:80`
  - `stream.vistter.com` → `http://backend:8000` (Path: `/api/*`)

**Note:** If you're running on the host (not Docker), use `localhost` instead of service names:
- `http://localhost:80` for frontend
- `http://localhost:8000` for backend

## VistterStream Configuration

### ✅ Step 5: Environment Variables
- [ ] `.env` file exists in VistterStream root directory
- [ ] `CLOUDFLARE_TUNNEL_TOKEN` is set with your token
- [ ] `CLOUDFLARE_TUNNEL_DOMAIN` is set to `stream.vistter.com`
- [ ] CORS origins updated (optional but recommended)

**Required in `.env`:**
```bash
CLOUDFLARE_TUNNEL_TOKEN=your-actual-token-here
CLOUDFLARE_TUNNEL_DOMAIN=stream.vistter.com
```

**Optional (recommended):**
```bash
CORS_ALLOW_ORIGINS=http://vistter.local:3000,http://localhost:3000,https://stream.vistter.com
```

### ✅ Step 6: Docker Compose Configuration
- [ ] `docker/docker-compose.rpi.yml` includes cloudflared service
- [ ] Cloudflared service is configured correctly

**How to check:**
- Open `docker/docker-compose.rpi.yml`
- Look for `cloudflared:` service section
- Should reference `CLOUDFLARE_TUNNEL_TOKEN` environment variable

## Testing & Verification

### ✅ Step 7: Start Services
- [ ] Docker Compose services started
- [ ] Cloudflared container is running
- [ ] Cloudflared logs show successful connection

**Commands:**
```bash
# Start services
docker-compose -f docker/docker-compose.rpi.yml up -d

# Check cloudflared is running
docker ps | grep cloudflared

# Check logs
docker logs vistterstream-cloudflared
```

**Expected log output:**
- Should see connection messages
- Should see "Your quick Tunnel has been created!" or similar
- Should show the URL: `https://stream.vistter.com`

### ✅ Step 8: Verify Tunnel Status in Cloudflare
- [ ] Tunnel shows as "Healthy" in Cloudflare Dashboard
- [ ] No error messages in tunnel status

**How to check:**
- Go to Zero Trust > Networks > Tunnels
- Your tunnel should show green/healthy status
- Click on it to see connection details

### ✅ Step 9: Test Access
- [ ] DNS resolves: `nslookup stream.vistter.com` or `dig stream.vistter.com`
- [ ] HTTPS works: `curl -I https://stream.vistter.com`
- [ ] Browser access works: Navigate to `https://stream.vistter.com`
- [ ] Login page loads
- [ ] Can log in successfully
- [ ] API calls work (check browser console for errors)

**Test commands:**
```bash
# Check DNS
nslookup stream.vistter.com
# Should return Cloudflare IPs

# Test HTTPS
curl -I https://stream.vistter.com
# Should return 200 OK or redirect

# Test in browser
# Open https://stream.vistter.com
# Should see VistterStream login page
```

## Troubleshooting Common Issues

### Issue: Tunnel shows as "Unhealthy"
**Solutions:**
1. Check cloudflared container is running: `docker ps | grep cloudflared`
2. Check logs: `docker logs vistterstream-cloudflared`
3. Verify token is correct in `.env` file
4. Check token hasn't expired (regenerate if needed)

### Issue: DNS not resolving
**Solutions:**
1. Wait a few minutes for DNS propagation
2. Check DNS records in Cloudflare Dashboard > DNS
3. Verify CNAME record exists for `stream.vistter.com`
4. Check nameservers are correct at registrar

### Issue: CORS errors in browser
**Solutions:**
1. Add `https://stream.vistter.com` to `CORS_ALLOW_ORIGINS` in `.env`
2. Restart backend: `docker-compose -f docker/docker-compose.rpi.yml restart backend`
3. Check browser console for specific CORS error messages

### Issue: Frontend can't reach backend
**Solutions:**
1. Verify both services are running: `docker ps`
2. Check cloudflared routing configuration in Cloudflare Dashboard
3. Verify path routing: `/api/*` should route to backend
4. Check browser network tab for failed requests

## Quick Verification Script

Run this to check your setup:

```bash
# Check if .env has Cloudflare config
grep -E "CLOUDFLARE_TUNNEL" .env

# Check if cloudflared container exists
docker ps -a | grep cloudflared

# Check cloudflared logs
docker logs vistterstream-cloudflared --tail 20

# Test DNS
nslookup stream.vistter.com

# Test HTTPS
curl -I https://stream.vistter.com 2>&1 | head -5
```

## Next Steps After Setup

Once everything is working:
1. ✅ Test login functionality
2. ✅ Test camera management
3. ✅ Test timeline creation
4. ✅ Test streaming functionality
5. ✅ Consider adding Cloudflare Access for additional security
6. ✅ Document any device-specific configuration needed

