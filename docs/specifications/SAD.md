# VistterStream Software Architecture & Specification

**Document Status**: This SAD represents the original architectural vision (2025). See section 1.1 for implementation status.

## 1. Architectural Overview

### 1.1 Implementation Status

**ORIGINAL VISION:**
VistterStream designed as appliance with cloud integration to VistterStudio for remote control and timeline authoring.

**ACTUAL IMPLEMENTATION (November 2025):**
VistterStream built as **standalone streaming appliance** with all functionality local:

✅ **Implemented Architecture:**
- Single Docker container (FastAPI backend + React frontend)
- SQLite database with comprehensive schema
- FFmpeg-based streaming engine with hardware acceleration
- ONVIF PTZ control via onvif-zeep
- Local timeline editor and execution
- Local asset management and overlay composition
- YouTube Live API integration (OAuth, broadcast lifecycle)
- Stream health watchdog with auto-recovery
- Multi-architecture Docker builds (ARM64 + x86_64)

⏳ **Not Implemented (Future):**
- VistterStudio cloud integration
- Outbound command channel
- Fleet management messaging
- Remote control plane
- Cloud-based overlay synchronization

**Architecture Reality:** The system operates entirely locally. All "VistterStudio integration" references in this document represent future enhancement opportunities, not current dependencies.

### 1.2 System Architecture

VistterStream is delivered as a containerized appliance that runs on ARM64 (Raspberry Pi) and x86_64 (Mac, Intel NUC) hardware. The system orchestrates IP camera ingest, local timeline execution, overlay rendering, and multi-endpoint streaming. The solution favors modular services within a single container to simplify deployment, while keeping responsibilities explicit for future multi-service evolution.

```
+-----------------------+         +-----------------------+
|     Local Browser     |<------->|  Web/API Gateway      |
+-----------------------+         +-----------------------+
                                            |
                                            v
                              +---------------------------+
                              |   Control & Orchestration  |
                              +---------------------------+
                              /             |             \
                             v              v              v
                   +---------------+  +-------------+  +------------+
                   | Camera/Device |  | Stream      |  | Overlay    |
                   | Manager       |  | Engine      |  | Service    |
                   +---------------+  +-------------+  +------------+
                             \              |              /
                              v             v             v
                         +-------------------------------------+
                         | Persistence, Metrics, & Messaging   |
                         +-------------------------------------+
```

## 2. Quality Attribute Priorities
1. **Reliability:** Streams must recover automatically and timelines must execute even with transient failures.
2. **Observability:** Operators require actionable telemetry to maintain the appliance remotely.
3. **Security:** Local-only access with secure credential handling and auditable operations.
4. **Portability:** Same codebase runs across target hardware via Docker multi-arch builds.
5. **Extensibility:** Components are loosely coupled to allow future cloud orchestration or clustering.

## 3. Component Responsibilities
| Component | Responsibilities | Key Interfaces |
| --- | --- | --- |
| **Web/API Gateway** | Serves React UI, exposes REST/WebSocket APIs, handles authentication, enforces RBAC. | HTTPS, WebSocket, session cookies/JWT. |
| **Control & Orchestration Service** | Normalizes timelines and imported segments, coordinates camera moves, overlay activation, and stream commands. Maintains state machine per timeline or segment playback session. | Internal gRPC/REST calls to Camera Manager, Stream Engine, Overlay Service. |
| **Camera/Device Manager** | Discovers cameras (ONVIF), maintains connection pools, issues PTZ commands, verifies heartbeats. | ONVIF/RTSP clients, internal command bus, metrics emitter. |
| **Stream Engine** | Wraps FFmpeg workers, manages encoding profiles, handles retries, produces health metrics. | Process supervisor, IPC for command/control, file system for assets. |
| **Overlay Service** | Syncs assets from VistterStudio, validates manifests, compiles Overlay Composition Language (OCL) scripts, and provides rasterized/HTML overlays to Stream Engine. Caches overlay payloads referenced by imported segments for offline playback. | HTTPS downloads, OCL validator, scene runtime API, integrity checker. |
| **Persistence Layer** | SQLite database + encrypted secrets vault storing configuration, presets, credentials, audit logs. | ORM/Data access layer. |
| **Metrics & Messaging Layer** | Collects Prometheus-style metrics, event bus for local alerts, optional webhook dispatcher. | Metrics endpoint, webhook clients. |

