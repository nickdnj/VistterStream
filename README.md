# VistterStream

A local streaming appliance that connects on-premises cameras to VistterStudio cloud timelines. VistterStream discovers, manages, and processes local cameras, including PTZ (pan-tilt-zoom) presets, and streams the final output to destinations such as YouTube Live, Facebook Live, or Twitch.

## Overview

VistterStream is designed to run on hardware like the Raspberry Pi in a Docker container, providing a web interface for camera management and live streaming capabilities. It ingests RTSP/RTMP feeds, applies overlays and instructions received from VistterStudio, and streams the final output to various platforms.

## Key Features

- **Camera Management**: Support for RTSP/RTMP cameras including Reolink (stationary) and Amcrest/Samba (PTZ)
- **PTZ Presets**: Define and execute preset positions for PTZ cameras
- **Live Previews**: Embedded video preview for each camera feed
- **Health Monitoring**: Real-time camera connection status and system metrics
- **Web Interface**: Local-only web UI for configuration and monitoring
- **FFmpeg Processing**: Professional video processing with overlays and transcoding
- **Multi-Output Streaming**: Support for multiple streaming destinations simultaneously

## Target Users

- **Small businesses & venues**: Shops, restaurants, marinas, and tourist attractions
- **Community organizations**: Visitor bureaus or chambers of commerce
- **Property managers & real estate**: Broadcasting properties or scenic angles
- **Event operators**: Local operators who need reliable camera-to-stream appliances

## Architecture

- **Single-container modular architecture** with Docker
- **Web UI**: React frontend with Tailwind CSS
- **API Backend**: FastAPI (Python) for REST APIs
- **Controller**: Manages camera configs, PTZ, and state
- **Stream Engine**: FFmpeg wrapper for video processing
- **Database**: SQLite for persistent local storage

## Technical Stack

- **Frontend**: React + Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **Streaming**: FFmpeg (multi-arch build)
- **Containerization**: Docker with multi-arch support (x86_64 & ARM64)
- **Authentication**: Local username/password with bcrypt

## Project Structure

```
VistterStream/
├── docs/                    # Documentation
│   ├── PRD.md              # Product Requirements Document
│   ├── SAD.md              # Software Architecture Document
│   ├── UXD.md              # User Experience Design Document
│   └── Local Test Cameras.md # Test camera configurations
├── README.md               # This file
└── [additional directories to be created]
```

## Test Cameras

The project includes configuration for local test cameras:

### Reolink (Fixed position camera)
- **Main Stream**: `rtsp://Wharfside:Wharfside2025!!@192.168.86.250:554/Preview_01_main`
- **Snapshot**: `http://Wharfside:Wharfside2025!!@192.168.86.250:80/cgi-bin/api.cgi?cmd=onvifSnapPic&channel=0`

### Sunba (PTZ camera with ONVIF support)
- **Main Stream**: `rtsp://192.168.86.23:554/user=admin_password=sOKDKxsV_channel=0_stream=0&onvif=0.sdp?real_stream`
- **Snapshot**: `http://192.168.86.23/webcapture.jpg?command=snap&channel=0&user=admin&password=sOKDKxsV`

## Development Status

**Milestone 1 COMPLETED** ✅ - Foundation & Local Camera Integration  
**Milestone 2 MOSTLY COMPLETE** ✅ - Streaming Engine & Destination Architecture  
**Milestone 3 IN PROGRESS** 🚧 - Multi-Track Timeline System

### ✅ **What's Working:**

#### **Core Infrastructure**
- **🚀 FastAPI Backend**: Complete REST API with authentication, camera management, and database models
- **🎨 React Frontend**: Beautiful dark-themed UI with Tailwind CSS, responsive design
- **💾 Database**: SQLite with comprehensive schema for cameras, destinations, streams, timelines
- **🔐 Authentication**: Secure login system with JWT tokens

#### **Camera Management**
- **📷 Camera Integration**: Full support for Reolink and Sunba cameras with RTSP/ONVIF
- **⚡ Live Monitoring**: Real-time camera status, snapshots, and health checks
- **📹 Live Stream Viewer**: Auto-refreshing camera preview with RTSP URL display
- **🔄 Background Health Monitor**: Keeps cameras persistently online
- **🎯 PTZ Preset System** ⭐ **NEW!**: Save, recall, and automate camera positions
  - ONVIF control for Sunba PTZ cameras (port 8899)
  - Capture current position as named preset
  - Test presets with "Go To" button
  - Use presets in streams and timelines
  - Pan/tilt/zoom position tracking

