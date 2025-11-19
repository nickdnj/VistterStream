# VistterStream

**A standalone, AI-built live streaming appliance for multi-camera productions.**

VistterStream is a complete live streaming system designed for creators who want professional multi-camera broadcasts without the complexity. Built for weather station operators, destination marketers, community organizations, and anyone who wants to showcase their location 24/7. It manages IP cameras, executes automated timelines with PTZ presets, applies overlays, and streams to YouTube Live, Facebook Live, Twitch, or custom RTMP destinations.

## About This Project – AI-Powered Development

This project represents a unique collaboration between a veteran software architect and multiple AI systems working in concert:

**Nick DeMarco** — 61, retired after four decades of enterprise software architecture in the EDA world — paired with ChatGPT, Cursor, Claude, Codex CLI, and Gemini to build a production-ready streaming platform entirely through conversation.

### The Collaborative Build Process

We didn't just write code. We built a complete software project the way it should be done:

1. **Specification Phase** - ChatGPT helped create comprehensive living documents: PRD, Software Architecture, UX Design
2. **Iterative Development** - Cursor and Codex CLI handled implementation, Claude provided narrative clarity, Gemini offered lateral thinking
3. **Continuous Refinement** - Specs evolved with the build, just like a real software shop
4. **Multi-Model Approach** - Each AI brought unique strengths: ChatGPT for architecture decisions, Cursor for code execution, Claude for documentation, Gemini for creative solutions

The result: A fully functional, professionally architected streaming platform that proves AI-assisted development can produce serious, production-ready software.

## 📖 Quick Start

**New to VistterStream?** Get streaming in 5 minutes:

- **🚀 [Quick Start Guide](docs/QUICK_START_GUIDE.md)** - Install and configure your first stream
- **📚 [Complete User Guide](docs/USER_GUIDE.md)** - Comprehensive feature reference with screenshots
- **📋 [Documentation Index](docs/README.md)** - All documentation organized by topic

## 🖥️ Reference Hardware

VistterStream was built and tested on this production hardware setup:

### Compute Platform

**Raspberry Pi 5 (8GB RAM)**
- **Model**: Raspberry Pi 5
- **RAM**: 8GB
- **Storage**: MicroSD card (32GB+ recommended) or NVMe SSD via PCIe
- **Power**: 27W USB-C power supply (5.1V/5A)
- **Networking**: Gigabit Ethernet (recommended for stable streaming)
- **Why**: Powerful ARM64 processor with hardware video encoding, runs Docker natively, low power consumption (~15W), perfect for 24/7 operation

**Performance**: The Raspberry Pi 5's VideoCore VII GPU provides hardware-accelerated H.264 encoding, enabling smooth 1080p60 streaming with multiple overlays while maintaining low CPU usage.

### Cameras

**Sunba PTZ Camera**
- **Type**: IP PTZ Camera with ONVIF support
- **Connection**: RTSP stream via network
- **PTZ Protocol**: ONVIF (port 8899)
- **Features**: 
  - Pan/Tilt/Zoom control
  - Preset positions (unlimited presets supported)
  - 1080p video output
  - Excellent for automated multi-angle shows
- **Use Case**: Primary camera for creating professional multi-angle content from a single camera using VistterStream's PTZ preset system

**Reolink Fixed Camera** (Optional)
- **Type**: Stationary IP camera
- **Connection**: RTSP stream
- **Features**: 
  - High-quality 1080p video
  - Wide angle lens
  - Reliable RTSP stream
- **Use Case**: Wide scenic shots, secondary angles in multi-camera timelines

### Weather Station

**WeatherFlow Tempest Weather Station**
- **Type**: Wireless all-in-one weather station
- **Connection**: WiFi to WeatherFlow cloud
- **API**: RESTful API for weather data
- **Integration**: VistterStream pulls real-time weather data via API overlays
- **Data Available**: 
  - Temperature, humidity, pressure
  - Wind speed and direction
  - Rain rate and accumulation
  - UV index, solar radiation
  - Lightning detection
