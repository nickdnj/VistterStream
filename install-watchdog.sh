#!/bin/bash
# VistterStream YouTube Watchdog Installation Script
# Run this on your Raspberry Pi or Linux system

set -e  # Exit on error

echo "=========================================="
echo "VistterStream YouTube Watchdog Installer"
echo "=========================================="
echo ""

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "Please do not run this script as root/sudo"
   echo "It will prompt for sudo when needed"
   exit 1
fi

# Check for required commands
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required but not installed"; exit 1; }
command -v pip3 >/dev/null 2>&1 || { echo "Error: pip3 is required but not installed"; exit 1; }
command -v systemctl >/dev/null 2>&1 || { echo "Error: systemd is required but not installed"; exit 1; }

# Detect installation directory
INSTALL_DIR="${INSTALL_DIR:-/opt/vistterstream}"
echo "Installation directory: $INSTALL_DIR"

# Check if directory exists
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Error: Installation directory does not exist: $INSTALL_DIR"
    echo "Please clone the repository first or set INSTALL_DIR environment variable"
    exit 1
fi

cd "$INSTALL_DIR"

echo ""
echo "Step 1: Installing Python dependencies..."
pip3 install aiohttp

echo ""
echo "Step 2: Checking for optional dependencies..."
if command -v yt-dlp >/dev/null 2>&1; then
    echo "✓ yt-dlp is installed (frame probing available)"
else
    echo "⚠ yt-dlp not found (frame probing will be disabled)"
    echo "  Install with: sudo apt-get install -y yt-dlp"
fi

echo ""
echo "Step 3: Checking configuration..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo "⚠ .env file not found"
    echo "Creating from env.sample..."
    cp "$INSTALL_DIR/env.sample" "$INSTALL_DIR/.env"
    echo "✓ Created .env file"
    echo ""
    echo "⚠ IMPORTANT: You must edit .env with your YouTube credentials!"
    echo "  Run: nano $INSTALL_DIR/.env"
    echo ""
    read -p "Press Enter to edit .env now, or Ctrl+C to exit and edit later..."
    nano "$INSTALL_DIR/.env"
else
    echo "✓ .env file exists"
fi

# Secure .env file
chmod 600 "$INSTALL_DIR/.env"

echo ""
echo "Step 4: Setting up log directory..."
sudo mkdir -p /var/log
sudo touch /var/log/vistterstream-watchdog.log
sudo touch /var/log/vistterstream-encoder.log
sudo chown $USER:$USER /var/log/vistterstream-watchdog.log /var/log/vistterstream-encoder.log
echo "✓ Log files created"

echo ""
echo "Step 5: Installing systemd services..."
sudo cp "$INSTALL_DIR/systemd/vistterstream-watchdog.service" /etc/systemd/system/

if [ ! -f "/etc/systemd/system/vistterstream-encoder.service" ]; then
    sudo cp "$INSTALL_DIR/systemd/vistterstream-encoder.service.example" \
            /etc/systemd/system/vistterstream-encoder.service
    echo "✓ Copied encoder service template"
    echo "⚠ IMPORTANT: You must customize the encoder service!"
    echo "  Run: sudo nano /etc/systemd/system/vistterstream-encoder.service"
    echo ""
    read -p "Press Enter to edit encoder service now, or Ctrl+C to exit and edit later..."
    sudo nano /etc/systemd/system/vistterstream-encoder.service
else
    echo "✓ Encoder service already exists (not overwriting)"
fi

echo ""
echo "Step 6: Reloading systemd..."
sudo systemctl daemon-reload
echo "✓ Systemd reloaded"

echo ""
echo "Step 7: Testing watchdog configuration..."
echo "Running quick test (Ctrl+C to skip)..."
cd "$INSTALL_DIR"
if timeout 10s python3 backend/services/youtube_stream_watchdog.py 2>&1 | head -20; then
    echo "✓ Watchdog starts successfully"
else
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ]; then
        echo "✓ Watchdog running (timeout reached, which is expected)"
    else
        echo "⚠ Warning: Watchdog test failed. Check configuration."
    fi
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo ""
echo "1. Verify your .env configuration:"
echo "   nano $INSTALL_DIR/.env"
echo ""
echo "2. Customize encoder service (if needed):"
echo "   sudo nano /etc/systemd/system/vistterstream-encoder.service"
echo ""
echo "3. Enable services to start on boot:"
echo "   sudo systemctl enable vistterstream-encoder"
echo "   sudo systemctl enable vistterstream-watchdog"
echo ""
echo "4. Start the encoder:"
echo "   sudo systemctl start vistterstream-encoder"
echo ""
echo "5. Wait for encoder to connect (~10 seconds), then start watchdog:"
echo "   sleep 10"
echo "   sudo systemctl start vistterstream-watchdog"
echo ""
echo "6. Monitor the watchdog:"
echo "   tail -f /var/log/vistterstream-watchdog.log"
echo ""
echo "7. Check service status:"
echo "   sudo systemctl status vistterstream-encoder"
echo "   sudo systemctl status vistterstream-watchdog"
echo ""
echo "For detailed documentation, see:"
echo "  - YOUTUBE_WATCHDOG_README.md (complete guide)"
echo "  - systemd/README.md (service management)"
echo ""
echo "=========================================="

