# Beelink Mini S12 to Ubuntu Server 24.04 LTS
## VistterStream Appliance Setup Guide

**Hardware:** Beelink Mini S12 Pro — Intel N95, 8GB RAM, 256GB SSD
**Target OS:** Ubuntu Server 24.04 LTS
**Purpose:** Dedicated VistterStream live streaming appliance

---

## Overview

This guide walks you through wiping Windows 11 Home from a Beelink Mini S12 and replacing it with Ubuntu Server 24.04 LTS, then deploying VistterStream as a Docker-based streaming appliance. The Intel N95 processor includes Quick Sync Video hardware encoding, which significantly reduces CPU load during live streaming.

**Estimated time:** 60–90 minutes for a complete setup.

**What you will need:**
- USB drive (8GB or larger)
- A separate computer to create the bootable USB
- A monitor and keyboard for the initial setup (can go headless after)
- Your home/office network ethernet cable (recommended over Wi-Fi)

---

## Part 1: Prepare the Beelink

### Step 1.1 — Back Up Your Windows Product Key

Before wiping Windows, save the product key in case you ever need it.

Open PowerShell as Administrator on the Beelink and run:

```powershell
(Get-WmiObject -query 'select * from SoftwareLicensingService').OA3xOriginalProductKey
```

Write down or save the key somewhere safe. If it returns blank, the key is embedded in the BIOS firmware and will reactivate automatically if you ever reinstall Windows — so no action needed.

### Step 1.2 — Download Ubuntu Server 24.04 LTS

Go to the official Ubuntu download page:

```
https://ubuntu.com/download/server
```

Download **Ubuntu Server 24.04.x LTS** (the .iso file, approximately 2.7GB). Verify you are getting the LTS release, not a interim release.

### Step 1.3 — Create a Bootable USB Drive

**Option A: Windows (using Rufus)**

1. Download Rufus from https://rufus.ie (free, no install required)
2. Insert your USB drive
3. Open Rufus and select:
   - Device: your USB drive
   - Boot selection: the Ubuntu Server ISO you downloaded
   - Partition scheme: GPT
   - Target system: UEFI (non CSM)
4. Click Start. When prompted about ISO Hybrid image mode, select **Write in DD Image mode**
5. Wait for the write to complete (2–3 minutes)

**Option B: macOS (using Balena Etcher)**

1. Download Balena Etcher from https://etcher.balena.io
2. Open Etcher, click "Flash from file" and select the Ubuntu ISO
3. Click "Select target" and choose your USB drive
4. Click "Flash!" and wait for it to complete
5. Dismiss any macOS warnings about the disk being unreadable — this is normal for Linux bootable drives

### Step 1.4 — Configure Beelink BIOS

1. Shut down the Beelink completely
2. Plug in your USB drive, monitor, and keyboard
3. Power on and immediately press **DEL** repeatedly until the BIOS menu appears

   > If DEL does not work, try F2. The timing is tight — start pressing immediately when you see the Beelink logo.

4. In the BIOS, navigate to the **Boot** tab:
   - Set the boot order so your USB drive is first
   - Look for "Boot Option #1" and change it to your USB drive

5. Navigate to the **Security** tab:
   - Find **Secure Boot** and set it to **Disabled**

   > Ubuntu Server can install with Secure Boot enabled, but disabling it avoids potential driver issues with Intel media drivers and simplifies the setup.

6. Press **F10** to Save and Exit. The system will reboot from your USB drive.

---

## Part 2: Install Ubuntu Server

### Step 2.1 — Boot to the Ubuntu Installer

After BIOS save, the system reboots. You should see the Ubuntu Server boot menu within 10–15 seconds. Select **"Try or Install Ubuntu Server"** and press Enter.

The installer loads in text mode — this is expected for Ubuntu Server. Navigation uses arrow keys, Tab, and Enter.

### Step 2.2 — Language and Keyboard

1. **Language:** Select English (or your preference) and press Enter
2. **Installer update:** If prompted to update the installer, select "Continue without updating" to avoid delays
3. **Keyboard layout:** Select your keyboard layout (typically English US)

### Step 2.3 — Network Configuration

1. The installer will detect your network interfaces
2. If you have an ethernet cable plugged in, it will automatically configure via DHCP — this is what you want for now
3. You will see an IP address assigned (e.g., 192.168.1.x) — note it down, you will use it later
4. If asked about proxy, leave it blank and press Enter

### Step 2.4 — Storage Configuration

