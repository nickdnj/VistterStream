# Product Requirements Document (PRD): Vistter Platform — VistterStream Appliance Focus

## 1. Product Overview
Vistter is an end-to-end platform for producing live and scheduled video streams. It consists of two primary products:

* **VistterStream** — an on-premises appliance that ingests camera feeds, executes show timelines, renders overlays, and distributes the encoded program feed to streaming destinations.
* **VistterStudio** — a cloud-hosted (firewalled) timeline editor and control surface that author VistterStream appliances subscribe to for orchestration instructions, assets, and monitoring directives.

This PRD focuses on the first shippable version of **VistterStream** while capturing the integration touchpoints that must exist for future VistterStudio control. The appliance must operate reliably on commodity edge hardware (e.g., Raspberry Pi, Intel NUC), expose a local-first configuration experience, and maintain a secure outbound channel to VistterStudio in order to receive instructions despite inbound firewall restrictions.

## 2. Product Goals
* **Establish the Vistter platform foundations** by delivering an appliance that can be controlled by VistterStudio through a defined outbound integration channel.
* **Preserve local camera investments** by making it easy to onboard stationary and PTZ cameras without bespoke configuration.
* **Deliver broadcast-ready streams** with synchronized overlays and camera motions driven by VistterStudio or local fallback automation.
* **Remain self-reliant offline** so that timelines, overlays, VistterStudio-authored segments, and fallback media continue operating during cloud or VistterStudio outages.
* **Provide operational transparency** with health monitoring, alerts, and auditability for both local operators and remote supervisors.

## 3. Stakeholders & Personas
| Persona | Goals | Pain Points Addressed |
| --- | --- | --- |
| **Local Operator** (shop owner, venue manager) | Configure cameras, verify previews, ensure stream reliability. | Complex camera setups, lack of technical expertise, limited time.
| **Remote Producer** (VistterStudio editor) | Author timelines, trigger shows, monitor execution remotely. | Cannot directly reach appliances behind firewalls; needs actionable feedback.
| **System Admin / IT** | Maintain security, firmware, and appliance updates. | Mixed hardware fleet, sensitive credentials, inbound firewall restrictions.
| **Advertiser/Partner** | Ensure overlays/ads play on schedule with proof of performance. | Needs verification when remote connectivity is intermittent.
| **Platform Product Team** | Validate platform architecture and integration before expanding VistterStudio. | Requires clarity on contracts between products and phased roadmap.

## 4. Scope Definition
* **In Scope (VistterStream v1.0)**
  * Local web application for appliance configuration, monitoring, and maintenance.
  * Camera discovery, manual addition, and PTZ preset management.
  * Outbound, firewall-friendly integration with VistterStudio for timeline execution, overlay ingestion, segment synchronization, and reporting.
  * Streaming to one or more destinations with configurable encoding profiles.
  * Local library to sync, validate, and manually trigger VistterStudio-authored segments for offline or operator-driven playback.
  * Logging, health telemetry, and status notifications surfaced locally and sync’d back to VistterStudio when connectivity exists.
  * Definition of the API contracts (events, commands, acknowledgements) between VistterStream and VistterStudio.
* **Out of Scope (for initial release)**
  * Authoring workflows inside VistterStudio beyond the minimal surfaces required for integration testing.
  * On-device video editing beyond overlay composition.
  * Automated firmware updates for third-party camera hardware.
  * Native mobile applications (responsive web only).

