# Preview System - Implementation TODO

> **Status**: Draft → Implementation Ready  
> **Target Completion**: 4 weeks  
> **Last Updated**: October 4, 2025

## Overview

This TODO tracks the implementation of the Preview Server + Preview Window subsystem per `PreviewSystem-Specification.md`. Tasks are organized by phase with clear acceptance criteria.

---

## Phase 1: Preview Server Setup (Week 1)

**Goal**: Get MediaMTX running and serving HLS locally.

### Tasks

- [ ] **1.1 Install MediaMTX on Development Machine**
  - [ ] Download MediaMTX binary for Mac/Linux
  - [ ] Place binary in `/usr/local/bin/`
  - [ ] Verify installation: `mediamtx --version`
  - **Owner**: DevOps/Platform  
  - **Estimate**: 30 minutes

- [ ] **1.2 Create MediaMTX Configuration**
  - [ ] Create `/etc/vistterstream/mediamtx.yml`
  - [ ] Configure RTMP ingest on port 1935
  - [ ] Configure HLS output on port 8888
  - [ ] Set low-latency parameters (1s segments)
  - [ ] Enable API on port 9997
  - **Owner**: Backend Lead  
  - **Estimate**: 1 hour

- [ ] **1.3 Test Manual RTMP Push**
  - [ ] Start MediaMTX with config
  - [ ] Push test video with FFmpeg: `ffmpeg -i test.mp4 -f flv rtmp://localhost:1935/preview/stream`
  - [ ] Verify HLS manifest generated: `curl http://localhost:8888/preview/index.m3u8`
  - [ ] Measure latency (should be <2s)
  - **Owner**: Backend Lead  
  - **Estimate**: 1 hour

- [ ] **1.4 Verify HLS Playback in Browser**
  - [ ] Create test HTML with HLS.js player
  - [ ] Load `http://localhost:8888/preview/index.m3u8`
  - [ ] Verify video plays smoothly
  - [ ] Test in Chrome, Safari, Firefox
  - **Owner**: Frontend Lead  
  - **Estimate**: 1 hour

- [ ] **1.5 Create Systemd Service (Production)**
  - [ ] Write `/etc/systemd/system/vistterstream-preview.service`
  - [ ] Configure auto-restart on failure
  - [ ] Test enable/start/stop/restart
  - [ ] Document service management commands
  - **Owner**: DevOps/Platform  
  - **Estimate**: 2 hours

- [ ] **1.6 Test on Raspberry Pi 5**
  - [ ] Download ARM64 MediaMTX binary
  - [ ] Install and configure on Pi
  - [ ] Run stress test (30 min preview)
  - [ ] Measure CPU/memory/temp
  - [ ] Document performance baseline
  - **Owner**: Hardware/Testing  
  - **Estimate**: 4 hours

**Phase 1 Acceptance Criteria**:
- ✅ MediaMTX accepts RTMP on `rtmp://localhost:1935/preview/stream`
- ✅ HLS available at `http://localhost:8888/preview/index.m3u8`
- ✅ Latency <2s (P95)
- ✅ Systemd service starts automatically on boot
- ✅ Runs on Pi 5 without thermal throttling

---

## Phase 2: Stream Router Service (Week 1-2)

**Goal**: Route timeline output to preview server.

### Tasks

- [ ] **2.1 Create StreamRouter Class**
  - [ ] File: `backend/services/stream_router.py`
  - [ ] Implement `PreviewMode` enum (IDLE, PREVIEW, LIVE)
  - [ ] Implement `StreamRouter` class with state machine
  - [ ] Add singleton pattern: `get_stream_router()`
  - **Owner**: Backend Lead  
  - **Estimate**: 3 hours

- [ ] **2.2 Implement start_preview() Method**
  - [ ] Accept timeline_id parameter
  - [ ] Build preview output URL: `rtmp://localhost:1935/preview/stream`
  - [ ] Call `get_timeline_executor().start_timeline()` with preview URL
  - [ ] Set mode to PREVIEW
  - [ ] Handle errors (timeline not found, already running)
  - **Owner**: Backend Lead  
  - **Estimate**: 2 hours

- [ ] **2.3 Implement stop() Method**
  - [ ] Stop timeline executor
  - [ ] Clean up FFmpeg processes
  - [ ] Reset state to IDLE
  - [ ] Handle graceful shutdown
  - **Owner**: Backend Lead  
  - **Estimate**: 1 hour