1. When you reach **"Guided storage configuration"**, select it and press Enter
2. Select your SSD as the target disk (it will show the 256GB drive)
3. Ensure **"Use an entire disk"** is selected
4. **Uncheck "Set up this disk as an LVM group"** — simpler is better for a single-purpose appliance
5. When shown the storage layout summary, press Enter to confirm
6. When warned that this will erase the disk, select **"Continue"** — this wipes Windows

### Step 2.5 — Profile Setup

Fill in the following fields:

| Field | Value |
|-------|-------|
| Your name | (your name, e.g., Nick) |
| Your server's name | `vistterstream` |
| Pick a username | `vistter` (or your preference) |
| Password | Choose a strong password |
| Confirm password | Re-enter it |

> The hostname `vistterstream` is important — it is used later for accessing the Cockpit admin interface at https://vistterstream:9090.

### Step 2.6 — Ubuntu Pro

When asked about Ubuntu Pro, select **"Skip for now"** and continue. Ubuntu Pro is optional and not required for this setup.

### Step 2.7 — SSH Setup

1. On the **"SSH Setup"** screen, check the box next to **"Install OpenSSH server"**

   > This is critical. It allows you to manage the server remotely via SSH without needing a monitor attached.

2. Leave "Import SSH identity" as No unless you want to import a public key from GitHub

### Step 2.8 — Featured Snaps

Skip all snaps on the "Featured Server Snaps" screen. You will install Docker from the official repository (not snap) in Part 3.

### Step 2.9 — Installation

The installation process begins. It typically takes 5–10 minutes. When complete:

1. Select **"Reboot Now"**
2. When prompted to remove the installation medium, unplug your USB drive and press Enter

The system reboots into Ubuntu Server. You will see a text login prompt after about 30 seconds.

---

## Part 3: Post-Install Essentials

> From this point forward, you can either work directly on the Beelink with a keyboard/monitor attached, or SSH in from another machine. SSH is recommended for ease of copy-pasting commands.
>
> To SSH in from another machine: `ssh vistter@<ip-address-you-noted-earlier>`

### Step 3.1 — Log In

At the login prompt, enter your username and password from Step 2.5.

### Step 3.2 — System Update

Run a full system update before installing anything else:

```bash
sudo apt update && sudo apt upgrade -y
```

This may take 3–5 minutes depending on how many packages need updating. If prompted about kernel updates or service restarts, accept the defaults.

### Step 3.3 — Install Intel Quick Sync Video Drivers

The Intel N95 has Intel UHD Graphics with Quick Sync Video (QSV), which provides hardware-accelerated H.264 and H.265 encoding. This offloads encoding from the CPU and dramatically improves streaming performance.

Install the VA-API media drivers:

```bash
sudo apt install -y intel-media-va-driver-non-free vainfo
```

Verify hardware encoding is available:

```bash
vainfo
```

You should see output similar to:

```
vainfo: VA-API version: 1.20 (libva 2.20.0)
vainfo: Driver version: Intel iHD driver for Intel(R) Gen Graphics - 24.x.x
vainfo: Supported profile and entrypoints
      VAProfileH264ConstrainedBaseline: VAEntrypointVLD
      VAProfileH264ConstrainedBaseline: VAEntrypointEncSliceLP
      VAProfileH264Main               : VAEntrypointVLD
      VAProfileH264Main               : VAEntrypointEncSliceLP
      VAProfileH264High               : VAEntrypointVLD
      VAProfileH264High               : VAEntrypointEncSliceLP
      ...
```

The key entries to look for are `VAEntrypointEncSliceLP` next to H264 profiles. These confirm hardware H.264 encoding is working. If you do not see these, try rebooting and running `vainfo` again.

> If `vainfo` reports no devices found, add your user to the render group:
> `sudo usermod -aG render $USER` then log out and back in.

### Step 3.4 — Install Docker Engine

Install from the official Docker repository — not from the Ubuntu snap store. The snap version has known issues with networking and volume mounts.

**Add Docker's GPG key and repository:**