## 5. Detailed Use Cases
| ID | Title | Primary Actor | Preconditions | Main Flow | Alternate / Exception Flows |
| --- | --- | --- | --- | --- | --- |
| UC-01 | First-time Appliance Setup | Local Operator | Appliance powered, connected to LAN. | 1. Operator accesses appliance via default URL. 2. Completes guided setup (timezone, credentials, outbound connection key). 3. Confirms system health baseline. | Network unreachable → show troubleshooting steps; outbound validation fails → provide proxy instructions. |
| UC-02 | Establish Trust with VistterStudio | System Admin | UC-01 complete; outbound internet available. | 1. Operator retrieves pairing code/token from VistterStudio. 2. Appliance opens outbound TLS channel and presents credentials. 3. Exchange device capabilities and configuration schemas. | Firewall blocks outbound ports → retry with alternative ports; token expired → request regeneration. |
| UC-03 | Camera Onboarding | Local Operator | UC-01 complete, operator authenticated. | 1. Start camera discovery or manual add. 2. Enter IP, protocol, credentials. 3. Test connection with preview. 4. Save camera config to appliance. | Connection test fails → provide actionable error; unsupported protocol → escalate with help link. |
| UC-04 | PTZ Preset Creation | Local Operator | PTZ-capable camera configured. | 1. Select camera and open PTZ controls. 2. Adjust pan/tilt/zoom with live preview. 3. Save preset name (e.g., “Front Entrance – Wide”). | PTZ command times out → retry guidance; camera offline → mark preset pending. |
| UC-05 | Timeline Synchronization | Remote Producer | Cameras and presets exist; VistterStudio timeline scheduled. | 1. VistterStudio publishes upcoming timeline events to message queue/topic. 2. Appliance downloads assets and pre-roll instructions. 3. Appliance acknowledges readiness, then executes steps at runtime. | Message delivery delayed → run local schedule; asset download fails → use cached fallback asset. |
| UC-06 | Manual Stream Control | Local Operator | Streams configured; operator authenticated. | 1. From dashboard, choose destination. 2. Start or stop stream. 3. View status, bitrate, errors. | Destination rejects key → prompt to update credentials; health thresholds exceeded → surface warnings. |
| UC-07 | Overlay Synchronization | Remote Producer | Valid VistterStudio credentials cached. | 1. Appliance receives overlay manifest. 2. Downloads assets into cache. 3. Validates checksums and availability. | Download fails → retries with exponential backoff; cache full → prompt cleanup. |
| UC-08 | Overlay Scene Playback | Control & Orchestration Service | Overlay assets cached; stream encoder healthy. | 1. VistterStudio publishes overlay orchestration script (scenes, layers, timing). 2. Appliance validates script against supported schema. 3. Overlay service executes scenes (fades, position changes, slide swaps) in sync with stream timeline. | Unsupported directive → fall back to safe defaults and log warning; timing drift detected → resync using timeline heartbeat. |
| UC-09 | Segment Import & Local Playback | Local Operator | Appliance paired with VistterStudio; segment package available. | 1. Operator selects "Import Segment" in Timelines view. 2. Appliance retrieves VistterStudio-authored segment (timeline slice + overlays) via sync channel or removable media. 3. Operator queues or manually plays segment locally, optionally chaining with live inputs. | Segment validation fails → provide error log and fallback slate; offline scenario → operator loads from USB/export package. |
| UC-10 | Incident Response & Recovery | System Admin | Appliance running in production. | 1. Receives alert (camera offline, CPU high, disk full). 2. Reviews diagnostic logs and metrics. 3. Applies corrective action (restart stream, adjust settings). | Appliance unreachable → instructions for physical reboot; persistent failure → escalate to support. |
| UC-11 | Third-Party Destination Streaming | Local Operator | Destination credentials configured. | 1. Operator selects YouTube/Facebook/Twitch profile. 2. Appliance validates stream key and handshake. 3. Stream engine routes encoded output per schedule. | Destination rejects stream → present troubleshooting steps; bandwidth insufficient → auto-adjust bitrate and alert operator. |

## 6. Functional Requirements
### 6.1 Platform Integration
* Provide an outbound-only connectivity model using TLS (WebSocket, MQTT, or HTTPS long poll) so appliances behind firewalls can receive commands without inbound port exposure.
* Support device registration, credential rotation, and revocation initiated from VistterStudio.
* Define a command schema for timelines (start/stop, preset move, overlay change, health request) with versioning and backward compatibility guarantees.
* Buffer incoming commands for at least 60 seconds during transient connectivity loss and reconcile once the channel resumes.
* Publish acknowledgements, telemetry, and error events back to VistterStudio within 3 seconds of processing.