- [ ] **2.4 Implement go_live() Method**
  - [ ] Verify current mode is PREVIEW
  - [ ] Stop preview stream
  - [ ] Get destination URLs from database
  - [ ] Restart timeline with live destinations
  - [ ] Set mode to LIVE
  - [ ] Log transition event
  - **Owner**: Backend Lead  
  - **Estimate**: 3 hours

- [ ] **2.5 Add Logging and Telemetry**
  - [ ] Log state transitions
  - [ ] Log timeline start/stop events
  - [ ] Add metrics (preview duration, go-live latency)
  - [ ] Integrate with existing logging infrastructure
  - **Owner**: Backend Lead  
  - **Estimate**: 2 hours

- [ ] **2.6 Unit Tests**
  - [ ] Test state machine transitions
  - [ ] Test preview start/stop
  - [ ] Test go-live workflow
  - [ ] Test error cases (invalid timeline, already running)
  - [ ] Mock timeline executor and database
  - **Owner**: Backend Lead  
  - **Estimate**: 4 hours

**Phase 2 Acceptance Criteria**:
- ✅ Timeline can start with preview destination
- ✅ Preview stream appears in MediaMTX paths list
- ✅ Go-live successfully switches destinations
- ✅ Clean shutdown without orphaned FFmpeg processes
- ✅ Unit tests pass with >80% coverage

---

## Phase 3: Preview Control API (Week 2)

**Goal**: Expose REST API for preview control.

### Tasks

- [ ] **3.1 Create Preview Router**
  - [ ] File: `backend/routers/preview.py`
  - [ ] Define request/response models (Pydantic)
  - [ ] Create APIRouter with `/api/preview` prefix
  - [ ] Add OpenAPI tags and documentation
  - **Owner**: Backend Lead  
  - **Estimate**: 1 hour

- [ ] **3.2 Implement POST /api/preview/start**
  - [ ] Accept `StartPreviewRequest` (timeline_id)
  - [ ] Verify timeline exists
  - [ ] Check preview server health
  - [ ] Call `stream_router.start_preview()`
  - [ ] Return HLS URL and status
  - [ ] Handle errors with appropriate HTTP codes
  - **Owner**: Backend Lead  
  - **Estimate**: 2 hours

- [ ] **3.3 Implement POST /api/preview/stop**
  - [ ] Call `stream_router.stop()`
  - [ ] Return success message
  - [ ] Handle "not running" error
  - **Owner**: Backend Lead  
  - **Estimate**: 1 hour

- [ ] **3.4 Implement POST /api/preview/go-live**
  - [ ] Accept `GoLiveRequest` (destination_ids)
  - [ ] Verify destinations exist
  - [ ] Call `stream_router.go_live()`
  - [ ] Return destination names and status
  - [ ] Add warning about timeline restart (temporary)
  - **Owner**: Backend Lead  
  - **Estimate**: 2 hours

- [ ] **3.5 Implement GET /api/preview/status**
  - [ ] Return current mode (idle/preview/live)
  - [ ] Return timeline info if active
  - [ ] Return HLS URL if in preview mode
  - [ ] Include preview server health check
  - **Owner**: Backend Lead  
  - **Estimate**: 1.5 hours

- [ ] **3.6 Implement GET /api/preview/health**
  - [ ] Check MediaMTX API: `http://localhost:9997/v1/config/get`
  - [ ] Return active streams count
  - [ ] Return error if server unreachable
  - **Owner**: Backend Lead  
  - **Estimate**: 1 hour

- [ ] **3.7 Create PreviewServerHealth Service**
  - [ ] File: `backend/services/preview_server_health.py`
  - [ ] Method: `check_health()` → bool
  - [ ] Method: `get_active_streams()` → dict
  - [ ] Use httpx for async HTTP requests
  - [ ] Add timeout and retry logic
  - **Owner**: Backend Lead  
  - **Estimate**: 2 hours

- [ ] **3.8 Register Router in Main App**
  - [ ] Import preview router in `backend/main.py`
  - [ ] Add `app.include_router(preview.router)`
  - [ ] Verify routes appear in OpenAPI docs
  - **Owner**: Backend Lead  
  - **Estimate**: 15 minutes