- **Use Case**: Dynamic weather overlays on scenic streams, perfect for weather storytelling

### Network Requirements

- **Internet**: 10+ Mbps upload for 1080p streaming (20+ Mbps recommended for multi-streaming)
- **Local Network**: Gigabit Ethernet switch recommended
- **Router**: Port forwarding not required (outbound connections only)
- **Cameras**: All cameras and Pi on same local network

### Optional Accessories

- **PoE Switch**: Power cameras via Ethernet (if cameras support PoE)
- **UPS**: Uninterruptible power supply for 24/7 reliability
- **Cooling**: Raspberry Pi 5 case with active cooling for sustained performance
- **Storage**: External SSD for local recording (optional)

### Total System Power

- Raspberry Pi 5: ~15W
- Sunba PTZ Camera: ~12W
- Reolink Camera: ~6W
- Network Switch: ~10W
- **Total**: ~43W (less than a standard light bulb!)

Perfect for 24/7 operation with minimal power costs.

## What Is VistterStream?

VistterStream is a **standalone streaming appliance** that runs on Raspberry Pi, Intel NUC, or Mac hardware in a Docker container. It provides a beautiful web interface for managing cameras, creating automated shows, and streaming to multiple platforms simultaneously.

### Perfect For

- **Weather Station Operators** - Showcase your Tempest station with live scenic views and weather overlays
- **Destination Marketers** - 24/7 scenic streams of harbors, main streets, and attractions
- **Community Organizations** - Broadcast local events and scenic views to build community pride
- **Small Businesses** - Restaurants, shops, marinas showing live ambiance
- **Property Managers** - Real estate and venue showcase streams

## Core Features

### 🎥 Camera Management
- **RTSP/RTMP Support** - Works with Reolink, Sunba, Amcrest, and most IP cameras
- **PTZ Camera Control** - Full pan/tilt/zoom control via ONVIF
- **Preset System** - Save and recall camera positions for automated shows
- **Health Monitoring** - Real-time connection status and automatic recovery
- **Live Snapshots** - Visual confirmation of camera views

### 🎬 Timeline Production
- **Multi-Camera Timelines** - Switch between cameras on a schedule
- **PTZ Automation** - Create professional multi-angle shows from a single PTZ camera
- **Visual Timeline Editor** - Drag, drop, and resize cues with precision
- **Looping Playback** - Run 24/7 unattended with automatic looping
- **Multi-Destination** - Stream timelines to multiple platforms simultaneously

### 🎨 Overlay System
- **Static Image Overlays** - Upload PNG/JPEG logos and graphics
- **Dynamic API Overlays** - Auto-refreshing content from APIs (weather, tides, scores)
- **Positioning Controls** - Precise placement with horizontal/vertical coordinates
- **Scaling System** - Proportional or custom dimensions for overlays
- **Opacity Control** - Transparent overlays blend perfectly
- **Multiple Overlays** - Stack multiple overlays in a single stream

### 📅 Automated Scheduling
- **Day/Time Windows** - Schedule timelines for specific days and times
- **Background Execution** - Scheduler runs automatically, checking every 30 seconds
- **Multiple Schedules** - Different content for different times of day
- **24/7 Operation** - Perfect for unattended streaming

### 📡 Streaming Destinations
- **YouTube Live** - Full broadcast lifecycle management with OAuth
- **Facebook Live** - Stream to Facebook pages and profiles
- **Twitch** - Gaming and creative content streaming
- **Custom RTMP** - Any RTMP server or CDN
- **Reusable Configs** - Configure once, use across all streams and timelines
- **Multi-Streaming** - Broadcast to 3+ platforms simultaneously

### 🔧 System Features
- **Hardware Acceleration** - Automatic detection and use of GPU encoders
- **Quality Profiles** - 1080p60, 720p, 480p with custom bitrates
- **Health Watchdog** - Automatic stream recovery from failures
- **YouTube API Integration** - Broadcast status monitoring and auto-reset
- **Beautiful UI** - Dark theme, responsive design, professional interface
- **Docker Deployment** - Single container, multi-architecture (ARM64/x86_64)
- **Local-First** - All configuration stored locally, no cloud dependencies