### 6.2 Camera & PTZ Management
* Discover ONVIF-compatible cameras and allow manual RTSP/RTMP entry.
* Validate camera connectivity (ping, auth, stream negotiation) before saving.
* Store unlimited presets per PTZ camera; map presets to VistterStudio shot identifiers.
* Provide test-and-save workflow for PTZ presets with snap-to-position confirmation.
* Maintain camera state (online/offline, last heartbeat, current preset) and expose updates to VistterStudio.

### 6.3 Timeline & Overlay Execution
* Subscribe to VistterStudio timeline events via secure channel and schedule execution with millisecond precision.
* Execute timeline steps with deterministic ordering: preset move → overlay update → stream routing.
* Cache overlay assets locally with versioning and fallback media.
* Import and catalog VistterStudio-authored **Segments** (encapsulated timeline slices with overlays and metadata) for both scheduled execution and manual local playback, including support for offline package ingestion.
* Interpret **Overlay Composition Language (OCL)** payloads that describe scenes, layers, transitions, and property automation (opacity, transforms, text tokens) with deterministic timing.
* Support time-relative (`t+`) and absolute (`00:01:23.500`) cues, transition definitions (fade, wipe, cut), z-order priorities, and layout anchors within the safe-title grid.
* Validate OCL payloads with schema versioning, reject unknown directives gracefully, and publish validation errors back to VistterStudio.
* Report execution metrics (latency, success/failure, active preset, overlay scene status) back to VistterStudio.
* Provide operator controls to queue, preview, and manually trigger imported segments while logging actions and notifying VistterStudio of local overrides.
* Allow locally-authenticated operators to trigger manual overrides that are logged and relayed to VistterStudio (e.g., pause overlays, pin emergency slate).

### 6.4 Streaming & Processing
* Support concurrent streaming to at least three destinations with configurable encoding profiles.
* Provide bitrate, resolution, and keyframe configuration per destination.
* Automatically recover from FFmpeg crashes with bounded retries and exponential backoff.
* Insert slate/fallback feed when source camera fails to deliver frames within threshold.
* Support optional recording of program output for later upload once bandwidth is available.

### 6.5 Local Web Experience
* Role-based access: Operator (camera/stream actions) and Admin (system configuration).
* Dashboard with live previews, health widgets, and recent activity log including VistterStudio command history.
* Wizards for onboarding (setup, camera add, VistterStudio pairing) and guided troubleshooting.
* System settings to manage credentials, network configuration, backups, and software updates.

### 6.6 Observability & Maintenance
* Collect and store system metrics (CPU, GPU, memory, disk, network throughput) with 24-hour retention.
* Provide downloadable diagnostic bundle (logs, configs, metrics snapshots).
* Send optional webhook/email alerts for critical incidents (stream failure, storage near capacity).
* Expose API endpoints for remote monitoring/automation (read-only tokens) and forward summaries to VistterStudio.
* Record overlay and segment playback audit trails, including cue execution timestamps, asset identifiers, segment identifiers, and operator overrides for advertiser proof-of-play.

### 6.7 Overlay Composition Language Definition
* Provide a JSON-based schema (`ocl`) that encapsulates:
  * `timeline` metadata (id, version, frame rate, base resolution).
  * `assets` manifest with secure URLs, checksums, media type, and usage rights tags.
  * `scenes` array containing ordered `tracks` (background, lower-third, fullscreen slide) with cues specifying `start`, `duration`, `layer`, `assetRef`, `transition`, `properties` (opacity, position, scale, text fields), and `automation` envelopes for property tweening.
  * `sync` directives to lock cues to camera presets or stream milestones (e.g., `awaitPreset("Front Entrance – Wide")`).
  * `fallbacks` block specifying safe-state overlays if assets missing or validation fails.
* Ensure schema documentation is published for VistterStudio team and versioned for backward compatibility.
* Support inline localization tokens (e.g., `{{locationName}}`) to be resolved by VistterStream before render.


