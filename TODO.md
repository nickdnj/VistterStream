# VistterStream Delivery Backlog

This plan concentrates exclusively on the local VistterStream appliance while acknowledging how it will interoperate with the VistterStudio control plane. Use it to steer implementation work without losing track of the working functionality already in the repo.

## Current Appliance Capabilities
- FastAPI surface that already wires together authentication, camera, stream, preset, and status routers, giving us a running API shell to extend rather than rewrite.
- User management endpoints with JWT authentication and password hashing in place, establishing a baseline security model to harden.
- Camera management workflow covering CRUD operations, connection testing, snapshots, and PTZ preset execution through the service layer, providing a concrete integration surface for upcoming segment automation.
- Stream lifecycle endpoints that already encapsulate create/update/start/stop patterns for outputs, ready to be connected to the orchestration engine and encoder control modules.

## Roadmap Focus Areas

### 1. Appliance ↔️ VistterStudio Link
- [ ] Finalize control-channel protocol (WebSocket vs MQTT), authentication envelope, and heartbeat cadence as captured in `docs/VistterStudioIntegration.md`.
- [ ] Implement outbound session initiation from the appliance, including pairing token redemption and rotating credentials.
- [ ] Build command dispatcher + acknowledgement loop that maps Studio instructions to local subsystems (cameras, timelines, overlays) with audit logging.
- [ ] Surface telemetry and error reporting pathways back to VistterStudio for operator visibility.

### 2. Timeline & Segment Engine
- [ ] Design deterministic scheduler that merges imported VistterStudio segments with local manual triggers and resolves conflicts.
- [ ] Persist segment packages, metadata, and media assets with checksum validation and retention policies.
- [ ] Provide manual operator tooling to queue, preview, and force segments while preserving Studio command context.

### 3. Overlay Composition & Rendering
- [ ] Formalize Overlay Composition Language (OCL) schema, versioning, and validation (see integration guide for contract expectations).
- [ ] Implement asset ingestion, caching, and fallback handling for overlays delivered from VistterStudio APIs.
- [ ] Deliver compositor capable of applying opacity curves, transitions, and timeline-driven state changes at broadcast framerates.

### 4. Streaming & Encoding Pipeline
- [ ] Wrap FFmpeg/encoder control for multi-destination outputs with failover strategies and bitrate telemetry.
- [ ] Connect stream lifecycle API endpoints to the encoder control plane and VistterStudio-triggered state changes.
- [ ] Expose real-time metrics (program bitrate, dropped frames, health) to both the local UI and Studio telemetry feeds.

### 5. Local Operator Experience
- [ ] Implement authenticated dashboard aligning with UXD flows for health monitoring, activity logs, and manual overrides.
- [ ] Build guided setup wizards for camera onboarding, appliance configuration, and Studio pairing.
- [ ] Ensure accessibility, localization hooks, and responsive layouts consistent with design specifications.

### 6. Platform Reliability & Security
- [ ] Harden authentication/RBAC, secrets management, and encrypted storage for sensitive credentials.
- [ ] Add observability stack (metrics, logs, diagnostics bundles) with export hooks for support escalation.
- [ ] Establish automated testing, CI/CD, and release packaging suited to the appliance deployment model.

### 7. Documentation & Change Management
- [ ] Keep PRD/SAD/UXD synchronized with implementation decisions and update the integration guide as interfaces evolve.
- [ ] Produce operator manuals and support runbooks tailored to appliance installation and troubleshooting.
- [ ] Define release notes, versioning strategy, and rollback procedures for VistterStream firmware/images.

> **Next Step:** Sequence the control-channel implementation and segment/overlay ingestion work to unlock end-to-end Studio-driven playback while preserving manual control fallback.