- [ ] **3.9 Integration Tests**
  - [ ] Test preview start/stop lifecycle
  - [ ] Test go-live workflow
  - [ ] Test error cases (invalid timeline, server down)
  - [ ] Test concurrent request handling
  - [ ] Mock MediaMTX API responses
  - **Owner**: Backend Lead  
  - **Estimate**: 4 hours

**Phase 3 Acceptance Criteria**:
- ✅ All API endpoints return correct status codes
- ✅ Error messages are actionable
- ✅ OpenAPI documentation complete
- ✅ Health check reports MediaMTX status accurately
- ✅ Integration tests pass

---

## Phase 4: Preview Window UI (Week 2-3)

**Goal**: Build React component with HLS player and controls.

### Tasks

- [ ] **4.1 Install HLS.js Dependency**
  - [ ] Run `npm install hls.js`
  - [ ] Add type definitions: `npm install --save-dev @types/hls.js`
  - [ ] Verify installation
  - **Owner**: Frontend Lead  
  - **Estimate**: 15 minutes

- [ ] **4.2 Create PreviewWindow Component**
  - [ ] File: `frontend/src/components/PreviewWindow.tsx`
  - [ ] Define component props interface
  - [ ] Create functional component with hooks
  - [ ] Add basic JSX structure (video + controls)
  - **Owner**: Frontend Lead  
  - **Estimate**: 1 hour

- [ ] **4.3 Implement HLS Player**
  - [ ] Create video ref with `useRef<HTMLVideoElement>`
  - [ ] Initialize HLS.js in `useEffect`
  - [ ] Configure low-latency settings
  - [ ] Handle MANIFEST_PARSED event
  - [ ] Handle ERROR events
  - [ ] Clean up on unmount
  - **Owner**: Frontend Lead  
  - **Estimate**: 3 hours

- [ ] **4.4 Implement Status Polling**
  - [ ] Call `/api/preview/status` every 2 seconds
  - [ ] Update component state with response
  - [ ] Handle network errors gracefully
  - [ ] Stop polling on unmount
  - **Owner**: Frontend Lead  
  - **Estimate**: 1.5 hours

- [ ] **4.5 Implement Start Preview Button**
  - [ ] Call `POST /api/preview/start` with timeline_id
  - [ ] Show loading spinner during request
  - [ ] Display error message on failure
  - [ ] Disable button when no timeline selected
  - [ ] Disable when preview server unhealthy
  - **Owner**: Frontend Lead  
  - **Estimate**: 2 hours

- [ ] **4.6 Implement Stop Preview Button**
  - [ ] Call `POST /api/preview/stop`
  - [ ] Show loading spinner
  - [ ] Clean up HLS player
  - [ ] Handle errors
  - **Owner**: Frontend Lead  
  - **Estimate**: 1 hour

- [ ] **4.7 Implement Go Live Button**
  - [ ] Show only when in preview mode
  - [ ] Require destination selection
  - [ ] Show confirmation dialog with destination list
  - [ ] Call `POST /api/preview/go-live`
  - [ ] Display success/error message
  - [ ] Animate button (pulse effect)
  - **Owner**: Frontend Lead  
  - **Estimate**: 2.5 hours

- [ ] **4.8 Load and Display Destinations**
  - [ ] Fetch destinations from `/api/destinations`
  - [ ] Display as checkboxes
  - [ ] Store selection in component state
  - [ ] Show only active destinations
  - **Owner**: Frontend Lead  
  - **Estimate**: 2 hours

- [ ] **4.9 Add Status Badges**
  - [ ] OFFLINE badge (gray) when idle
  - [ ] PREVIEW badge (blue, pulsing) when previewing
  - [ ] LIVE badge (red, pulsing) when live
  - [ ] Show timeline name if active
  - **Owner**: Frontend Lead  
  - **Estimate**: 1.5 hours

- [ ] **4.10 Error Handling and Messages**
  - [ ] Create error message component
  - [ ] Show actionable errors (server down, timeline not found)
  - [ ] Warning for unhealthy preview server
  - [ ] Info messages (latency, timeline restart warning)
  - **Owner**: Frontend Lead  
  - **Estimate**: 2 hours