## 7. Non-functional Requirements
* **Availability:** 99% appliance uptime when powered and networked; VistterStudio command channel uptime ≥ 98%.
* **Latency:** Camera preset execution + overlay activation < 2 seconds end-to-end under nominal conditions; command acknowledgement back to VistterStudio < 3 seconds.
* **Security:** Enforce encrypted credential storage, TLS for local UI (self-signed allowed), audit login attempts, and mutual authentication with VistterStudio control plane.
* **Performance:** Support 1080p60 ingest for up to three cameras concurrently on reference hardware; OCL renderer must composite at least three overlay layers at 60fps without dropped frames.
* **Scalability:** Architecture must allow clustering/fleet management in future without rework (stateless controller APIs, tenant-aware identifiers).
* **Reliability:** Survive network blips up to 60 seconds without manual intervention with queued command replay.
* **Maintainability:** Configuration represented as versioned schema with migration tooling and remote diff visibility within VistterStudio.

## 8. Dependencies & Assumptions
* Hardware provides hardware-accelerated decoding/encoding (Pi GPU, Intel Quick Sync) or falls back to software.
* VistterStudio exposes authenticated APIs or message broker endpoints for timeline directives, overlay manifests, overlay composition language payloads, segment packages, and status callbacks.
* Firewall policies allow outbound connectivity from the appliance to VistterStudio control endpoints and streaming destinations.
* Operators will have physical access to appliance for recovery procedures.
* VistterStudio implements minimal UI flows to issue pairing tokens, view appliance telemetry, and resend commands for testing.
* Streaming destinations such as YouTube Live, Facebook Live, Twitch, and custom RTMP endpoints accept outbound streams from VistterStream once credentials validated.

## 9. Release Considerations
* **MVP Success Criteria:** At least two camera types supported (one stationary, one PTZ); single timeline execution driven by VistterStudio via outbound channel; dual destination streaming; operator dashboard with health metrics and VistterStudio command history.
* **Future Enhancements:** Multi-appliance fleet management, AI-based anomaly detection, integration with advertising analytics, LTE/cellular fallback, deeper VistterStudio editing tools.
* **Open Questions:** Desired SLA for alert delivery? Should appliance support offline authoring when VistterStudio unreachable? How will licensing of third-party codecs be handled? What message broker will VistterStudio expose (managed MQTT vs. HTTPS push)? How often will OCL schema evolve and how will backward compatibility be maintained across appliance firmware versions?

## 10. Iteration Framework & Traceability
### 10.1 Document Status Checkpoints
| Area | Current Maturity | Next Validation Step | Owner |
| --- | --- | --- | --- |
| Product Goals & Scope | Draft aligned across platform leads | Review with GTM stakeholders to validate positioning | Product Manager |
| Use Case Catalog | Comprehensive v1 covering core appliance flows | Add edge cases for multi-appliance scenarios | Product & Engineering |
| Functional Requirements | Draft with integration emphasis | Map to API contract backlog and implementation tickets | Product & Tech Leads |
| Non-functional Requirements | Draft with performance/security targets | Benchmark against reference hardware prototypes | Engineering |

### 10.2 Use Case Coverage Matrix
| Use Case ID | Key Requirements | Notes |
| --- | --- | --- |
| UC-01, UC-02 | 6.1, 6.5 | Validate setup wizard copy and firewall guidance with pilot customers. |
| UC-03, UC-04 | 6.2, 6.5 | Confirm PTZ preset schema aligns with VistterStudio shot IDs. |
| UC-05, UC-08 | 6.1, 6.3, 6.7 | Stress-test command buffering during simulated outages. |
| UC-06, UC-11 | 6.4 | Capture credential rotation workflow for each streaming destination. |
| UC-07 | 6.3, 6.7 | Define overlay asset retention policy and cache eviction triggers. |
| UC-09 | 6.3, 6.6 | Document operator permissions for manual segment playback overrides. |
| UC-10 | 6.6 | Align incident escalation paths with support SLAs. |