#### **Streaming Destinations** ⭐ **NEW!**
- **📡 Destination-First Architecture**: Configure YouTube, Facebook, Twitch, Custom RTMP once, use everywhere
- **🎯 Reusable Configs**: Stream keys stored centrally, referenced by streams and timelines
- **📊 Usage Tracking**: Automatic `last_used` timestamp tracking per destination
- **🎨 Platform Presets**: Built-in RTMP URL templates for major platforms

#### **Stream Management**
- **▶️ Single-Camera Streams**: Direct camera-to-destination streaming with full control
- **🎯 PTZ Preset Streams** ⭐ **NEW!**: Streams automatically move PTZ cameras to preset positions
  - Select camera + preset in stream configuration
  - Camera moves to preset before stream starts
  - 3-second settling time for mechanical movement
  - Edit streams to change presets on-the-fly
- **🎛️ Encoding Profiles**: Resolution, bitrate, framerate configuration (1080p/720p/480p)
- **🔥 Hardware Acceleration**: Automatic detection and usage of hardware encoders
- **⏯️ Start/Stop Control**: Reliable stream control with orphaned process cleanup
- **🚨 Emergency Stop**: "Kill All Streams" button to terminate rogue processes

#### **Composite Streams & Timelines** ⭐ **NEW!**
- **🎬 Multi-Camera Composite Streams**: Switch between cameras on a schedule (e.g., 1 min each, looping)
- **📅 Timeline Editor**: Visual interface to create timelines with camera cues
- **🎯 PTZ Preset Timelines** ⭐ **BREAKTHROUGH!**: Automated multi-angle shows from single PTZ camera!
  - Select camera + preset for each timeline cue
  - Camera automatically repositions between presets during playback
  - Create professional multi-angle shows: "Wide Shot → Close Up → Medium Shot → Loop"
  - Visual preset selector in timeline editor
  - Same camera, multiple presets = infinite creative possibilities!
- **🎯 Multi-Track System**: Video track with sequential cue execution
- **▶️ Timeline Execution**: Start/stop timeline playback with live camera switching
- **🔄 Looping Support**: Infinite loop mode for continuous operation
- **📡 Multi-Destination**: Stream timelines to multiple platforms simultaneously
- **🔄 Auto-Restart**: Smart start button automatically restarts running timelines

### **Technical Architecture:**
- **Backend**: FastAPI with SQLAlchemy ORM, Pydantic schemas, JWT authentication
- **Frontend**: React 18 with TypeScript, Tailwind CSS, React Router, Axios
- **Database**: SQLite with models for cameras, destinations, streams, timelines, tracks, cues, **presets**
- **PTZ Control**: ONVIF integration for pan/tilt/zoom camera automation (onvif-zeep library)
- **Streaming**: FFmpeg process manager with hardware acceleration, auto-restart, metrics
- **Real-time**: Live status monitoring, health checks, auto-refreshing UI
- **API Design**: RESTful endpoints with enriched responses, proper error handling
- **Security**: Bcrypt password hashing, JWT tokens, encrypted credentials
- **UI/UX**: Professional dark theme, responsive design, beautiful animations, conditional preset UI

## 🎯 Current Focus: Overlay System & Advanced Features

### **Just Completed:** ✅
- **🎯 Complete PTZ Preset System**: ONVIF control, preset management, timeline integration
- **📝 Timeline Save Fix**: Tracks and cues now properly persist to database
- **🔄 Auto-Restart Timelines**: Smart start button handles running timelines gracefully

### **Next Up:**
- **🎥 Overlay System**: Text overlays, image overlays, lower thirds, fade transitions
- **📆 Timeline Scheduling**: Future execution, recurring schedules
- **☁️ VistterStudio Integration**: Import/export timelines, cloud control
- **📊 Advanced Metrics**: Real-time bitrate, FPS, dropped frames
- **🔄 Multi-Destination Streaming**: Simultaneous streaming to 3+ platforms (architecture ready, needs testing)

## Documentation

### **Core Specifications**
- **[Product Requirements Document (PRD)](docs/PRD.md)** - Product vision, use cases, requirements
- **[Software Architecture Document (SAD)](docs/SAD.md)** - System architecture and component design
- **[User Experience Design (UXD)](docs/UXD.md)** - UI/UX specifications and workflows
- **[Streaming Pipeline Technical Spec](docs/StreamingPipeline-TechnicalSpec.md)** ⭐ **PRIMARY SPEC** - Detailed streaming & timeline implementation
- **[VistterStudio Integration](docs/VistterStudioIntegration.md)** - Future cloud control integration

### **Development Resources**
- **[TODO List](TODO.md)** - Current development roadmap and task tracking
- **[Local Test Cameras](docs/Local%20Test%20Cameras.md)** - Test camera configurations
- **[Changelog](CHANGELOG.md)** - Version history and updates

## License

[License information to be added]

## Contributing

[Contributing guidelines to be added]