## Architecture

VistterStream uses a modern, modular architecture:

```
┌─────────────────────────────────────────────────┐
│           React Frontend (Tailwind CSS)         │
│  Cameras • Timelines • Destinations • Settings  │
└────────────────┬────────────────────────────────┘
                 │ REST API + WebSocket
┌────────────────┴────────────────────────────────┐
│          FastAPI Backend (Python)               │
│  Camera Service • Timeline Executor • FFmpeg    │
│  PTZ Control • Watchdog • Asset Management      │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────┴────────────────────────────────┐
│     SQLite Database • File Storage • Logs       │
└─────────────────────────────────────────────────┘
```

### Technical Stack

- **Frontend**: React 18 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python) + SQLAlchemy
- **Database**: SQLite with comprehensive schema
- **Streaming**: FFmpeg with hardware acceleration
- **PTZ Control**: ONVIF (onvif-zeep)
- **Container**: Docker with multi-arch builds
- **Authentication**: JWT tokens with bcrypt

## What Makes VistterStream Special

### Single PTZ Camera = Multi-Camera Show

One of VistterStream's breakthrough features: Create professional multi-angle content from a **single PTZ camera**:

1. Save multiple presets: "Wide Shot", "Close Up", "Medium"
2. Create a timeline with cues referencing different presets
3. Camera automatically repositions between angles
4. Result: Professional multi-camera production without buying multiple cameras!

### Destination-First Architecture

Configure YouTube, Facebook, Twitch once. Reuse everywhere. Stream keys, OAuth credentials, and platform settings are centralized and referenced by all streams and timelines.

### Smart Broadcast Management

YouTube Live integration handles the broadcast lifecycle automatically:
- OAuth authentication with Google
- Automatic broadcast status checks
- Auto-reset when broadcasts finish
- Frame probing for stream health
- Daily broadcast resets (optional)

### Unattended Operation

Built for 24/7 streaming:
- Health watchdog monitors all streams
- Automatic recovery from failures
- Scheduled content rotation
- Camera health monitoring
- Emergency "Kill All" button

## Project Structure

```
VistterStream/
├── docs/
│   ├── specifications/           # PRD, SAD, UXD, technical specs
│   ├── working_documents/        # Debug notes, fixes, deployment docs
│   ├── status_notes/             # Development history
│   ├── screenshots/              # UI reference images
│   ├── QUICK_START_GUIDE.md      # Get started in 5 minutes
│   ├── USER_GUIDE.md             # Complete feature reference
│   └── README.md                 # Documentation index
├── backend/
│   ├── routers/                  # API endpoints
│   ├── services/                 # Business logic
│   ├── models/                   # Database models
│   └── migrations/               # Schema migrations
├── frontend/
│   └── src/
│       ├── components/           # React components
│       └── pages/                # Main application pages
├── docker/                       # Docker Compose configurations
├── scripts/                      # Deployment and utility scripts
├── tests/                        # Test suite
└── README.md                     # This file
```

## Installation

### Quick Install (Docker)

```bash
# Clone the repository
git clone https://github.com/yourusername/VistterStream.git
cd VistterStream

# Copy and configure environment
cp env.sample .env
# Edit .env with your settings

# Start the system
docker-compose up -d

# Access the UI
open http://localhost:3000
```

### Raspberry Pi Installation

See **[Raspberry Pi Setup Guide](docs/RaspberryPi-Docker.md)** for detailed instructions.

### Manual Installation

See **[Docker Testing Guide](docs/Docker-Testing-Complete.md)** for advanced deployment options.

## Documentation

### 📖 User Documentation
- **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** ⭐ START HERE!
- **[Complete User Guide](docs/USER_GUIDE.md)** - All features explained
- **[Documentation Index](docs/README.md)** - Find any documentation

