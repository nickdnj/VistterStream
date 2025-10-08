#!/bin/bash
# VistterStream Preview System Installation Script
# For macOS and Linux (Raspberry Pi)

set -e

echo "🚀 VistterStream Preview System Installer"
echo "=========================================="
echo ""

# Detect OS
OS_TYPE=$(uname -s)
ARCH=$(uname -m)

echo "📋 Detected: $OS_TYPE ($ARCH)"
echo ""

# Step 1: Install MediaMTX
echo "📦 Step 1: Installing MediaMTX..."

if [ "$OS_TYPE" = "Darwin" ]; then
    # macOS
    if [ "$ARCH" = "arm64" ]; then
        MEDIAMTX_URL="https://github.com/bluenviron/mediamtx/releases/download/v1.15.1/mediamtx_v1.15.1_darwin_arm64.tar.gz"
    else
        MEDIAMTX_URL="https://github.com/bluenviron/mediamtx/releases/download/v1.15.1/mediamtx_v1.15.1_darwin_amd64.tar.gz"
    fi
elif [ "$OS_TYPE" = "Linux" ]; then
    # Linux / Raspberry Pi
    if [ "$ARCH" = "aarch64" ]; then
        MEDIAMTX_URL="https://github.com/bluenviron/mediamtx/releases/download/v1.15.1/mediamtx_v1.15.1_linux_arm64.tar.gz"
    else
        MEDIAMTX_URL="https://github.com/bluenviron/mediamtx/releases/download/v1.15.1/mediamtx_v1.15.1_linux_amd64.tar.gz"
    fi
else
    echo "❌ Unsupported OS: $OS_TYPE"
    exit 1
fi

# Download MediaMTX
echo "⬇️  Downloading MediaMTX from $MEDIAMTX_URL"
curl -L -o /tmp/mediamtx.tar.gz "$MEDIAMTX_URL"

# Extract
echo "📂 Extracting MediaMTX..."
cd /tmp
tar -xzf mediamtx.tar.gz

# Install
echo "📥 Installing MediaMTX to /usr/local/bin..."
sudo mv mediamtx /usr/local/bin/
sudo chmod +x /usr/local/bin/mediamtx

# Create config directory
echo "📁 Creating configuration directory..."
sudo mkdir -p /etc/vistterstream
sudo cp "$(dirname "$0")/docker/mediamtx/mediamtx.yml" /etc/vistterstream/

echo "✅ MediaMTX installed successfully!"
echo ""

# Step 2: Install systemd service (Linux only)
if [ "$OS_TYPE" = "Linux" ]; then
    echo "📦 Step 2: Installing systemd service..."
    
    # Update user in service file if not 'pi'
    CURRENT_USER=$(whoami)
    sed "s/User=pi/User=$CURRENT_USER/" "$(dirname "$0")/docker/mediamtx/vistterstream-preview.service" | sudo tee /etc/systemd/system/vistterstream-preview.service > /dev/null
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable and start service
    sudo systemctl enable vistterstream-preview
    sudo systemctl start vistterstream-preview
    
    echo "✅ MediaMTX service installed and started!"
    echo ""
    
    # Check status
    echo "📊 Service status:"
    sudo systemctl status vistterstream-preview --no-pager || true
    echo ""
else
    echo "ℹ️  Step 2: Skipped (systemd not available on macOS)"
    echo "   To start MediaMTX manually, run:"
    echo "   mediamtx /etc/vistterstream/mediamtx.yml"
    echo ""
fi

# Step 3: Install Python dependencies
echo "📦 Step 3: Installing Python dependencies..."
cd "$(dirname "$0")"
source venv/bin/activate
pip install httpx
echo "✅ Python dependencies installed!"
echo ""

# Step 4: Install frontend dependencies
echo "📦 Step 4: Installing frontend dependencies..."
cd frontend
npm install
echo "✅ Frontend dependencies installed!"
echo ""

# Step 5: Test MediaMTX
echo "🔍 Step 5: Testing MediaMTX..."
if curl -s http://localhost:9997/v1/config/get > /dev/null 2>&1; then
    echo "✅ MediaMTX is running and healthy!"
else
    echo "⚠️  MediaMTX is not responding. You may need to start it manually."
    if [ "$OS_TYPE" = "Darwin" ]; then
        echo "   Run: mediamtx /etc/vistterstream/mediamtx.yml"
    else
        echo "   Run: sudo systemctl start vistterstream-preview"
    fi
fi
echo ""

# Done!
echo "🎉 Preview System Installation Complete!"
echo ""
echo "Next steps:"
echo "1. Start VistterStream backend: cd backend && python start.py"
echo "2. Start frontend dev server: cd frontend && npm start"
echo "3. Open http://localhost:3000 in your browser"
echo "4. Go to Timeline Editor and try the Preview feature!"
echo ""
echo "For more information, see:"
echo "  - docs/PreviewSystem-QuickStart.md"
echo "  - docs/PreviewSystem-Specification.md"
echo ""