## 4. Data Models & Storage
* **Configuration Database (SQLite):** 
  - **Cameras:** RTSP/ONVIF camera configurations, credentials (encrypted), status tracking
  - **StreamingDestinations:** Reusable destination configs (YouTube, Facebook, Twitch, Custom RTMP) with platform-specific settings and stream keys
  - **Streams:** Camera-to-destination mappings with encoding profiles, referencing both cameras and destinations
  - **Timelines:** Multi-track timeline definitions with camera cues and overlay instructions
  - **TimelineTracks & TimelineCues:** Granular timeline execution steps
  - **Presets:** PTZ camera position presets with pan/tilt/zoom coordinates, linked to cameras and referenced by streams/timelines
  - **Audit trails:** User actions and system events
* **Asset Cache (Filesystem):** Overlay images/videos, fallback slates, OCL scene caches, with version manifest for validation.
* **Overlay Composition Scripts:** Parsed/validated JSON persisted with schema version and compilation checksum for deterministic playback.
* **Telemetry Store (Time-Series):** Lightweight ring buffer (e.g., SQLite table or embedded TSDB) retaining 24–48 hours of metrics and events.
* **Secrets Management:** Credentials encrypted with appliance-specific key stored in secure enclave or OS keyring.

### 4.1 Streaming Destination Architecture
VistterStream implements a **destination-first architecture** where streaming targets (YouTube Live, Facebook Live, Twitch, Custom RTMP) are configured once and reused across both single-camera streams and multi-camera timelines:

```
┌─────────────────────────┐
│  StreamingDestinations  │  ← Configure once
│  (YouTube, FB, Twitch)  │
└────────┬────────────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌─────────┐  ┌──────────┐
│ Streams │  │ Timelines│  ← Reference destinations
└─────────┘  └──────────┘
```

**Benefits:**
- Stream keys configured once, reused everywhere
- Update destination → updates all dependent streams/timelines
- Track `last_used` timestamp per destination
- Platform-specific validation and presets

### 4.2 PTZ Preset System Architecture
VistterStream implements **ONVIF-based PTZ camera control** allowing operators to save camera positions as presets and reference them in streams and timelines for automated multi-angle content:

```
┌──────────────────────┐
│   PTZ Presets        │  ← Save positions once
│   (Zoomed In, Wide)  │
└─────────┬────────────┘
          │
     ┌────┴─────┐
     ↓          ↓
┌─────────┐  ┌──────────┐
│ Streams │  │ Timelines│  ← Reference presets
│         │  │  Cues    │
└─────────┘  └──────────┘
     ↓          ↓
┌──────────────────────┐
│  ONVIF PTZ Service   │  ← Move camera (port 8899)
│  (move_to_preset)    │
└──────────────────────┘
```

**Implementation Details:**
- **ONVIF Port Detection**: Sunba cameras use port 8899 (not standard 80)
- **Preset Storage**: Database stores pan/tilt/zoom coordinates per preset
- **Execution Sequence**: 
  1. Move camera to preset via ONVIF
  2. Wait 3 seconds for mechanical settling
  3. Start FFmpeg stream from new position
- **Graceful Degradation**: Stream continues even if PTZ move fails
- **Lazy Import**: ONVIF library loaded on-demand to avoid startup dependencies

**Use Cases Enabled:**
- Single PTZ camera → Multiple preset angles = Professional multi-camera show
- Timeline cues: "Camera 1 Preset 1 (Wide Shot)" → "Camera 1 Preset 2 (Close Up)" → Loop
- Preset reuse across multiple streams and timelines
- Live preset testing via "Go To" button in UI

## 5. Interface Contracts
* **REST API:** CRUD endpoints for cameras, presets, streams, overlays, system settings. JSON schema versioned and documented via OpenAPI.
* **WebSocket/API Events:** Push timeline updates, health notifications, alert streams to the UI and optionally VistterStudio.
* **Timeline Ingress:** Authenticated channel (HTTPS webhook or MQTT) from VistterStudio delivering timeline steps, overlay references, OCL payloads, segment packages, and scheduling metadata.
* **Segment Import Interface:** Offline-capable loader (USB/SMB/package upload) that validates signed segment bundles before registering them for manual playback.
* **Overlay Runtime API:** Internal API (`/overlay/runtime`) exposing commands to preload scenes, start/stop cues, adjust dynamic tokens, and report cue completion back to orchestration service.
* **Stream Command Bus:** Internal queue (e.g., Redis Streams or in-process dispatcher) issuing start/stop/restart commands to FFmpeg workers.