```bash
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

**Install Docker:**

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

**Add your user to the docker group** (so you can run docker without sudo):

```bash
sudo usermod -aG docker $USER
```

**Apply the group change without logging out:**

```bash
newgrp docker
```

**Verify Docker is running:**

```bash
docker run hello-world
```

You should see a "Hello from Docker!" message. Docker is set to start automatically on boot by default.

### Step 3.5 — Install Tailscale

Tailscale creates a secure private network (VPN mesh) between your devices. This allows you to SSH into the Beelink from anywhere without exposing it to the internet.

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

Start Tailscale and connect to your account:

```bash
sudo tailscale up
```

This prints a URL. Open it on your phone or another computer and log in to your Tailscale account to authorize the device. Once authorized, the terminal shows your Tailscale IP address (in the 100.x.x.x range).

**Note your Tailscale IP** — you can always SSH into the Beelink using this address from any device on your Tailscale network, even from outside your home network:

```bash
ssh vistter@100.x.x.x
```

### Step 3.6 — Install Cockpit (Optional Web Admin)

Cockpit provides a clean web-based dashboard for monitoring system resources, managing services, and viewing logs — useful if you prefer a GUI over command line for day-to-day checks.

```bash
sudo apt install -y cockpit
```

Access Cockpit by opening a browser on another machine and navigating to:

```
https://vistterstream:9090
```

Or using the IP address directly:

```
https://192.168.1.x:9090
```

> Your browser will warn about the self-signed certificate — click "Advanced" and "Accept the Risk" to proceed. Log in with your Ubuntu username and password.

---

## Part 4: Deploy VistterStream

### Step 4.1 — Clone the Repository

Navigate to where you want to store the application and clone the repo:

```bash
cd /opt
sudo git clone https://github.com/your-org/vistterstream.git
sudo chown -R $USER:$USER /opt/vistterstream
cd /opt/vistterstream
```

> If the repository is private, you will need to authenticate with GitHub. Consider setting up a personal access token or SSH key for this.

### Step 4.2 — Configure Environment

Copy the sample environment file and edit it:

```bash
cp .env.sample .env
nano .env
```

Fill in the required configuration values per the VistterStream documentation. Common settings include:
- Domain or local IP for the web UI
- Streaming destinations (RTMP URLs and stream keys)
- Any API keys required

Save and exit nano with **Ctrl+X**, then **Y**, then **Enter**.

### Step 4.3 — Configure Intel Quick Sync Hardware Acceleration

The N95's hardware encoder is accessed via VA-API in FFmpeg. Update the FFmpeg encoder setting in your `.env` or VistterStream configuration to use the Intel hardware encoder instead of software encoding.

**Change the encoder from software (libx264) to hardware:**

| If you see this | Change it to |
|----------------|-------------|
| `libx264` | `h264_qsv` (Intel Quick Sync, preferred) |
| `h264_v4l2m2m` | `h264_vaapi` (VA-API fallback) |

If VistterStream has a hardware acceleration setting in the `.env` file, set it to:

```
FFMPEG_ENCODER=h264_qsv
```

Or if using VA-API directly:

```
FFMPEG_ENCODER=h264_vaapi
VAAPI_DEVICE=/dev/dri/renderD128
```

> To confirm the render device path: `ls /dev/dri/` — you should see `renderD128` (and possibly `card0`).

For VA-API encoding, Docker needs access to the GPU device. Ensure the docker-compose file includes the device mapping:

```yaml
devices:
  - /dev/dri:/dev/dri
```

If this is not already in the compose file, add it under the relevant service definition.

### Step 4.4 — Start VistterStream

```bash
cd /opt/vistterstream
docker compose up -d
```

The `-d` flag runs containers in the background (detached mode).

Watch the startup logs:

```bash
docker compose logs -f
```

Press **Ctrl+C** to stop watching logs (containers keep running).

### Step 4.5 — Access the Web UI

Open a browser and navigate to:

```
http://192.168.1.x:8080
```

Replace `192.168.1.x` with the Beelink's IP address and `8080` with whatever port VistterStream uses (check your `.env` file). You should see the VistterStream web interface.

---

## Part 5: Production Hardening

### Step 5.1 — Set a Static IP Address

DHCP-assigned IPs can change. Set a static IP so the Beelink always has the same address on your network.

Find your current network interface name:

```bash
ip link show
```

Look for an interface that starts with `enp` or `eth` (e.g., `enp2s0`) — this is your ethernet adapter.

Edit the netplan configuration:

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Replace the contents with the following (adjust the interface name, IP, gateway, and DNS for your network):

```yaml
network:
  version: 2
  ethernets:
    enp2s0:
      dhcp4: no
      addresses:
        - 192.168.1.50/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

