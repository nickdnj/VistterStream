# VistterStream Delivery Backlog - FOCUSED & REFINED

## 🎯 **CURRENT MISSION: Streaming Pipeline + Timeline Orchestration**
*Build the core appliance capabilities standalone, THEN integrate VistterStudio control*

---

## 📚 **Key Documentation References**

### **Design & Architecture**
- **[PRD.md](docs/PRD.md)** - Product Requirements & Use Cases
- **[SAD.md](docs/SAD.md)** - Software Architecture Document
- **[UXD.md](docs/UXD.md)** - User Experience Design
- **[StreamingPipeline-TechnicalSpec.md](docs/StreamingPipeline-TechnicalSpec.md)** ⭐ **PRIMARY SPEC** - Detailed streaming & timeline architecture
- **[VistterStudioIntegration.md](docs/VistterStudioIntegration.md)** - Future integration contracts

### **Implementation Notes**
- **Multi-Track Timeline System** - See StreamingPipeline-TechnicalSpec.md §"Multi-Track Timeline System"
- **Hardware Acceleration** - See StreamingPipeline-TechnicalSpec.md §"Hardware Acceleration" (Pi 5 + Mac)
- **Failure Recovery** - See StreamingPipeline-TechnicalSpec.md §"Failure Recovery System"
- **Database Schema** - See StreamingPipeline-TechnicalSpec.md §"Database Schema Extensions"

---

## 🚀 **PHASE 1: STREAMING PIPELINE** (Weeks 1-2)
*Reference: [StreamingPipeline-TechnicalSpec.md](docs/StreamingPipeline-TechnicalSpec.md)*

### **1.1 FFmpeg Streaming Engine** ⚡
*See spec §"Streaming Pipeline Architecture"*

- [ ] **FFmpeg Process Manager**
  - Spawn/manage FFmpeg processes with proper lifecycle control
  - Process monitoring with health checks and auto-restart
  - Graceful shutdown and resource cleanup
  - Output parsing for errors, warnings, and stats (bitrate, fps, dropped frames)

- [ ] **Multi-Destination Streaming**
  - Simultaneous streaming to 3+ destinations (YouTube, Facebook, Twitch, custom RTMP)
  - Per-destination encoding profiles (bitrate, resolution, codec, keyframe interval)
  - Destination-specific retry logic and failure isolation
  - Stream key management and validation

- [ ] **Input Source Management**
  - RTSP camera feed ingestion with failover
  - Fallback slate/media when camera fails
  - Input switching (for timeline-driven camera changes)
  - Audio handling (passthrough, silence, or mixed)

- [ ] **Hardware Acceleration** 
  - Detect and use hardware encoders (Pi 5: `h264_v4l2m2m`, Mac: `h264_videotoolbox`)
  - Fallback to software encoding when HW unavailable
  - Performance benchmarking per hardware profile
  - *See spec §"Hardware Acceleration" for Pi 5 & Mac specific implementations*

- [ ] **Stream Health & Telemetry**
  - Real-time metrics: bitrate, FPS, dropped frames, buffer status
  - Stream state tracking (starting, running, degraded, failed)
  - Alert generation for critical failures
  - Performance logging for troubleshooting

### **1.2 Overlay System** 🎨
*See spec §"Overlay System (MVP)" for simple overlay types*

- [ ] **FFmpeg Filter Graph Integration**
  - Text overlays (dynamic, template-based)
  - Image/logo overlays (PNG with alpha)
  - Position, scale, opacity control
  - Fade in/out transitions
  - *Reference: Filter graph template in spec*

- [ ] **Dynamic Overlay Updates**
  - Live text updates without restarting stream
  - Overlay scene switching (lower thirds, full screen graphics)
  - Asset preloading and caching
  - Timing precision (frame-accurate cues)

### **1.3 Stream Management API** 📡
- [ ] **Enhanced Backend Endpoints**
  - Start/stop/restart streams with profiles
  - Get real-time stream status and metrics
  - Update stream destinations on-the-fly
  - Stream recording control (optional DVR)