- [ ] **4.11 Styling and Layout**
  - [ ] 16:9 aspect ratio video container
  - [ ] Responsive layout (desktop focus)
  - [ ] Tailwind CSS styling
  - [ ] Match VistterStream design system
  - [ ] Dark theme
  - **Owner**: Frontend Lead  
  - **Estimate**: 3 hours

- [ ] **4.12 Component Tests**
  - [ ] Test component renders
  - [ ] Test HLS player initialization
  - [ ] Test button click handlers
  - [ ] Test error states
  - [ ] Mock API responses
  - **Owner**: Frontend Lead  
  - **Estimate**: 4 hours

**Phase 4 Acceptance Criteria**:
- ✅ Video plays smoothly with <2s latency
- ✅ Buttons enable/disable based on state
- ✅ Error messages are clear and actionable
- ✅ Component updates in real-time (2s polling)
- ✅ UI matches VistterStream design system
- ✅ Component tests pass

---

## Phase 5: Timeline Editor Integration (Week 3)

**Goal**: Embed preview window in timeline editor UI.

### Tasks

- [ ] **5.1 Import PreviewWindow Component**
  - [ ] Add import in `TimelineEditor.tsx`
  - [ ] Pass timelineId prop from selected timeline
  - [ ] Add callback handlers (optional)
  - **Owner**: Frontend Lead  
  - **Estimate**: 30 minutes

- [ ] **5.2 Position Preview Window**
  - [ ] Add section above timeline tracks
  - [ ] Add collapsible header: "Preview Monitor"
  - [ ] Implement expand/collapse toggle
  - [ ] Persist collapsed state in localStorage
  - **Owner**: Frontend Lead  
  - **Estimate**: 2 hours

- [ ] **5.3 Handle Timeline Selection**
  - [ ] Pass `selectedTimeline?.id` to PreviewWindow
  - [ ] Auto-stop preview when changing timelines (optional)
  - [ ] Show warning if preview running and switching timelines
  - **Owner**: Frontend Lead  
  - **Estimate**: 1.5 hours

- [ ] **5.4 Responsive Layout Adjustments**
  - [ ] Test on 1920x1080 screen
  - [ ] Test on 1366x768 screen
  - [ ] Adjust preview window size for smaller screens
  - [ ] Ensure timeline editor remains usable
  - **Owner**: Frontend Lead  
  - **Estimate**: 2 hours

- [ ] **5.5 Keyboard Shortcuts (Optional)**
  - [ ] Space: Play/pause preview
  - [ ] L: Go live
  - [ ] Esc: Stop preview
  - [ ] Document shortcuts in UI
  - **Owner**: Frontend Lead  
  - **Estimate**: 3 hours (OPTIONAL)

- [ ] **5.6 User Acceptance Testing**
  - [ ] Test with non-technical user
  - [ ] Collect feedback on UX
  - [ ] Iterate on confusing UI elements
  - [ ] Document common user questions
  - **Owner**: Product/UX  
  - **Estimate**: 4 hours

**Phase 5 Acceptance Criteria**:
- ✅ Preview window visible when timeline selected
- ✅ UI remains responsive during preview
- ✅ Layout works on common screen sizes
- ✅ Non-technical user can operate without training

---

## Phase 6: Testing & Hardening (Week 3-4)

**Goal**: Validate on Raspberry Pi and handle edge cases.

### Tasks

- [ ] **6.1 Deploy to Raspberry Pi 5**
  - [ ] Install MediaMTX on Pi
  - [ ] Deploy VistterStream backend updates
  - [ ] Deploy frontend build
  - [ ] Configure systemd services
  - **Owner**: DevOps/Platform  
  - **Estimate**: 3 hours

- [ ] **6.2 Performance Benchmarking**
  - [ ] Test preview + live streaming simultaneously (future)
  - [ ] Measure CPU usage (target <80%)
  - [ ] Measure memory usage (target <200MB additional)
  - [ ] Measure latency (target <2s P95)
  - [ ] Monitor temperature (no thermal throttling)
  - **Owner**: Testing/QA  
  - **Estimate**: 4 hours

- [ ] **6.3 Timeline Complexity Tests**
  - [ ] Test with 3-camera timeline
  - [ ] Test with camera switching + overlays
  - [ ] Test with 30-minute loop
  - [ ] Test with rapid camera switches (5s per cue)
  - **Owner**: Testing/QA  
  - **Estimate**: 3 hours

