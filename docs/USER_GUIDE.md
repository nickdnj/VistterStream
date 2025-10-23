# VistterStream User Guide

**Version:** 1.0.0-beta  
**Last Updated:** October 23, 2025

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard](#dashboard)
3. [Camera Management](#camera-management)
4. [Stream Management](#stream-management)
5. [Timeline Editor](#timeline-editor)
6. [Scheduler](#scheduler)
7. [Settings](#settings)
   - [General Settings](#general-settings)
   - [Account Security](#account-security)
   - [PTZ Presets](#ptz-presets)
   - [Assets](#assets)
   - [Destinations](#destinations)
   - [System Information](#system-information)

---

## Getting Started

### Logging In

VistterStream is accessed through a web browser at your appliance's IP address (default port 3000).

**Default Credentials:**
- **Username:** `admin`
- **Password:** `admin`

> ⚠️ **Security Note:** It's highly recommended to change the default password after your first login. See [Account Security](#account-security) section.

**Login Page Features:**
- Clean, modern interface with VistterStream branding
- Username and password fields
- Secure authentication
- Remember to change default credentials immediately for security

---

## Dashboard

The Dashboard is your central hub for monitoring the VistterStream appliance status.

### Overview Cards

The dashboard displays four key metrics:

1. **Active Cameras** - Number of connected and operational cameras (e.g., 2)
2. **Active Streams** - Number of currently running streams (e.g., 0)
3. **CPU Usage** - Real-time CPU utilization percentage (e.g., 58.1%)
4. **Uptime** - How long the system has been running (e.g., 66h 53m)

### Camera Status

The dashboard shows a quick overview of your cameras with:
- Camera name and type (STATIONARY or PTZ)
- Connection protocol (RTSP)
- IP address and port
- Last seen timestamp
- Quick "View Details" link for each camera
- "Add Camera" button to configure new cameras

**Example Cameras Shown:**
- **Reolink Wharfside** - STATIONARY camera at 192.168.12.37
- **Sunba** - PTZ camera at 192.168.12.59

### Navigation

The left sidebar provides easy access to all main sections:
- 🏠 Dashboard
- 📷 Cameras
- ▶️ Streams
- 🎬 Timelines
- 📅 Scheduler
- ⚙️ Settings

The top-right corner shows:
- Current user (admin)
- User role (Administrator)
- Sign out button

---

## Camera Management

The Camera Management page allows you to view, configure, and manage all connected IP cameras.

### Camera List

Cameras are displayed in a table format with:
- **Preview** - Live snapshot thumbnail (click to view full stream)
- **Camera Name** - Clickable to view live stream
- **Protocol** - RTSP indicator
- **Type** - STATIONARY or PTZ badge
- **Address** - IP address and port number
- **Status** - Green indicator for healthy cameras
- **Actions:**
  - 🎥 **View Live Stream** - Opens live camera feed
  - ✏️ **Edit** - Modify camera settings
  - 🗑️ **Delete** - Remove camera from system

### Adding a Camera

Click the **"+ Add Camera"** button in the top-right to configure a new camera. You'll need:
- Camera name
- IP address
- Port number
- RTSP credentials
- Camera type (Stationary or PTZ)

### Camera Types

**STATIONARY**
- Fixed position cameras
- No pan/tilt/zoom controls
- Ideal for static monitoring positions

**PTZ (Pan-Tilt-Zoom)**
- Controllable camera movement
- Supports preset positions
- Can be automated in timelines

---

## Stream Management

The Stream Management page is where you configure output streams to platforms like YouTube, Facebook, and Twitch.

### Current Status

If no streams are configured, you'll see:
- **"No streams configured"** message
- Helpful prompt: "Create your first stream to go live on YouTube, Facebook, or Twitch"
- **"+ Add Stream"** or **"Create Stream"** buttons

### Stream Configuration

When adding a stream, you can:
- Choose streaming platform (YouTube, Facebook, Twitch, Custom RTMP)
- Configure stream key and destination
- Link to streaming destinations configured in Settings
- Set stream quality and encoding parameters

### Supported Platforms

- **YouTube Live** - Stream directly to your YouTube channel
- **Facebook Live** - Broadcast to your Facebook page
- **Twitch** - Go live on Twitch
- **Custom RTMP** - Any RTMP-compatible service

---

## Timeline Editor

The Timeline Editor is VistterStream's most powerful feature - a video production timeline for creating sophisticated multi-camera broadcasts.

### Timeline Overview

**Header Information:**
- Timeline name (e.g., "Wharfside Marina")
- Output resolution (e.g., 1920x1080)
- Frame rate (e.g., 30fps)
- Loop mode indicator

**Key Controls:**
- **+ New Timeline** - Create additional timelines
- **💾 Save** - Save timeline changes
- **⏹️ Stop** - Stop timeline playback
- **Destination Selector** - Choose which destination to stream to (e.g., "Vistter 2")

### Left Panel

**📷 Cameras**
- Shows all available cameras (2 cameras shown)
- Lists camera names and types:
  - Reolink Wharfside (Fixed)
  - Sunba (PTZ)
- Drag cameras onto the timeline to add video segments

**🎨 Assets**
- Shows number of available overlay assets (5 assets shown)
- Includes graphics, weather data, images
- Drag assets onto overlay tracks

**Timelines**
- List of saved timelines
- Currently showing "Wharfside Marina"
- Delete option for each timeline

**Live Control**
- Quick links to YouTube Live Studio
- Preview Channel Page option
- Helps monitor your live broadcast

### Timeline Tracks

**Track Types:**
- **🎥 Video Track** - Main camera video feeds
- **🎨 Overlay Track** - Graphics and overlays on top of video
- **🔊 Audio Track** - Audio sources (can be added)

Each track has:
- Track name and icon
- Remove track button (trash icon)
- Visual timeline with time markers

### Timeline Controls

**Playhead Position:**
- Current time: 0:00.0
- Total duration: 10:00.0
- Red playhead line shows current position

**Zoom Controls:**
- Current zoom: 100%
- **−** Zoom out (Ctrl + -)
- **+** Zoom in (Ctrl + +)
- **⏮️** Reset to start button

**Time Ruler:**
- Shows time in seconds (0s, 1s, 2s, etc.)
- Extends to full timeline duration (600s = 10 minutes)
- Precise positioning for cues and segments

### Adding Content

**Add Track Buttons:**
- **🎥 Video** - Add video track
- **🎨 Overlay** - Add overlay track
- **🔊 Audio** - Add audio track

### Timeline Cues

The timeline shows scheduled camera positions and overlays:

**PTZ Cues** (shown in blue on video track):
- **Sunba** camera with preset position
- **🎯 Preset Name** (e.g., "C-Dock", "B-Dock", "A-Dock")
- Start time (e.g., 200.5s, 201.5s)
- Delete cue button on each

**Overlay Cues** (shown in purple on overlay track):
- Asset name (e.g., "Tempest Weather", "NOAA Tide Forecast")
- **🌐 api image** indicator for dynamic content
- Duration and timing
- Delete cue button

**Example Overlays Visible:**
- Tempest Weather
- Tempest 5-Hour Forecast
- Tempest 5-Day Forecast
- NOAA Tide Forecast

### Timeline Workflow

1. **Create Timeline** - Click "+ New Timeline"
2. **Set Parameters** - Configure resolution, fps, duration
3. **Add Video Track** - Drag cameras onto timeline
4. **Position Cues** - Click timeline to place camera switches or PTZ movements
5. **Add Overlays** - Drag assets onto overlay track
6. **Preview** - Use playback controls to test
7. **Save** - Click save button
8. **Stream** - Select destination and start streaming

---

## Scheduler

The Scheduler allows you to automate timeline playback on a recurring schedule.

### Create Schedule

**Schedule Configuration:**
- **Name** - Schedule identifier (e.g., "New Schedule")
- **Start Time** - When to begin streaming (e.g., 06:00 AM)
- **End Time** - When to stop streaming (e.g., 11:00 PM)
- **Days** - Select days of the week:
  - Mon, Tue, Wed, Thu, Fri, Sat, Sun
  - Click to toggle each day
  - Selected days are highlighted in blue

**Timelines Selection:**
- Checkbox list of available timelines
- Select one or more timelines to schedule
- Example: "Wharfside Marina"

**Save Schedule Button:**
- Click to save the schedule configuration

### Existing Schedules

The right panel shows all configured schedules:

**Schedule Card Shows:**
- Schedule name
- Time range (e.g., "06:00-23:00")
- Active days (e.g., "Days: 0,1,2,3,4,5,6")
- Status indicator (Idle/Active)
- Number of timelines (e.g., "Timelines: 1")
- **Start Now** button (blue) - Begin streaming immediately
- **Stop** button (gray) - Stop active schedule
- **Delete** button (red) - Remove schedule

### Schedule Behavior

- Schedules run automatically at configured times
- Multiple schedules can run on different days
- Schedules will activate the selected timeline(s)
- Manual override available with Start Now/Stop buttons

---

## Settings

The Settings page provides comprehensive configuration for your VistterStream appliance.

### Settings Navigation

Six tabs organize different setting categories:
- ⚙️ **General** - System configuration
- 👤 **Account** - Password management
- 🎯 **PTZ Presets** - Camera position management
- 🎨 **Assets** - Overlay content management
- 📡 **Destinations** - Streaming outputs
- 💻 **System** - System information and emergency controls

---

### General Settings

Basic system configuration options.

**Available Settings:**
- **Appliance Name** - Currently: "VistterStream Appliance" (disabled)
- **Timezone** - Currently: "America/New_York" (disabled)

> 📝 **Note:** These settings are currently disabled but will be configurable in future updates.

---

### Account Security

Manage the administrator account password.

**Current User:**
- Signed in as: **admin**

**Change Password Form:**
- **Current Password** - Enter existing password
- **New Password** - Enter new password (minimum 6 characters)
- **Confirm Password** - Re-enter new password
- **Update Password** button

**Security Requirements:**
- Password must be at least 6 characters
- All fields are required
- Current password must be verified

> 🔒 **Best Practice:** Use a strong, unique password for your VistterStream appliance. Change the default password immediately after first login.

---

### PTZ Presets

Manage saved camera positions for PTZ (Pan-Tilt-Zoom) cameras.

**Camera Selection:**
- Dropdown to select PTZ camera
- Example: "Sunba - 192.168.12.59"

**Capture Preset Button:**
- **📸 Capture Preset** - Save current camera position

### Preset List

Each camera shows its presets organized by camera:

**📹 Sunba** - 3 presets

Each preset card displays:
- **Preset Name** (e.g., "C-Dock", "B-Dock", "A-Dock")
- **PTZ Values:**
  - **PAN** - Horizontal position (e.g., -1.000)
  - **TILT** - Vertical position (e.g., -1.000)
  - **ZOOM** - Zoom level (e.g., 0.000)
- **Created Date/Time** - When preset was saved
- **Action Buttons:**
  - **✏️ Edit** - Modify preset name or values
  - **🎯 Go To** - Move camera to this position now
  - **🗑️ Delete** - Remove preset

### Using PTZ Presets

1. **Position Camera** - Use PTZ controls to move camera to desired position
2. **Capture** - Click "📸 Capture Preset" button
3. **Name Preset** - Give it a descriptive name
4. **Use in Timeline** - Drag preset onto timeline editor
5. **Recall** - Click "🎯 Go To" to move camera instantly

---

### Assets

Manage overlay graphics, images, videos, and dynamic content for your streams.

**Add Asset Button:**
- **+ Add Asset** - Create new asset

### Asset Types

VistterStream supports multiple asset types:
- **Static Images** - PNG, JPG graphics
- **Videos** - MP4, MOV files
- **API Images** - Dynamic content from web APIs
- **Weather Data** - Live weather overlays
- **Custom Graphics** - Logos, lower thirds, etc.

### Current Assets

The system shows 5 configured assets:

**1. Weather-Tides Monitor**
- Type: API IMAGE
- Position: Middle Left
- Size: 1700 × Auto px
- Opacity: 100%
- Refresh: 30s
- Shows current conditions

**2. Tempest Weather**
- Type: API IMAGE
- Position: Middle Left
- Opacity: 100%
- Refresh: 30s
- Current weather data

**3. Tempest 5-Hour Forecast**
- Type: API IMAGE
- Tempest 5-Hour Forecast
- Position: Middle Left
- Opacity: 100%
- Refresh: 30s
- Short-term weather forecast

**4. Tempest 5-Day Forecast**
- Type: API IMAGE
- Tempest 5-Day Forecast
- Position: Middle Left
- Opacity: 100%
- Refresh: 30s
- Extended forecast

**5. NOAA Tide Forecast**
- Type: API IMAGE
- Tempest 5-Day Forecast (label on card)
- Position: Middle Left
- Opacity: 100%
- Refresh: 30s
- Tide predictions

### Asset Actions

Each asset card has four action buttons:
- **✏️ Edit** (Blue) - Modify asset settings
- **📄 Copy** (Orange) - Duplicate asset
- **📌 Pin** (Green) - Pin to timeline
- **🗑️ Delete** (Red) - Remove asset

### Creating Assets

Click **"+ Add Asset"** or **"Create First Asset"** to:
1. Choose asset type
2. Configure source (file upload, API URL, etc.)
3. Set position and size
4. Configure opacity and refresh rate
5. Name the asset
6. Save

---

### Destinations

Configure where your streams will be broadcast.

**Add Destination Button:**
- **+ Add Destination** - Add new streaming destination

### Destination Types

- **YouTube** - Stream to YouTube Live
- **Facebook** - Broadcast to Facebook Live
- **Twitch** - Stream to Twitch
- **Custom RTMP** - Any RTMP server

### Configured Destination

**Vistter 2** (YouTube destination)
- Platform: YouTube (red badge)
- Status: Active (green badge)
- Type: RTMP Server

**Configuration Details:**
- **RTMP Server:** `rtmp://a.rtmp.youtube.com/live2`
- **Channel ID:** Not set
- **Stream Key:** •••••••••••••••• (hidden, click "Show" to reveal)
- **Last used:** 10/22/2025

**Actions:**
- **Edit** (gray button) - Modify destination settings
- **Delete** (red button) - Remove destination

### Adding a Destination

1. Click **"+ Add Destination"**
2. Select platform (YouTube, Facebook, Twitch, Custom)
3. Enter stream information:
   - RTMP URL
   - Stream key
   - Channel ID (optional, for YouTube features)
4. Name the destination
5. Save

### Using Destinations

- Destinations appear in Timeline Editor destination selector
- Choose which destination to stream to when going live
- Multiple destinations can be configured
- Switch between destinations without re-configuration

---

### System Information

View system details and access emergency controls.

**System Details:**
- **Version:** 1.0.0-beta
- **Platform:** macOS
- **Database:** SQLite
- **FFmpeg:** 7.1.1

### Emergency Controls

**Kill All Streams**
- Red button: **⚠️ Kill All Streams**
- Description: "Forcefully stop all FFmpeg processes"
- Use case: Emergency stop for unresponsive streams

⚠️ **Warning:** This will immediately terminate all active streams and FFmpeg processes. Use only when streams are unresponsive or you need to stop everything quickly.

**When to Use Emergency Stop:**
- Streams become unresponsive
- System resource issues
- Need to stop all streaming immediately
- FFmpeg processes are hung

---

## Tips and Best Practices

### Camera Setup
- Test each camera connection before adding to timeline
- Use descriptive names for easy identification
- For PTZ cameras, create presets before timeline production

### Timeline Production
- Start with a simple timeline to learn the interface
- Save frequently while editing
- Test timeline playback before going live
- Use meaningful names for timelines and cues

### Scheduling
- Test schedules with short durations first
- Verify timezone settings match your location
- Monitor first scheduled stream to ensure proper operation
- Use descriptive schedule names

### Streaming
- Configure destinations before creating timelines
- Test stream keys and URLs before going live
- Monitor system resources (CPU usage) during streaming
- Keep stream keys secure (never share publicly)

### Asset Management
- Organize assets with clear naming conventions
- Test API-based assets to ensure data sources are accessible
- Set appropriate refresh rates for dynamic content
- Use optimal image sizes for your output resolution

### Security
- Change default admin password immediately
- Use strong passwords (minimum 6 characters, recommended 12+)
- Regularly review access logs
- Keep system software updated

---

## Troubleshooting

### Cannot Login
- Verify correct IP address and port (default: 3000)
- Check network connectivity
- Try default credentials: admin/admin
- Clear browser cache and cookies

### Camera Not Connecting
- Verify camera is powered on and connected to network
- Check IP address is correct
- Confirm RTSP port (usually 554)
- Test camera credentials
- Ensure camera supports RTSP protocol

### Stream Won't Start
- Verify destination is configured correctly
- Check stream key is valid and not expired
- Confirm network has sufficient upload bandwidth
- Review FFmpeg logs for errors
- Try "Kill All Streams" if processes are stuck

### Timeline Not Playing
- Ensure timeline has been saved
- Check that timeline has video content
- Verify cameras are online
- Check for overlapping cues
- Review timeline duration settings

### High CPU Usage
- Reduce number of simultaneous streams
- Lower output resolution if possible
- Check for stuck FFmpeg processes
- Monitor system resources in Dashboard
- Consider hardware encoding if available

### PTZ Preset Not Working
- Verify camera supports PTZ over ONVIF
- Check camera is PTZ type, not stationary
- Confirm preset was saved correctly
- Test "Go To" button from Preset page
- Review camera PTZ credentials

---

## Support and Resources

For additional help:
- Check project README.md for setup instructions
- Review technical documentation in /docs folder
- Check system logs for detailed error messages
- Use Emergency Controls to reset stuck streams
- Refer to PRD.md and SAD.md for system architecture details

---

## Appendix

### Keyboard Shortcuts

Timeline Editor:
- `Ctrl + +` - Zoom in
- `Ctrl + -` - Zoom out
- `Space` - Play/Pause (when implemented)

### Default Ports

- Web Interface: 3000
- RTSP: 554
- RTMP: 1935

### File Locations

- Database: `vistterstream.db`
- Uploaded Assets: `backend/uploads/assets/`
- Configuration: `.env` file

---

*This user guide is for VistterStream version 1.0.0-beta. Features and interface may change in future releases.*