- [ ] **Frontend Stream Dashboard**
  - Live stream status indicators with metrics graphs
  - Multi-stream preview (snapshots or live thumbnails)
  - Quick actions (start/stop, change destination)
  - Error display with troubleshooting hints

---

## 🎬 **PHASE 2: TIMELINE & SEGMENT ENGINE** (Weeks 3-4)
*Reference: [StreamingPipeline-TechnicalSpec.md](docs/StreamingPipeline-TechnicalSpec.md)*

### **2.1 Timeline Data Model** 📋
*See spec §"Multi-Track Timeline System" for complete schema*

- [ ] **Timeline Schema Design**
  - Multi-track structure: 1 video track + multiple overlay tracks
  - Action/Cue definitions (camera preset, overlay change, stream control)
  - Timing model: Sequential per track, parallel across tracks
  - Validation rules and schema versioning
  - *Reference: JSON schema example in spec*

- [ ] **Database Extensions**
  - Timelines table (id, name, created, modified, status)
  - Timeline tracks table (track_type, layer, timeline_id)
  - Timeline cues table (track_id, start_time, duration, action_type, params)
  - Assets table (overlays, test patterns, transitions)
  - Execution history and audit logs
  - *Reference: Complete SQL schema in spec §"Database Schema Extensions"*

### **2.2 Timeline Execution Engine** ⚙️
- [ ] **Scheduler & State Machine**
  - Timeline player with play/pause/stop/seek
  - Precise cue execution (sub-second accuracy)
  - Action dispatch to camera, overlay, and stream services
  - Progress tracking and completion detection

- [ ] **Action Handlers**
  - Camera preset execution (move PTZ, switch input)
  - Overlay scene activation (show/hide, transition)
  - Stream control (start/stop destination, adjust quality)
  - Wait/delay actions for sequencing

- [ ] **Manual Operator Controls**
  - Timeline queue management (next up, schedule)
  - Manual playback controls (UI + API)
  - Override capabilities (emergency stop, pin camera/overlay)
  - Execution logging for audit trail

### **2.3 Timeline Builder UI** 🛠️
*See spec §"Operator Interface" for "GO LIVE" experience and controls*

- [ ] **Frontend Timeline Editor**
  - Visual timeline builder (drag-drop cues)
  - Multi-track view (video + overlay tracks)
  - Camera preset picker with preview
  - Overlay scene selector
  - Duration/timing editor with validation
  - Timeline preview/simulation mode

- [ ] **Timeline Library**
  - Browse, search, filter timelines
  - Clone/duplicate existing timelines
  - Import/export timeline packages
  - Version history and rollback

### **2.4 Segment System** 📦
- [ ] **Segment Package Format**
  - Bundle definition (timeline + assets + metadata)
  - Manifest with checksums and dependencies
  - Compression and signing for integrity
  - Offline import via USB/network share

- [ ] **Segment Playback**
  - Load segment and validate dependencies
  - Asset caching and preloading
  - Execution with local overrides
  - Sync status back to VistterStudio (when connected)

---

## 🎯 **PHASE 3: INTEGRATION & POLISH** (Week 5+)

### **3.1 System Orchestration** 🎭
- [ ] **Unified Control Service**
  - Coordinate camera, stream, overlay, and timeline services
  - Resource locking and conflict resolution
  - State synchronization across components
  - Event bus for cross-service communication

- [ ] **Error Handling & Recovery**
  *See spec §"Failure Recovery System" for detailed handlers*
  - **Camera Failure**: Backup camera → Test pattern → Last frame
  - **Stream Failure**: Exponential backoff retry (2s, 4s, 8s...60s max, 10 retries)
  - **Degraded Mode**: High CPU → reduce quality; Network issues → reduce bitrate
  - Auto-recovery monitoring and operator alerts
  - *Reference: Handler classes (CameraFailureHandler, StreamFailureHandler, DegradedModeManager) in spec*