### 🔧 Setup & Deployment
- **[Raspberry Pi Setup](docs/RaspberryPi-Docker.md)** - Deploy on Raspberry Pi
- **[Docker Testing](docs/Docker-Testing-Complete.md)** - Docker deployment guide
- **[YouTube OAuth Setup](docs/working_documents/oauth/YOUTUBE_OAUTH_SETUP.md)** - Configure YouTube API

### 📋 Technical Specifications
- **[Product Requirements (PRD)](docs/specifications/PRD.md)** - Original product vision
- **[Software Architecture (SAD)](docs/specifications/SAD.md)** - System design
- **[UX Design (UXD)](docs/specifications/UXD.md)** - User experience specification
- **[Streaming Pipeline Spec](docs/specifications/StreamingPipeline-TechnicalSpec.md)** - Detailed implementation
- **[Scheduler Design](docs/specifications/Scheduler.md)** - Scheduling system

### 🔮 Future Vision
- **[VistterStudio Integration](docs/specifications/VistterStudioIntegration.md)** - Planned cloud control platform
- **[Preview System Spec](docs/specifications/PreviewSystem-Specification.md)** - Advanced preview features

## Current Status

**✅ Production-Ready** (November 2025)

### What's Working
- ✅ Complete camera management (RTSP/RTMP/ONVIF)
- ✅ PTZ preset system with ONVIF control
- ✅ Multi-camera timeline system
- ✅ Asset management and overlay system
- ✅ Multiple streaming destinations
- ✅ Automated scheduling
- ✅ YouTube Live integration with OAuth
- ✅ Stream health monitoring and auto-recovery
- ✅ Beautiful, responsive web UI
- ✅ Docker deployment (ARM64 + x86_64)

### What's Next
- ⏳ VistterStudio cloud control platform (future)
- ⏳ Advanced analytics and metrics
- ⏳ Mobile app (currently responsive web)
- ⏳ AI-powered scene detection
- ⏳ Multi-language support

## Vision vs Reality

### Original Vision (from PRD)
VistterStream was originally conceived as part of a two-product platform:
- **VistterStream** - On-premises appliance (this project)
- **VistterStudio** - Cloud-hosted timeline editor and control surface

### What Was Actually Built
**VistterStream is a complete, standalone streaming appliance.** All the core functionality works perfectly without any cloud dependencies:

- ✅ Local web UI for all configuration
- ✅ Local timeline editor (no cloud required)
- ✅ Local asset management
- ✅ Direct streaming to platforms
- ✅ All automation runs locally

**VistterStudio** remains a future enhancement for fleet management and advanced remote control, but is **not required** for full functionality.

## Test Cameras

The project includes configuration for local test cameras:

### Reolink (Fixed position)
- **Stream**: `rtsp://Wharfside:Wharfside2025!!@192.168.86.250:554/Preview_01_main`
- **Snapshot**: `http://Wharfside:Wharfside2025!!@192.168.86.250:80/cgi-bin/api.cgi?cmd=onvifSnapPic&channel=0`

### Sunba (PTZ with ONVIF)
- **Stream**: `rtsp://192.168.86.23:554/user=admin_password=sOKDKxsV_channel=0_stream=0&onvif=0.sdp?real_stream`
- **ONVIF Port**: 8899 (non-standard)

## Contributing

This project was built through AI-assisted development. Contributions welcome! Please:

1. Check existing issues and documentation
2. Follow the established code style
3. Include tests for new features
4. Update documentation as needed

## License

[License information to be added]

## Acknowledgments

Built with the collaborative power of:
- **ChatGPT** - Architecture and specifications
- **Cursor** - Code implementation
- **Claude** - Documentation and narrative
- **Codex CLI** - Raspberry Pi deployment
- **Gemini** - Creative problem solving
- **Nick DeMarco** - Vision, orchestration, and 40 years of software architecture experience

This project proves that AI-assisted development, when done thoughtfully with proper specifications and iterative refinement, can produce professional, production-ready software.

---

**Ready to start streaming?** → **[Quick Start Guide](docs/QUICK_START_GUIDE.md)** 🚀
