# VistterStream Quick Start Guide

Get streaming in 5 minutes! This guide will walk you through the essential steps to start broadcasting with VistterStream.

---

## Step 1: Login (1 minute)

1. Open your web browser
2. Navigate to your VistterStream appliance: `http://[your-ip-address]:3000`
3. Login with default credentials:
   - **Username:** `admin`
   - **Password:** `admin`
4. **Important:** Change your password immediately (see Step 6)

---

## Step 2: Add Your First Camera (2 minutes)

1. Click **"Cameras"** in the left sidebar
2. Click **"+ Add Camera"** button (top-right)
3. Fill in camera details:
   - **Name:** Give it a descriptive name (e.g., "Front Door Camera")
   - **IP Address:** Your camera's IP address
   - **Port:** Usually `554` for RTSP
   - **Username/Password:** Camera credentials
   - **Type:** Select "STATIONARY" or "PTZ"
4. Click **"Save"**
5. Wait for camera to connect (green status indicator)

**Quick Tip:** Test your camera by clicking "View Live Stream"

---

## Step 3: Configure Streaming Destination (3 minutes)

### For YouTube:

1. Click **"Settings"** in the left sidebar
2. Click the **"📡 Destinations"** tab
3. Click **"+ Add Destination"**
4. Fill in details:
   - **Name:** "My YouTube Channel"
   - **Platform:** Select "YouTube"
   - **RTMP URL:** `rtmp://a.rtmp.youtube.com/live2`
   - **Stream Key:** Get this from YouTube Studio → Go Live → Stream Settings
   - **Channel ID:** (Optional) Your YouTube channel ID
5. Click **"Save"**

### For Custom RTMP:

1. Follow steps 1-3 above
2. Select **"Custom RTMP"**
3. Enter your RTMP server URL and stream key
4. Click **"Save"**

---

## Step 4: Create Your First Timeline (5 minutes)

1. Click **"Timelines"** in the left sidebar
2. Click **"+ New Timeline"** button
3. Configure timeline basics:
   - **Name:** "My First Stream"
   - **Resolution:** 1920x1080 (recommended)
   - **Frame Rate:** 30fps
   - **Duration:** 600 seconds (10 minutes) or as needed

4. **Add camera to timeline:**
   - Look at left panel → **"📷 Cameras"** section
   - Click and drag your camera onto the **Video track**
   - The camera feed will appear as a blue block on the timeline

5. **Save your timeline:**
   - Click **"💾 Save"** button at the top

**Quick Tip:** For now, keep it simple - just one camera on one track. You can add overlays and PTZ presets later!

---

## Step 5: Go Live! (1 minute)

1. In Timeline Editor, select your destination from the dropdown (e.g., "My YouTube Channel")
2. Make sure your timeline is saved
3. Click the **"▶️ Play"** or **"Go Live"** button
4. Monitor the stream status
5. Check your streaming platform to confirm you're live!

**Streaming Controls:**
- **⏹️ Stop** - Stop the stream
- Status indicators show stream health

---

## Step 6: Secure Your System (2 minutes)

**IMPORTANT:** Change your password!

1. Click **"Settings"** in the left sidebar
2. Click **"👤 Account"** tab
3. Enter:
   - **Current Password:** `admin`
   - **New Password:** Choose a strong password (min. 6 characters)
   - **Confirm Password:** Re-enter your new password
4. Click **"Update Password"**

---

## You're All Set! 🎉

Your VistterStream is now configured and ready to broadcast. Here are some next steps:

### Immediate Next Steps:

- **Test your stream** - Do a test broadcast to verify everything works
- **Monitor Dashboard** - Check CPU usage and system health
- **Adjust as needed** - Fine-tune camera positions and stream quality

### Once You're Comfortable:

- **Add more cameras** - Configure additional camera feeds
- **Create PTZ presets** - Save camera positions for PTZ cameras
- **Add overlays** - Create assets for graphics and weather data
- **Set up schedules** - Automate streaming with the Scheduler
- **Advanced timelines** - Create multi-camera productions with cues

---

## Quick Reference

### Essential URLs
- **VistterStream:** `http://[your-ip]:3000`
- **YouTube Live Studio:** https://studio.youtube.com/
- **YouTube Stream Settings:** YouTube Studio → Go Live → Stream

### Default Ports
- Web Interface: `3000`
- RTSP Cameras: `554`
- RTMP Streaming: `1935`

### Dashboard Metrics to Monitor
- ✅ **Active Cameras** - Should match number of configured cameras
- ✅ **Active Streams** - Shows 1+ when streaming
- ⚠️ **CPU Usage** - Should stay under 80% for best performance
- ℹ️ **Uptime** - System reliability indicator

### Common Issues & Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Can't see camera | Check IP address, credentials, and network |
| Stream won't start | Verify stream key, check destination config |
| High CPU usage | Reduce resolution or number of streams |
| Login not working | Try clearing browser cache, use default credentials |

---

## Getting Help

- **Full User Guide:** See `USER_GUIDE.md` for comprehensive documentation
- **System Issues:** Check Dashboard → System tab for version and status
- **Emergency Stop:** Settings → System → "Kill All Streams" button
- **Technical Docs:** Review the `/docs` folder for detailed specifications

---

## Pro Tips for New Users

1. **Start Simple** - Begin with one camera and basic timeline
2. **Test First** - Always test before going live to an audience
3. **Save Often** - Click save frequently when editing timelines
4. **Monitor CPU** - Keep an eye on CPU usage in Dashboard
5. **Name Things Well** - Use descriptive names for cameras, timelines, and destinations
6. **One Thing at a Time** - Add features gradually as you learn the system
7. **Use Preview** - Check "View Live Stream" before adding to timeline
8. **Backup Settings** - Document your configurations

---

## Your First Week Roadmap

### Day 1: Basic Setup ✓
- Login and change password
- Add first camera
- Create simple timeline
- Test stream

### Day 2-3: Expand
- Add remaining cameras
- Create camera presets (if PTZ)
- Test different stream resolutions

### Day 4-5: Enhance
- Add logo/graphic overlays
- Create weather assets
- Build more complex timelines

### Day 6-7: Automate
- Set up streaming schedule
- Create multiple timelines
- Configure backup destinations

---

**Congratulations!** You're now ready to use VistterStream. Start simple, experiment safely, and gradually add more features as you become comfortable with the system.

For detailed information on any feature, refer to the complete **USER_GUIDE.md**.

---

*Happy Streaming! 📹🎬*