### **3.2 Observability & Operations** 📊
- [ ] **Metrics & Monitoring**
  - Prometheus-style metrics endpoint
  - System health dashboard (CPU, GPU, memory, disk, network)
  - Stream quality metrics (bitrate history, error rates)
  - Timeline execution metrics (cue latency, success rate)

- [ ] **Logging & Diagnostics**
  - Structured JSON logging with correlation IDs
  - Log levels and filtering
  - Diagnostic bundle generator (logs + config + metrics)
  - Remote log shipping (optional)

### **3.3 VistterStudio Integration Prep** 🔗
- [ ] **Control Channel Foundation**
  - Outbound WebSocket/MQTT client
  - Command envelope parsing and validation
  - ACK/NACK response handling
  - Telemetry publishing

- [ ] **API Contract Definition**
  - Document command schemas (timeline load/execute, overlay update)
  - Define telemetry events and metrics
  - Version negotiation and feature flags
  - Authentication and credential rotation

---

## 🔧 **TECHNICAL DEBT & QUALITY**

### **Code Quality**
- [ ] Fix authentication flow issue in frontend
- [ ] Add comprehensive error handling to camera service
- [ ] Implement proper password encryption (replace base64)
- [ ] Add input validation and sanitization everywhere

### **Testing Strategy**
- [ ] Unit tests for core services (camera, stream, timeline)
- [ ] Integration tests for FFmpeg pipeline
- [ ] End-to-end timeline execution tests
- [ ] Performance testing on target hardware (Pi, NUC)
- [ ] Chaos testing (network failures, camera drops, process crashes)

### **Documentation**
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Operator manual (camera setup, timeline creation, streaming)
- [ ] Developer guide (architecture, extending, troubleshooting)
- [ ] Deployment guide (Docker, hardware setup, networking)

---

## 📝 **DEFERRED (Post-MVP)**
- VistterStudio cloud integration (full command/control)
- Multi-appliance fleet management
- Advanced overlay rendering (HTML5/WebGL compositor)
- AI-based anomaly detection
- Mobile app/PWA
- Advanced analytics and reporting
- Automated firmware updates

---

## ✨ **SUCCESS CRITERIA**

**Milestone 2: Streaming Pipeline** ✅
- Stream from 3 cameras to 3 destinations simultaneously
- Real-time overlays (text + images) during stream
- Auto-recovery from camera/stream failures
- Health dashboard with live metrics

**Milestone 3: Timeline Engine** ✅
- Create timeline with 10+ actions (camera moves, overlays, stream controls)
- Execute timeline with <500ms cue latency
- Manual playback controls (play/pause/stop/seek)
- Timeline library with import/export

**Milestone 4: Integration Ready** ✅
- Segment package import and playback
- API contracts documented for VistterStudio
- Observability stack (metrics, logs, diagnostics)
- Battle-tested on reference hardware

---

## 📖 **Quick Reference Guide**

### **Before You Start Any Task:**
1. ✅ Read the relevant section in [StreamingPipeline-TechnicalSpec.md](docs/StreamingPipeline-TechnicalSpec.md)
2. ✅ Check cross-references in PRD, SAD, and UXD for context
3. ✅ Review database schema if touching data models
4. ✅ Understand failure recovery patterns for reliability features

### **Key Implementation Principles:**
- **Reliability First** - Auto-recovery, fallbacks, degraded mode over failure
- **Sequential per track, Parallel across tracks** - Timeline execution model
- **Hardware-accelerated** - Pi 5 (`h264_v4l2m2m`) and Mac (`h264_videotoolbox`)
- **Simple MVP, Complex Later** - Text/image overlays now, animations later
- **Multi-destination isolation** - One stream fails, others continue

### **When You're Stuck:**
- Camera issues? → See spec §"Failure Recovery System"
- Timeline questions? → See spec §"Multi-Track Timeline System"
- FFmpeg problems? → See spec §"Streaming Pipeline Architecture" + §"Hardware Acceleration"
- UI/UX decisions? → See UXD.md + spec §"Operator Interface"

---

## 🚀 **LET'S FUCKING GO!** 🚀