## 6. Runtime Scenarios
### 6.1 Camera Onboarding Flow
1. User submits camera configuration through Web UI.
2. API Gateway validates payload and stores draft record.
3. Camera Manager tests connectivity (RTSP handshake, credential auth).
4. On success, configuration committed and preview token generated; on failure, result surfaced to UI with diagnostics.

### 6.2 Timeline Execution Flow
1. Timeline instruction arrives from VistterStudio.
2. Orchestration Service locks associated resources (camera, stream).
3. Camera Manager executes PTZ move and confirms completion.
4. Overlay Service parses OCL payload, preloads required assets, and schedules cues relative to timeline clock.
5. Stream Engine activates encoding pipeline and routes to destinations.
6. Overlay Runtime triggers cue transitions (fade in/out, opacity adjustments, slide changes) and notifies orchestration service on completion.
7. Execution results and metrics (including overlay cue latency) are reported back via WebSocket and VistterStudio callback.

### 6.3 Overlay Orchestration Flow
1. VistterStudio publishes OCL document referencing asset bundle and schema version.
2. Overlay Service fetches document, validates against JSON schema, and stores compiled scene graph.
3. Control Service issues `prepareScene(sceneId)` prior to showtime; Overlay Service ensures textures, fonts, and animations staged.
4. When timeline clock hits cue start, Overlay Service issues render instructions to Stream Engine overlay compositor (e.g., HTML canvas, WebGL, or FFmpeg filter graph).
5. During playback, OCL automation curves adjust properties (opacity, scale) and event hooks emit telemetry (cueStarted, cueCompleted, cueFallback).
6. If validation or rendering fails, fallback overlay defined in OCL is applied and error surfaced to both local UI and VistterStudio.

### 6.4 Failure Recovery Flow
1. Stream Engine detects frame loss or FFmpeg exit code.
2. Control Service triggers retry with exponential backoff, optionally swapping to fallback feed.
3. Metrics layer records incident; alert dispatched to UI and configured webhooks.
4. After max retries, stream marked degraded, operator prompted for manual intervention.

### 6.5 Local Segment Playback Flow
1. Operator selects an imported segment from the Timelines view or quick action list.
2. Control Service loads associated timeline slice, overlay cues, and media references from persistence.
3. Overlay Service ensures assets are cached locally and validates integrity hashes; Stream Engine primes corresponding profiles.
4. Operator triggers manual play; Control Service starts the segment clock, issuing camera/overlay/stream commands in recorded order.
5. Completion events and any overrides are logged locally and, when connected, synchronized back to VistterStudio for audit.

## 7. Deployment View
* **Containerization:** Single Docker image with multi-stage build bundling frontend, backend, FFmpeg binaries, and headless renderer runtime for OCL scenes (e.g., Node/Chromium or GPU-accelerated compositor).
* **Process Model:** Supervisor process (e.g., uvicorn/gunicorn) runs API Gateway; background workers (async tasks or Celery-like) manage orchestration and FFmpeg lifecycles.
* **Configuration:** Environment variables for hardware-specific options, mount for persistent volume storing SQLite DB, cache, and logs.
* **Networking:** Expose HTTPS (443/8443) locally, optional SSH for support. Outbound firewall rules for streaming destinations and VistterStudio APIs.
* **Updates:** OTA update script downloads signed image, verifies checksum, performs rolling restart with rollback capability.

## 8. Security Considerations
* TLS termination on appliance with auto-generated cert; allow custom cert upload.
* Bcrypt/Argon2 password hashing, salted and stretched.
* Role-based authorization enforced per endpoint; audit log for configuration changes and login attempts.
* Secrets at rest encrypted with hardware-backed key when available.
* Optional IP allowlist for UI access; CSRF protection on state-changing endpoints.