### 10.3 Requirements Backlog for Next Revision
1. Define explicit telemetry event taxonomy shared with VistterStudio (success, warning, error codes).
2. Capture appliance-to-Studio credential rotation lifecycle (request, approval, revocation) and required UI surfaces.
3. Specify localization strategy for OCL tokens and operator UI (supported locales, fallback behavior).
4. Detail resiliency expectations for offline-only operation (maximum duration, required operator tooling).
5. Document compliance and privacy requirements for recorded streams and audit logs per region.

### 10.4 Decision Log References
* **DL-001:** Outbound-only command channel chosen to satisfy firewall constraints—revisit once reverse proxy option explored.
* **DL-002:** JSON-based OCL schema selected for human readability and Studio compatibility—evaluate binary formats after MVP.
* **DL-003:** Local web UI prioritized over native clients—reconsider after multi-appliance fleet management roadmap defined.
* **DL-004:** ⭐ **PTZ Preset System Implemented (Oct 2025)** - ONVIF port 8899 for Sunba cameras, preset-first architecture enabling single camera multi-angle shows, timeline cue integration complete.

---

## 11. PTZ Preset System Implementation (October 2025)

### 11.1 Overview
The PTZ Preset System is now **fully implemented** and operational, enabling sophisticated automated camera control for single-camera multi-angle productions.

### 11.2 Technical Implementation
**ONVIF Integration:**
- Library: `onvif-zeep` with lazy loading for graceful degradation
- Port Discovery: Sunba cameras use **port 8899** (non-standard, discovered via testing)
- Connection Pooling: Cached ONVIF sessions per camera
- Commands: `move_to_preset()`, `get_current_position()`, `set_preset()`

**Database Schema:**
```sql
presets table:
  - id, camera_id (FK), name
  - pan, tilt, zoom (float values from ONVIF)
  - created_at

streams table (updated):
  - preset_id (FK, nullable) -- Optional preset for stream

timeline_cues table (existing):
  - action_params JSON includes preset_id
```

**Execution Flow:**
1. User saves preset → Captures current camera position via ONVIF
2. User creates stream/timeline with preset → Stored in database
3. Stream/timeline starts → PTZ service moves camera to preset
4. System waits 3 seconds for mechanical movement
5. FFmpeg begins streaming from new position

### 11.3 User Workflows
**Workflow 1: Single-Camera Multi-Angle Stream**
- Camera: Sunba PTZ
- Presets: "Zoomed In", "Wide Shot"
- Stream 1: Sunba PTZ + "Zoomed In" preset → YouTube
- Stream 2: Sunba PTZ + "Wide Shot" preset → Facebook
- Result: Different views from same camera to different platforms

**Workflow 2: Automated Multi-Angle Timeline** ⭐ **BREAKTHROUGH**
- Timeline: "Multi-Angle Show"
- Cue 1: Sunba PTZ + "Wide Shot" (60s)
- Cue 2: Sunba PTZ + "Zoomed In" (30s)  
- Cue 3: Sunba PTZ + "Medium Shot" (45s)
- Loop: Enabled
- Result: Camera automatically repositions, creating professional multi-angle content from single PTZ camera

### 11.4 Key Achievements
✅ **Camera 1 Preset 1 → Camera 1 Preset 2** - Original user requirement fully satisfied
✅ ONVIF port auto-detection (8899 for Sunba, fallback to configured port)
✅ Preset Management UI with capture, test, delete operations
✅ Stream dialog conditional preset selector (only for PTZ cameras)
✅ Timeline editor expandable preset palette
✅ Database migration for preset support in streams
✅ Critical bug fix: Timeline save now persists tracks and cues

### 11.5 Known Limitations & Future Work
- **Manual Positioning**: Operator must position camera via camera's web UI before capturing preset (no joystick control in VistterStream yet)
- **Single ONVIF Profile**: Uses first media profile only (most cameras have one primary profile)
- **Hardcoded Port Fallback**: Port 8899 hardcoded for Sunba, should be configurable per camera
- **No Preset Import/Export**: VistterStudio integration pending for cloud preset library

### 11.6 Dependencies Added
- **onvif-zeep**: ONVIF/SOAP library for PTZ camera control
- **zeep**: SOAP client (dependency of onvif-zeep)
- **lxml**: XML parsing for ONVIF responses
