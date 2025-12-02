# Cloudflare Tunnel Setup Guide

This guide will help you set up Cloudflare Tunnel to access your VistterStream instance from anywhere on the web without opening any ports on your firewall.

## What is Cloudflare Tunnel?

Cloudflare Tunnel (formerly Argo Tunnel) creates a secure, outbound-only connection from your VistterStream device to Cloudflare's network. This means:

- ✅ **No port forwarding required** - Your firewall can remain completely closed
- ✅ **Automatic HTTPS** - Cloudflare provides SSL certificates automatically
- ✅ **Free** - Cloudflare Tunnel is free for personal use
- ✅ **DDoS Protection** - Your service is protected by Cloudflare's network
- ✅ **Access from anywhere** - Access your VistterStream from any device with a web browser

## Prerequisites

1. A Cloudflare account (free) - [Sign up here](https://dash.cloudflare.com/sign-up)
2. Your domain (vistter.com) added to Cloudflare
3. Docker and Docker Compose installed on your VistterStream device

## Step 1: Add Your Domain to Cloudflare

1. Log in to your [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click **"Add a Site"**
3. Enter your domain (e.g., `vistter.com`)
4. Select a plan (Free plan is sufficient)
5. Cloudflare will scan your existing DNS records
6. Update your domain's nameservers at your registrar to point to Cloudflare (instructions provided by Cloudflare)

## Step 2: Create a Cloudflare Tunnel

1. In the Cloudflare Dashboard, go to **Zero Trust** (or **Networks** > **Tunnels**)
2. Click **"Create a tunnel"**
3. Select **"Cloudflared"** as the connector
4. Give your tunnel a name (e.g., `vistterstream-tunnel`)
5. Click **"Save tunnel"**

## Step 3: Get Your Tunnel Token

After creating the tunnel, Cloudflare will display a command like:

```bash
cloudflared service install <TUNNEL_TOKEN>
```

**Copy the `<TUNNEL_TOKEN>`** - you'll need this in the next step.

Alternatively, you can get the token from:
- Zero Trust Dashboard > Networks > Tunnels > Your Tunnel > Configure

## Step 4: Configure DNS

1. In the tunnel configuration page, click **"Configure"** next to your tunnel
2. Under **Public Hostnames**, click **"Add a public hostname"**
3. Configure:
   - **Subdomain**: `stream` (or your preferred subdomain)
   - **Domain**: Select `vistter.com` (or your domain)
   - **Service Type**: `HTTP`
   - **URL**: `frontend:80` (for the frontend)
4. Click **"Save hostname"**
5. Add another public hostname for the API:
   - **Subdomain**: `stream` (same as above)
   - **Domain**: `vistter.com`
   - **Service Type**: `HTTP`
   - **URL**: `backend:8000`
   - **Path**: `/api/*`
6. Click **"Save hostname"**

**Note**: Cloudflare will automatically create the DNS CNAME record for you.

## Step 5: Configure VistterStream

1. Open your `.env` file in the VistterStream root directory
2. Add the following variables:

```bash
# Cloudflare Tunnel Configuration
CLOUDFLARE_TUNNEL_TOKEN=your-tunnel-token-here
CLOUDFLARE_TUNNEL_DOMAIN=stream.vistter.com
```

Replace `your-tunnel-token-here` with the token you copied in Step 3.

3. Update CORS settings (optional, but recommended):

```bash
CORS_ALLOW_ORIGINS=https://stream.vistter.com
```

## Step 6: Update Docker Compose

The Cloudflare Tunnel service is already configured in `docker/docker-compose.rpi.yml`. If you're using a different compose file, make sure the `cloudflared` service is included.

The service will automatically:
- Use the token from `CLOUDFLARE_TUNNEL_TOKEN` environment variable
- Connect to Cloudflare's network
- Route traffic to your frontend and backend services

## Step 7: Start the Services

1. Navigate to your VistterStream directory
2. Start the services:

```bash
docker-compose -f docker/docker-compose.rpi.yml up -d
```

3. Check that the cloudflared container is running:

```bash
docker ps | grep cloudflared
```

4. Check the logs:

```bash
docker logs vistterstream-cloudflared
```

You should see messages like:
```
INF +--------------------------------------------------------------------------------------------+
INF |  Your quick Tunnel has been created! Visit it:                                             |
INF |  https://stream.vistter.com                                                                |
INF +--------------------------------------------------------------------------------------------+
```

## Step 8: Access Your VistterStream

Open your web browser and navigate to:

```
https://stream.vistter.com
```

You should see the VistterStream login page!

## Troubleshooting

### Tunnel Not Connecting

1. **Check the token**: Make sure `CLOUDFLARE_TUNNEL_TOKEN` is set correctly in your `.env` file
2. **Check logs**: `docker logs vistterstream-cloudflared`
3. **Verify DNS**: Make sure the CNAME record exists in Cloudflare DNS
4. **Check tunnel status**: In Cloudflare Dashboard > Zero Trust > Networks > Tunnels, verify the tunnel shows as "Healthy"

### CORS Errors

If you see CORS errors in the browser console:

1. Make sure `CLOUDFLARE_TUNNEL_DOMAIN` is set in your `.env` file
2. Add the tunnel domain to `CORS_ALLOW_ORIGINS`:
   ```bash
   CORS_ALLOW_ORIGINS=https://stream.vistter.com
   ```
3. Restart the backend service:
   ```bash
   docker-compose -f docker/docker-compose.rpi.yml restart backend
   ```

### Frontend Can't Reach Backend

1. Check that both frontend and backend services are running:
   ```bash
   docker ps
   ```
2. Verify the API URL in the frontend is using the correct domain
3. Check browser console for specific error messages

### Tunnel Shows as "Unhealthy"

1. Check that the cloudflared container is running:
   ```bash
   docker ps | grep cloudflared
   ```
2. Check container logs:
   ```bash
   docker logs vistterstream-cloudflared
   ```
3. Verify the tunnel token is still valid in Cloudflare Dashboard
4. Try recreating the tunnel if the token has expired

### DNS Not Resolving

1. Wait a few minutes for DNS propagation (can take up to 24 hours, but usually much faster)
2. Check DNS records in Cloudflare Dashboard > DNS
3. Verify the CNAME record points to your tunnel (format: `<tunnel-id>.cfargotunnel.com`)

## Advanced Configuration

### Using a Custom Config File

If you need more control over routing, you can edit `docker/cloudflared/config.yml` and use credentials-based authentication instead of token-based.

1. Download your tunnel credentials from Cloudflare Dashboard
2. Save them to `docker/cloudflared/credentials.json`
3. Update `docker/cloudflared/config.yml` with your tunnel ID
4. Remove `CLOUDFLARE_TUNNEL_TOKEN` from your `.env` file

### Multiple Subdomains

You can create multiple tunnels or use different subdomains for different services:

- `stream.vistter.com` - Main VistterStream interface
- `api.vistter.com` - API-only access (if needed)
- `preview.vistter.com` - Preview server (if exposed)

### Access Control

Cloudflare Zero Trust (free tier) allows you to add access policies:

1. Go to Zero Trust > Access > Applications
2. Add an application for `https://stream.vistter.com`
3. Configure access policies (e.g., require email verification, 2FA, etc.)

## Security Considerations

- **HTTPS**: Cloudflare Tunnel automatically provides HTTPS - no certificate management needed
- **Access Control**: Consider using Cloudflare Access to restrict who can access your VistterStream
- **Token Security**: Keep your tunnel token secure - don't commit it to version control
- **Firewall**: Your firewall can remain completely closed - no inbound ports needed

## Cost

Cloudflare Tunnel is **completely free** for personal use. There are no bandwidth limits or connection limits for tunnels.

## Additional Resources

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
- [Cloudflare Community Forums](https://community.cloudflare.com/)

## Support

If you encounter issues not covered in this guide:

1. Check the [VistterStream GitHub Issues](https://github.com/yourusername/VistterStream/issues)
2. Check Cloudflare Tunnel logs: `docker logs vistterstream-cloudflared`
3. Review Cloudflare Dashboard for tunnel status and errors




