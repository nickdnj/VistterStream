#!/bin/bash
# Deployment script for Cloudflare Tunnel setup
# Run this script to deploy to remote device
# Default: 192.168.12.107 (can be overridden with REMOTE_HOST env var)

REMOTE_HOST="${REMOTE_HOST:-192.168.12.107}"
REMOTE_USER="${REMOTE_USER:-vistter}"
REMOTE_DIR="VistterStream"

echo "═══════════════════════════════════════════════════════════════"
echo "Deploying Cloudflare Tunnel Configuration to $REMOTE_USER@$REMOTE_HOST"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Step 1: Check SSH connection
echo "Step 1: Testing SSH connection..."
ssh -o StrictHostKeyChecking=no $REMOTE_USER@$REMOTE_HOST "echo 'SSH connection successful'" || {
    echo "❌ SSH connection failed. Please check:"
    echo "   - Network connectivity to $REMOTE_HOST"
    echo "   - SSH service is running on remote device"
    echo "   - Username and password are correct"
    exit 1
}
echo "✅ SSH connection successful"
echo ""

# Step 2: Check if VistterStream directory exists
echo "Step 2: Checking VistterStream deployment..."
if ssh $REMOTE_USER@$REMOTE_HOST "test -d $REMOTE_DIR"; then
    echo "✅ VistterStream directory exists"
    REMOTE_PATH="$REMOTE_DIR"
else
    echo "⚠️  VistterStream directory not found in home directory"
    echo "   Checking current directory..."
    REMOTE_PATH=$(ssh $REMOTE_USER@$REMOTE_HOST "pwd")
    echo "   Current directory: $REMOTE_PATH"
fi
echo ""

# Step 3: Transfer .env file with Cloudflare token
echo "Step 3: Transferring .env file with Cloudflare Tunnel configuration..."
if [ -f .env ]; then
    # Extract just the Cloudflare-related lines
    grep -E "CLOUDFLARE|TUNNEL" .env > /tmp/cloudflare_env.txt || echo "# Cloudflare Tunnel Configuration" > /tmp/cloudflare_env.txt
    
    # Transfer to remote
    scp .env $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/.env.new || {
        echo "❌ Failed to transfer .env file"
        exit 1
    }
    
    # Backup existing .env and replace
    ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && cp .env .env.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null; mv .env.new .env"
    echo "✅ .env file transferred and updated"
else
    echo "❌ .env file not found locally"
    exit 1
fi
echo ""

# Step 4: Check Docker services
echo "Step 4: Checking Docker services..."
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && docker ps | grep vistter || echo 'No VistterStream containers found'"
echo ""

# Step 5: Pull latest code (if using git)
echo "Step 5: Checking for code updates..."
if ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && git status &>/dev/null"; then
    echo "   Git repository detected, pulling latest changes..."
    ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && git pull"
    echo "✅ Code updated"
else
    echo "   Not a git repository, skipping code update"
fi
echo ""

# Step 6: Start/restart services
echo "Step 6: Starting Docker services with Cloudflare Tunnel..."
# Try docker compose (newer) first, fallback to docker-compose (older)
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && (docker compose -f docker/docker-compose.rpi.yml up -d || docker-compose -f docker/docker-compose.rpi.yml up -d)"
echo ""

# Step 7: Check cloudflared container
echo "Step 7: Verifying cloudflared container..."
sleep 3
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && docker ps | grep cloudflared"
echo ""

# Step 8: Show cloudflared logs
echo "Step 8: Cloudflared container logs (last 20 lines):"
ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_PATH && docker logs vistterstream-cloudflared --tail 20 2>&1"
echo ""

echo "═══════════════════════════════════════════════════════════════"
echo "✅ Deployment complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Verify tunnel is healthy in Cloudflare Dashboard"
echo "2. Test access at: https://stream.vistter.com"
echo "3. Check logs if needed: ssh $REMOTE_USER@$REMOTE_HOST 'cd $REMOTE_PATH && docker logs vistterstream-cloudflared'"
echo ""