> Replace `enp2s0` with your actual interface name. Replace `192.168.1.50` with the static IP you want (pick one outside your router's DHCP range). Replace `192.168.1.1` with your router's gateway IP.

Apply the configuration:

```bash
sudo netplan apply
```

Your SSH session may drop if you were connected via the old IP. Reconnect using the new static IP.

### Step 5.2 — Configure UFW Firewall

Enable the firewall and allow only the necessary services:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 9090/tcp   # Cockpit (omit if not using)
sudo ufw enable
```

> Tailscale traffic is automatically handled through its own interface — you do not need to add a specific UFW rule for it.

Verify the rules:

```bash
sudo ufw status
```

You should see:

```
Status: active

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
9090/tcp                   ALLOW       Anywhere
```

### Step 5.3 — Enable Automatic Security Updates

Configure the system to automatically apply security patches:

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

When prompted, select **Yes** to enable automatic updates.

You can verify the configuration is correct:

```bash
cat /etc/apt/apt.conf.d/20auto-upgrades
```

It should show:

```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```

### Step 5.4 — Verify Docker Starts on Boot

Docker is configured to start on boot by default when installed from the official repository. Confirm it:

```bash
sudo systemctl is-enabled docker
```

It should return `enabled`. If not:

```bash
sudo systemctl enable docker
```

Also ensure VistterStream containers restart automatically. In your `docker-compose.yml`, verify the relevant services have restart policies:

```yaml
restart: unless-stopped
```

This ensures containers come back up automatically after a reboot or crash.

### Step 5.5 — Cloudflare Tunnel (Optional)

If you need to expose VistterStream to the internet without opening router ports (ideal for security), use a Cloudflare Tunnel. This is covered in the separate `CLOUDFLARE_TUNNEL_SETUP.md` guide in this docs folder.

---

## Part 6: Quick Reference Card

### SSH Access

**From your local network:**
```bash
ssh vistter@192.168.1.50
```

**From anywhere via Tailscale:**
```bash
ssh vistter@100.x.x.x
```

**Web admin (Cockpit):**
```
https://192.168.1.50:9090
```

---

### VistterStream Commands

**Start VistterStream:**
```bash
cd /opt/vistterstream && docker compose up -d
```

**Stop VistterStream:**
```bash
cd /opt/vistterstream && docker compose down
```

**Restart VistterStream:**
```bash
cd /opt/vistterstream && docker compose restart
```

**View live logs:**
```bash
cd /opt/vistterstream && docker compose logs -f
```

**View logs for a specific service:**
```bash
cd /opt/vistterstream && docker compose logs -f <service-name>
```

---

### Update VistterStream

```bash
cd /opt/vistterstream
git pull
docker compose pull
docker compose up -d
```

---

### System Commands

**Check system resource usage:**
```bash
htop
```
(Install with `sudo apt install htop` if not present)

**Check disk space:**
```bash
df -h
```

**Check Docker container status:**
```bash
docker ps
```

**Check Docker container resource usage:**
```bash
docker stats
```

**Reboot the system:**
```bash
sudo reboot
```

**Shut down the system:**
```bash
sudo shutdown now
```

---

### Verify Hardware Encoding is Active

While a stream is running, check whether the GPU is being used:

```bash
sudo apt install -y intel-gpu-tools
sudo intel_gpu_top
```

You should see non-zero activity in the "Video" or "VideoEnhance" rows when streaming. Press **q** to exit.

---

### Firewall Management

**Check current rules:**
```bash
sudo ufw status
```

**Allow a new port:**
```bash
sudo ufw allow <port>/tcp
```

**Remove a rule:**
```bash
sudo ufw delete allow <port>/tcp
```

---

### Tailscale Commands

**Check Tailscale status:**
```bash
tailscale status
```

**Show your Tailscale IP:**
```bash
tailscale ip -4
```

**Disconnect from Tailscale:**
```bash
sudo tailscale down
```

**Reconnect:**
```bash
sudo tailscale up
```

---

## Troubleshooting

### Docker containers won't start

Check logs for errors:
```bash
cd /opt/vistterstream && docker compose logs
```

Check if another process is using a required port:
```bash
sudo ss -tlnp | grep <port>
```

### Hardware encoding not working

Verify the render device exists:
```bash
ls -la /dev/dri/
```

Check VA-API status:
```bash
vainfo
```

Verify Docker can access the GPU (run a quick test):
```bash
docker run --rm --device /dev/dri:/dev/dri intel/intel-opencl-icd vainfo
```

### Cannot SSH into the server

1. Verify the server is powered on (check the LED on the Beelink)
2. Check the IP address is correct — log in directly with keyboard/monitor and run `ip addr`
3. Verify SSH is running: `sudo systemctl status ssh`
4. Check the firewall: `sudo ufw status`

### Static IP not working

Verify the netplan config has no syntax errors (YAML is whitespace-sensitive):
```bash
sudo netplan --debug apply
```

Check the current assigned addresses:
```bash
ip addr show
```

---

*Guide version: March 2026 | Hardware: Beelink Mini S12 Pro | OS: Ubuntu Server 24.04 LTS*