- [ ] **6.4 Go-Live with Real Platforms**
  - [ ] Test go-live to YouTube (test stream key)
  - [ ] Test go-live to Facebook
  - [ ] Test go-live to multiple destinations
  - [ ] Verify stream quality on platform side
  - **Owner**: Testing/QA  
  - **Estimate**: 3 hours

- [ ] **6.5 Preview Server Crash Recovery**
  - [ ] Kill MediaMTX process manually
  - [ ] Verify systemd restarts service
  - [ ] Verify health check detects failure
  - [ ] Verify UI shows error message
  - [ ] Test preview restart after recovery
  - **Owner**: Testing/QA  
  - **Estimate**: 2 hours

- [ ] **6.6 Stress Testing**
  - [ ] Run preview for 60 minutes continuously
  - [ ] Rapid start/stop cycles (10x in 5 minutes)
  - [ ] Concurrent API requests
  - [ ] Memory leak detection
  - **Owner**: Testing/QA  
  - **Estimate**: 4 hours

- [ ] **6.7 Error Scenario Testing**
  - [ ] Timeline not found
  - [ ] Preview server down
  - [ ] Invalid destinations
  - [ ] Network interruption during go-live
  - [ ] Disk full (HLS segments)
  - **Owner**: Testing/QA  
  - **Estimate**: 3 hours

- [ ] **6.8 Browser Compatibility**
  - [ ] Test in Chrome 90+
  - [ ] Test in Safari 14+ (native HLS)
  - [ ] Test in Firefox 88+
  - [ ] Document any compatibility issues
  - **Owner**: Testing/QA  
  - **Estimate**: 2 hours

- [ ] **6.9 Latency Optimization**
  - [ ] Measure current latency
  - [ ] Tune HLS segment duration
  - [ ] Tune HLS buffer settings
  - [ ] Tune FFmpeg encoding parameters
  - [ ] Document optimal settings
  - **Owner**: Testing/Performance  
  - **Estimate**: 4 hours

- [ ] **6.10 Load Testing**
  - [ ] Simulate operator workflow (20 preview sessions)
  - [ ] Monitor resource usage over time
  - [ ] Identify performance bottlenecks
  - [ ] Recommend hardware requirements
  - **Owner**: Testing/Performance  
  - **Estimate**: 4 hours

**Phase 6 Acceptance Criteria**:
- ✅ Preview runs on Pi 5 without overheating
- ✅ Go-live successfully publishes to YouTube
- ✅ System recovers from preview server crashes
- ✅ 60-minute preview session completes without issues
- ✅ CPU usage <80% on Pi 5
- ✅ Latency <2s (P95)

---

## Phase 7: Documentation & Release (Week 4)

**Goal**: Production-ready release with documentation.

### Tasks

- [ ] **7.1 Operator User Guide**
  - [ ] Write step-by-step guide with screenshots
  - [ ] Document preview workflow
  - [ ] Document go-live workflow
  - [ ] Include troubleshooting tips
  - **Owner**: Product/Docs  
  - **Estimate**: 6 hours

- [ ] **7.2 Troubleshooting Guide**
  - [ ] Common issues and solutions
  - [ ] Diagnostic commands
  - [ ] Log file locations
  - [ ] When to restart services
  - **Owner**: Support/Docs  
  - **Estimate**: 4 hours

- [ ] **7.3 Architecture Documentation**
  - [ ] Update `PreviewSystem-Specification.md` with actual implementation
  - [ ] Document deviations from spec
  - [ ] Add sequence diagrams
  - [ ] Document API contracts
  - **Owner**: Tech Lead/Docs  
  - **Estimate**: 4 hours

- [ ] **7.4 API Documentation**
  - [ ] Ensure OpenAPI specs complete
  - [ ] Add request/response examples
  - [ ] Document error codes
  - [ ] Add Postman collection
  - **Owner**: Backend Lead  
  - **Estimate**: 3 hours

- [ ] **7.5 Demo Video**
  - [ ] Record preview workflow demo
  - [ ] Record go-live demo
  - [ ] Show timeline creation + preview
  - [ ] Narrate key features
  - [ ] Upload to YouTube/Vimeo
  - **Owner**: Product/Marketing  
  - **Estimate**: 4 hours

