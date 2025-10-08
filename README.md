# VistterStream

A local streaming appliance that connects on-premises cameras to VistterStudio cloud timelines. VistterStream discovers, manages, and processes local cameras, including PTZ (pan-tilt-zoom) presets, and streams the final output to destinations such as YouTube Live, Facebook Live, or Twitch.

## Overview

VistterStream is designed to run on hardware like the Raspberry Pi in a Docker container, providing a web interface for camera management and live streaming capabilities. It ingests RTSP/RTMP feeds, applies overlays and instructions received from VistterStudio, and streams the final output to various platforms.

## Key Features

- **Camera Management**: Support for RTSP/RTMP cameras including Reolink (stationary) and Amcrest/Samba (PTZ)
- **PTZ Presets**: Define and execute preset positions for PTZ cameras
- **Live Scheduling**: Background scheduler starts/stops timelines on day/time windows
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

#### **Asset Management & Overlay System** ⭐ **NEW!** (Oct 3, 2025)
- **🎨 Comprehensive Asset Management**: Full CRUD for overlay assets with beautiful UI
  - **API Image Assets**: Dynamic content from API endpoints (e.g., weather/tides data)
  - **Static Image Assets**: Upload PNG, JPEG, GIF, WebP with drag-and-drop or file picker
  - **Video Assets**: Upload MP4, MOV, WebM for video overlays
  - **Graphic Assets**: Custom graphic overlays with positioning controls
- **📤 File Upload System**: Drag-and-drop or click to upload with validation
  - File type validation (images, videos)
  - Size limit enforcement (50MB max)
  - Preview generation for all asset types
  - Unique filename generation (UUID-based)
- **📐 Asset Scaling Controls**: Precise dimension control for overlays
  - Width/Height input fields (pixels)
  - Proportional scaling (set one dimension, other auto-adjusts)
  - "Auto" for original size preservation
  - Real-time size display in asset cards
- **🎯 Positioning System**: Coordinate-based overlay placement
  - Horizontal (0=Left, 1=Right) and Vertical (0=Top, 1=Bottom) controls
  - Position preview labels (e.g., "Bottom Left", "Top Right", "Center")
  - Opacity control (0-100%)
  - Layer management for multiple overlays
- **🔄 API Asset Refresh**: Automatic content updates for dynamic overlays
  - Configurable refresh intervals (1-3600 seconds)
  - Live weather, tides, scores, news integration
  - Background refresh without stream interruption
- **📺 Program Monitor Integration**: Real-time preview of composed output
  - Actual camera snapshots (not simulations)
  - Overlays composited in preview
  - Position and size verification before going live
  - Multiple overlay support in preview
- **🎬 FFmpeg Integration**: Professional overlay compositing in live streams
  - Hardware-accelerated overlay rendering
  - Dynamic overlay updates during stream
  - Multiple simultaneous overlays supported
  - Scaling, positioning, opacity all applied in real-time

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

## 🎯 Current Focus: Production-Ready Streaming!

### **Just Completed:** ✅ **(October 3, 2025)**
- **🎨 Complete Asset Management System**: CRUD operations, file uploads, previews, multiple asset types
- **📐 Asset Scaling System**: Control overlay dimensions with width/height controls, proportional scaling
- **🎥 Multiple Overlay Support**: Static images + API overlays working together in streams
- **📺 Program Monitor**: Real-time preview with actual camera snapshots and overlay composition
- **🎬 Multi-Track Timeline Editor**: Drag, drop, resize cues with Premiere Pro-level UX
- **🔄 Stream Status Sync**: Frontend polling keeps Start/Stop button accurate
- **🐛 Path Resolution Fixes**: URL paths correctly converted to filesystem paths for uploads
- **🔐 Robust Stop Functionality**: Handles database errors gracefully during cancellation

### **Ready for Production:**
- **🚀 YouTube Live Streaming**: ✅ Working with camera switching and overlays
- **📡 RTMP Relay Architecture**: ✅ Seamless switching infrastructure deployed
- **🎯 PTZ Preset System**: ✅ Automated multi-angle shows from single camera
- **💾 Complete Database**: ✅ Assets, timelines, tracks, cues, executions, presets
- **🎨 Beautiful UI**: ✅ Dark theme, responsive, professional-grade

### **Next Up:**
- **🎯 End-to-End Testing**: Full timeline → YouTube test with seamless switching
- **☁️ VistterStudio Integration**: Import/export timelines, cloud control
- **📊 Advanced Metrics**: Real-time bitrate graphs, FPS monitoring, dropped frames
- **🔄 Multi-Destination Testing**: Simultaneous streaming to 3+ platforms (architecture ready)

## Documentation

### **Core Specifications**
- **[Product Requirements Document (PRD)](docs/PRD.md)** - Product vision, use cases, requirements
- **[Software Architecture Document (SAD)](docs/SAD.md)** - System architecture and component design
- **[User Experience Design (UXD)](docs/UXD.md)** - UI/UX specifications and workflows
- **[Streaming Pipeline Technical Spec](docs/StreamingPipeline-TechnicalSpec.md)** ⭐ **PRIMARY SPEC** - Detailed streaming & timeline implementation
- **[VistterStudio Integration](docs/VistterStudioIntegration.md)** - Future cloud control integration

### **Preview System** 🆕 ⭐ **(October 2025)**
- **[Preview System Specification](docs/PreviewSystem-Specification.md)** - Complete PRD+SAD for local preview & go-live workflow (18,000 words)
- **[Preview Quick Start Guide](docs/PreviewSystem-QuickStart.md)** - 30-minute developer setup guide
- **[Preview Implementation TODO](docs/PreviewSystem-TODO.md)** - Detailed task breakdown with 57 actionable items
- **[Preview Executive Summary](docs/PreviewSystem-Summary.md)** - High-level overview for stakeholders

Note: Local preview window has been removed in favor of using YouTube Live Studio directly from the Timeline UI.

### **Scheduler** (October 2025)
- See `docs/Scheduler.md` for design and API
- UI: left nav → Scheduler; create schedules with days/time windows and timelines
- Background loop runs every 30s to enforce active schedules

### **Development Resources**
- **[TODO List](TODO.md)** - Current development roadmap and task tracking
- **[Local Test Cameras](docs/Local%20Test%20Cameras.md)** - Test camera configurations
- **[Changelog](CHANGELOG.md)** - Version history and updates

## License

[License information to be added]

## Contributing

[Contributing guidelines to be added]