## 9. Scalability & Extensibility
* Design allows horizontal scaling by externalizing persistence and message bus; controllers can become stateless microservices.
* Abstract camera and stream drivers to plug in additional vendors or protocols without touching orchestration core.
* Provide feature flags for experimental overlays or AI modules without redeploying base appliance.

## 10. Observability & Operations
* Metrics endpoint (Prometheus format) exposes system health, stream bitrate, frame drops, PTZ latency.
* Structured logging (JSON) with correlation IDs for timeline steps, segment executions, and overlay cues; logs shipped to local file and optional remote sink.
* Health checks: liveness for container runtime, readiness verifying DB connectivity and FFmpeg worker pool.
* Diagnostics bundle generator collects logs, configs, metrics snapshots for support tickets.

## 11. Compliance & Testing Strategy
* Unit tests for camera drivers, overlay manifest parser, and orchestration logic.
* Integration tests simulating timeline execution, manual segment playback, and mocked FFmpeg responses with OCL overlay playback.
* Hardware-in-the-loop regression tests for supported camera models and PTZ sequences.
* Security testing covering credential storage, API auth, TLS configuration, and OWASP top risks.
* Performance testing measuring CPU/memory under multi-stream load and failover scenarios.

## 12. Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Hardware limitations prevent smooth 1080p streaming. | Dropped frames, unusable stream. | Provide adaptive profiles, hardware acceleration detection, and fallback quality levels. |
| Overlay sync fails during network outage. | Advertisers miss placements. | Cache assets with manifest versions, allow manual override, provide stale asset warnings. |
| OCL directive unsupported on legacy firmware. | Overlay scenes render incorrectly during live event. | Implement schema version negotiation, feature flags, and compatibility matrix with automated regression tests per OCL version. |
| PTZ commands unreliable on certain vendors. | Timeline misses shot transitions. | Vendor-specific adapter layer with retry logic, fallback presets, certification process per camera. |
| Security breach via default credentials. | Unauthorized access to streams. | Mandatory password reset during setup, password strength checks, optional 2FA roadmap. |

## 13. Open Questions
* Which protocol (MQTT vs. Webhook) will VistterStudio standardize for timeline delivery?
* What is the required retention period for audit logs?
* Do we need built-in cellular failover support for remote locations?
* Will overlays render via HTML5, vector graphics, or GPU shaders, and how will we package the runtime for both ARM and x86 targets?
* How will VistterStream expose preview APIs so VistterStudio can validate OCL scenes before going live?

## 14. Traceability to Product Requirements
| PRD Requirement | Architectural Elements | Validation Approach |
| --- | --- | --- |
| 6.1 Platform Integration | Control & Orchestration, Web/API Gateway, Timeline Ingress | Contract tests against mocked VistterStudio endpoints; soak tests for reconnection handling. |
| 6.2 Camera & PTZ Management | Camera/Device Manager, Persistence Layer | Hardware-in-the-loop regression suite, PTZ command replay logs. |
| 6.3 Timeline & Overlay Execution | Control Service, Overlay Service, Stream Engine | Scenario simulations executing OCL payloads with telemetry capture. |
| 6.4 Streaming & Processing | Stream Engine, Metrics Layer | Load testing on reference hardware, failover drills. |
| 6.5 Local Web Experience | Web/API Gateway, Frontend SPA | UX acceptance tests, accessibility audits. |
| 6.6 Observability & Maintenance | Metrics & Messaging, Persistence | Synthetic alert pipelines, diagnostics bundle generation tests. |
| 6.7 Overlay Composition Language | Overlay Service, Asset Cache | Schema validation suite, golden-master rendering comparisons. |

## 15. Architecture Backlog & Next Steps
1. **Document Control Plane Contracts:** Produce OpenAPI/AsyncAPI specs for inbound commands and outbound telemetry, versioned alongside firmware releases.
2. **Define Reference Deployments:** Create reproducible Docker Compose stacks for ARM64 and x86_64 hardware to validate portability claims.
3. **Prototype Overlay Runtime:** Evaluate rendering options (Chromium headless vs. GPU compositor) and document performance benchmarks.
4. **Security Hardening Plan:** Detail threat model, penetration testing schedule, and certificate rotation strategy before pilot deployments.
5. **Operational Runbooks:** Draft incident response playbooks aligned with observability metrics and alerting pathways.
