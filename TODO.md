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

### 📊 **Phase 1 Progress: 90% Complete** ✅ **STREAMING TO YOUTUBE LIVE!**

### **1.1 FFmpeg Streaming Engine** ⚡
*See spec §"Streaming Pipeline Architecture"*

- [x] **FFmpeg Process Manager** ✅ **(COMPLETED 2025-10-01)** 🎉 **LIVE ON YOUTUBE!**
  - ✅ Spawn/manage FFmpeg processes with proper lifecycle control
  - ✅ Process monitoring with health checks and auto-restart
  - ✅ Graceful shutdown and resource cleanup
  - ✅ Output parsing for errors, warnings, and stats (bitrate, fps, dropped frames)
  - ✅ Hardware acceleration detection (Mac: h264_videotoolbox, Pi 5: h264_v4l2m2m)
  - ✅ RTSP camera input → RTMP output streaming
  - ✅ Successfully streaming to YouTube Live!

- [x] **Streaming Destinations Architecture** ✅ **(COMPLETED 2025-10-01)** 🎉 **DESTINATION-FIRST DESIGN!**
  - ✅ Centralized destination management (YouTube, Facebook, Twitch, Custom RTMP)
  - ✅ Reusable destination configs with platform presets
  - ✅ Stream keys configured once, used everywhere
  - ✅ Streams reference destinations (no duplicate keys)
  - ✅ Timelines reference destinations (multi-select support)
  - ✅ Usage tracking (`last_used` timestamp)
  - ✅ CRUD API for destination management
  - ✅ Frontend UI with platform-specific forms

- [x] **Single-Camera Streaming** ✅ **(COMPLETED 2025-10-01)**
  - ✅ YouTube RTMP streaming (LIVE and working!)
  - ✅ Encoding profiles (1920x1080/720p/480p, 4500k/6000k/2500k bitrate, 30/60fps)
  - ✅ Start/Stop control with orphaned process cleanup
  - ✅ Emergency "Kill All Streams" button
  - ✅ Stream status tracking and auto-refresh

- [ ] **Multi-Destination Streaming** (Architecture ready, needs testing!)
  - ⏳ Simultaneous streaming to 3+ destinations (YouTube + Facebook + Twitch)
  - ⏳ Per-destination encoding profiles
  - ⏳ Destination-specific retry logic and failure isolation

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

- [x] **Backend Endpoints** ✅ **(COMPLETED 2025-10-01)**
  - ✅ Start/stop streams with encoding profiles
  - ✅ Get real-time stream status
  - ✅ Stream configuration (name, camera, destination, quality)
  - ⏳ Stream recording control (DVR - future)
  - ⏳ Live metrics updates (coming soon)

- [x] **Frontend Stream Dashboard** ✅ **(COMPLETED 2025-10-01)**
  - ✅ Live stream status indicators with auto-refresh (5s)
  - ✅ Stream list showing camera, destination, quality, status
  - ✅ Quick actions (start/stop buttons)
  - ✅ Visual status indicators (running, stopped, starting, error)
  - ✅ **Add Stream form UI** (YouTube, Facebook, Twitch, Custom RTMP)
  - ⏳ Metrics graphs (bitrate, FPS - coming soon)

- [x] **Camera Management UI** ✅ **(COMPLETED 2025-10-01)**
  - ✅ Live camera thumbnails with auto-refresh
  - ✅ **Camera Health Monitor** - Background service tests cameras every 3 min
  - ✅ Lightweight status probes (HEAD/GET requests, not full RTSP)
  - ✅ Live stream viewer (500ms snapshot refresh)
  - ✅ Click thumbnail or play button to view live feed
  - ✅ HTTP Digest auth for Reolink cameras

---

## 🎬 **PHASE 2: TIMELINE & SEGMENT ENGINE** (Weeks 3-4)
*Reference: [StreamingPipeline-TechnicalSpec.md](docs/StreamingPipeline-TechnicalSpec.md)*