- [ ] **7.6 Release Notes**
  - [ ] Changelog entry
  - [ ] Feature highlights
  - [ ] Breaking changes (if any)
  - [ ] Upgrade instructions
  - [ ] Known limitations
  - **Owner**: Product Manager  
  - **Estimate**: 2 hours

- [ ] **7.7 Update Main README**
  - [ ] Add preview system section
  - [ ] Link to detailed docs
  - [ ] Update feature list
  - [ ] Add screenshots
  - **Owner**: Product/Docs  
  - **Estimate**: 1 hour

- [ ] **7.8 Training Materials**
  - [ ] Create quick-start video (5 min)
  - [ ] Create troubleshooting checklist
  - [ ] Create FAQ document
  - **Owner**: Support/Training  
  - **Estimate**: 6 hours

**Phase 7 Acceptance Criteria**:
- ✅ Operator guide complete with screenshots
- ✅ Troubleshooting guide covers common issues
- ✅ API documentation complete in OpenAPI
- ✅ Demo video published
- ✅ Release notes approved

---

## Post-Release Tasks (Future)

### Quick Wins (1-2 weeks)

- [ ] Add preview quality presets (low/medium/high)
- [ ] Add preview recording (DVR feature)
- [ ] Add audio level meters in preview
- [ ] Add frame rate / bitrate stats overlay

### Future Enhancements (Q1 2026)

- [ ] **Seamless Go-Live**: Transition without restarting timeline
- [ ] **Multi-User Preview**: Multiple viewers of same preview
- [ ] **WebRTC Preview**: Sub-second latency option
- [ ] **Preview Timeline Scrubbing**: Seek backward/forward
- [ ] **Instant Replay**: Save and replay last N minutes

---

## Progress Tracking

### Overall Progress

- [ ] Phase 1: Preview Server Setup (0/6 tasks)
- [ ] Phase 2: Stream Router Service (0/6 tasks)
- [ ] Phase 3: Preview Control API (0/9 tasks)
- [ ] Phase 4: Preview Window UI (0/12 tasks)
- [ ] Phase 5: Timeline Editor Integration (0/6 tasks)
- [ ] Phase 6: Testing & Hardening (0/10 tasks)
- [ ] Phase 7: Documentation & Release (0/8 tasks)

**Total**: 0/57 core tasks completed

### Time Estimate

- **Phase 1**: ~12 hours
- **Phase 2**: ~15 hours
- **Phase 3**: ~15 hours
- **Phase 4**: ~25 hours
- **Phase 5**: ~13 hours
- **Phase 6**: ~32 hours
- **Phase 7**: ~30 hours

**Total**: ~142 hours (~4 weeks for 1 full-time developer)

---

## Risk Register

| Risk | Mitigation | Owner |
|------|------------|-------|
| MediaMTX crashes frequently on Pi | Test early, have FFmpeg fallback plan | Testing |
| Latency >2s unacceptable | Tune HLS settings, consider WebRTC | Performance |
| Go-live transition too slow | Document as known limitation, plan seamless for Phase 2 | Product |
| CPU overload on Pi during preview | Adaptive quality reduction, limit concurrent streams | Performance |

---

## Success Metrics

**Track these post-release**:

- [ ] Preview latency <2s (P95) - **Measurement**: Timestamp in video frame
- [ ] Go-live success rate >99% - **Measurement**: Successful transitions / attempts
- [ ] Preview server uptime >99% - **Measurement**: systemd uptime checks
- [ ] Operator satisfaction >4.5/5 - **Measurement**: Post-release survey
- [ ] Feature adoption >80% - **Measurement**: % of streams using preview

---

## Notes & Decisions

### Decision Log

- **2025-10-04**: Selected MediaMTX over Nginx-RTMP (better maintenance, ARM support)
- **2025-10-04**: Accepted timeline restart for go-live (seamless in Phase 2)
- **2025-10-04**: Preview server runs as separate systemd service (not in container for simplicity)

### Open Questions

1. Should preview recording be mandatory for audit compliance?
   - **Status**: Discuss with product team
2. Do we need preview authentication for security?
   - **Status**: No for MVP (localhost only)
3. Should we support simultaneous preview + live?
   - **Status**: Future enhancement, not MVP

---

**Ready to start?** Begin with Phase 1, Task 1.1! 🚀

