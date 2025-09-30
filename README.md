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

### What's Working:
- **🚀 FastAPI Backend**: Complete REST API with authentication, camera management, and database models
- **🎨 React Frontend**: Beautiful dark-themed UI with Tailwind CSS, responsive design
- **📷 Camera Integration**: Full support for Reolink and Sunba cameras with RTSP testing
- **⚡ Real-time Monitoring**: Live camera status, system metrics, and health monitoring
- **💾 Database**: SQLite with complete schema for cameras, presets, streams, and users
- **🔐 Authentication**: Secure login system (minor frontend flow issue pending)

### Screenshots:
- Beautiful login interface with dark theme
- Professional dashboard with system metrics
- Camera management with real-time status
- Responsive design that works on all devices

### Current Features:
- Camera discovery and configuration
- RTSP connection testing
- Snapshot capture and preview
- Real-time status monitoring
- PTZ preset management (ready)
- User authentication system

### Technical Architecture:
- **Backend**: FastAPI with SQLAlchemy ORM, Pydantic schemas, JWT authentication
- **Frontend**: React 18 with TypeScript, Tailwind CSS, React Router, Axios
- **Database**: SQLite with comprehensive schema for cameras, users, presets, streams
- **Camera Support**: OpenCV for RTSP testing, HTTP requests for snapshots
- **Real-time Features**: Live status monitoring, health checks, system metrics
- **API Design**: RESTful endpoints with proper error handling and validation
- **Security**: Bcrypt password hashing, JWT tokens, CORS configuration
- **UI/UX**: Professional dark theme, responsive design, beautiful animations

## 🎯 Current Focus: Streaming Pipeline + Timeline Orchestration

### **Milestone 2: Streaming Engine** (In Progress)
- FFmpeg process management with hardware acceleration (Pi 5 + Mac)
- Multi-destination streaming (YouTube, Facebook, Twitch, custom RTMP)
- Automatic camera failover and test pattern fallback
- Real-time overlay compositing (text, images, lower thirds)
- Stream health monitoring and auto-recovery

### **Milestone 3: Multi-Track Timeline System** (Next)
- Timeline orchestrator with video + overlay tracks
- Sequential cue execution with precise timing
- Timeline builder UI with drag-drop interface
- Segment import/export for reusable content
- "GO LIVE" button with pre-flight checks

**See [StreamingPipeline-TechnicalSpec.md](docs/StreamingPipeline-TechnicalSpec.md) for complete technical details.**

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