### 📊 **Phase 2 Progress: 60% Complete** ✅ **COMPOSITE STREAMS WORKING!**

### **2.1 Timeline Data Model** 📋
*See spec §"Multi-Track Timeline System" for complete schema*

- [x] **Timeline Schema Design** ✅ **(COMPLETED 2025-10-01)**
  - ✅ Multi-track structure: 1 video track + multiple overlay tracks
  - ✅ Action/Cue definitions (show_camera with camera_id, duration, transitions)
  - ✅ Timing model: Sequential per track, parallel across tracks
  - ✅ Validation with Pydantic schemas
  - ✅ Looping support for infinite playback

- [x] **Database Extensions** ✅ **(COMPLETED 2025-10-01)**
  - ✅ `timelines` table (id, name, description, duration, fps, resolution, loop, is_active)
  - ✅ `timeline_tracks` table (track_type, layer, is_enabled, timeline_id)
  - ✅ `timeline_cues` table (track_id, cue_order, start_time, duration, action_type, action_params, transitions)
  - ✅ `timeline_executions` table (timeline_id, started_at, completed_at, status, error_message, metrics)
  - ⏳ Assets table (overlays, test patterns - coming next)
  - ⏳ Execution audit logs (detailed tracking - future)

### **2.2 Timeline Execution Engine** ⚙️
- [x] **Timeline Executor Core** ✅ **(COMPLETED 2025-10-01)** 🎉 **MULTI-CAMERA SWITCHING WORKING!**
  - ✅ Timeline playback with start/stop control
  - ✅ Sequential cue execution with precise timing
  - ✅ Camera switching via FFmpeg stream restart
  - ✅ Looping support for continuous operation
  - ✅ Execution state tracking in database
  - ✅ Error handling and graceful failure recovery

- [x] **Camera Switching Action Handler** ✅ **(COMPLETED 2025-10-01)**
  - ✅ `show_camera` action executes camera switches
  - ✅ Stop current FFmpeg stream → Start new stream with different camera
  - ✅ Cue duration control (e.g., 1 minute per camera)
  - ⏳ PTZ preset execution (coming later)
  - ⏳ Overlay scene activation (next priority)

- [ ] **Advanced Playback Controls** (Next up!)
  - ⏳ Pause/resume timeline execution
  - ⏳ Seek to specific cue
  - ⏳ Manual override (pin camera, skip cue)
  - ⏳ Timeline queue management

- [ ] **Timeline Scheduling** (Future)
  - Schedule timeline for future execution
  - Recurring schedules (daily, weekly, etc.)
  - Pre-flight checks before go-live
  - Scheduled timeline queue

### **2.3 Timeline Builder UI** 🛠️
*See spec §"Operator Interface" for "GO LIVE" experience and controls*

- [x] **Frontend Timeline Editor** ✅ **(COMPLETED 2025-10-01)** 🎉 **VISUAL TIMELINE EDITOR!**
  - ✅ Visual timeline creator with sidebar
  - ✅ Multi-track view (video track visible)
  - ✅ Camera selector from camera palette
  - ✅ Add/remove/edit cues (camera + duration)
  - ✅ Duration editor for each cue
  - ✅ Timeline metadata (name, description, resolution, fps, loop)
  - ✅ Save timeline to database
  - ✅ Multi-destination selector for streaming
  - ⏳ Drag-drop cue reordering (future enhancement)
  - ⏳ Overlay track UI (coming next)
  - ⏳ Timeline preview/simulation mode (future)

- [ ] **Timeline Library** (Partially implemented)
  - ✅ Browse existing timelines (sidebar list)
  - ✅ Select timeline to edit
  - ⏳ Search/filter timelines
  - ⏳ Clone/duplicate timelines
  - ⏳ Import/export timeline packages
  - ⏳ Version history and rollback

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