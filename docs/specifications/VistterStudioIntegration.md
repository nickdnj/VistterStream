# VistterStudio ↔️ VistterStream Integration Guide

This guide describes how the VistterStream appliance connects to VistterStudio, receives orchestration instructions, and reports telemetry while remaining operable behind customer firewalls. Treat it as the living contract shared by both teams.

## 1. Connectivity Overview
- **Initiation model:** VistterStream establishes outbound connections to VistterStudio to avoid inbound firewall openings. Primary channel candidates are secure WebSockets (wss) or MQTT over TLS. A lightweight REST bootstrap endpoint issues pairing tokens and the broker URL.
- **Pairing flow:**
  1. Operator signs into VistterStudio and requests a pairing token tied to the appliance serial number.
  2. Appliance admin enters the token locally; VistterStream exchanges it for long-lived credentials and device metadata.
  3. Stream establishes the persistent control channel, authenticating with mutual TLS and signed JWT session claims.
- **Resilience:** Clients maintain exponential backoff reconnect, replay unacknowledged commands, and expose connectivity state in local UI and telemetry.

## 2. Message Taxonomy
All control traffic shares a versioned envelope containing `message_id`, `correlation_id`, `timestamp`, `schema_version`, and `device_id`.

### 2.1 Commands from VistterStudio
| Command Type | Purpose | Key Fields |
| --- | --- | --- |
| `DEVICE_CONFIG` | Update appliance settings (network, time, firmware) | `config_patch`, `apply_after` |
| `CAMERA_ACTION` | Drive discovery, CRUD, or PTZ presets | `camera_id`, `action`, `payload` |
| `TIMELINE_LOAD` | Send compiled segment timelines for local caching | `timeline_id`, `segments[]`, `assets_manifest` |
| `TIMELINE_EXECUTE` | Trigger play/pause/seek for loaded timelines | `timeline_id`, `cue_id`, `execution_mode` |
| `OVERLAY_UPDATE` | Push overlay composition packages or quick edits | `overlay_id`, `ocl_package_uri`, `checksum` |
| `STREAM_CONTROL` | Start/stop outputs or adjust encoder settings | `stream_id`, `command`, `parameters` |

### 2.2 Responses & Telemetry from VistterStream
| Message Type | Purpose | Key Fields |
| --- | --- | --- |
| `ACK` | Confirm command receipt and validation | `message_id`, `status`, `error` |
| `PROGRESS` | Report long-running execution updates | `message_id`, `percent_complete`, `state` |
| `EVENT` | Notify Studio about local operator overrides, faults, or timeline state changes | `event_type`, `severity`, `context` |
| `METRICS` | Deliver periodic health data | `cpu`, `gpu`, `network`, `stream_bitrate[]` |

## 3. Overlay Composition Language (OCL)
VistterStudio compiles overlay scenes into OCL payloads that VistterStream validates and renders.
- **Structure:** `scene` → `layers[]` → `tracks[]` with time-based keyframes. Each property (opacity, position, scale) supports easing curves.
- **Assets:** Payload references media via signed URLs and includes checksums. VistterStream caches assets locally and confirms integrity before playback.
- **Timelines:** OCL clips align to segment timelines. Commands may reference `cue_points` to coordinate with camera presets or audio marks.
- **Versioning:** Envelope includes `ocl_version`; appliances advertise supported versions during pairing. Backward-compatible changes require feature flags.

## 4. Segment & Timeline Lifecycle
1. **Authoring:** Studio timelines bundle camera presets, overlays, and audio cues into segments.
2. **Packaging:** Studio exports `TIMELINE_LOAD` with manifest, OCL payloads, and asset descriptors.
3. **Ingestion:** VistterStream validates schemas, downloads assets, and stores them under the segment library with integrity metadata.
4. **Execution:** `TIMELINE_EXECUTE` or local operator actions schedule segments through the appliance timeline engine. Conflicts resolve via priority rules (Studio commands > scheduled timelines > manual overrides, unless emergency stop).
5. **Feedback:** Execution progress, warnings, and completion events return via telemetry messages.

## 5. Security & Compliance
- Enforce TLS 1.2+ with pinned certificates. Rotate credentials via Studio-issued refresh commands.
- Sign all commands and responses; reject unsigned or replayed messages using nonce tracking.
- Keep minimal personally identifiable information in transit. Operational logs remain on the appliance unless explicitly exported.

## 6. Testing & Validation Strategy
- **Contract tests:** Shared schema repository with JSON Schema or Protobuf definitions and golden samples.
- **Integration sandbox:** Cloud-hosted broker and mock Studio service for end-to-end validation against appliance builds.
- **Failover drills:** Simulate connectivity drops, token expiration, and conflicting commands to validate buffering and reconciliation logic.

## 7. Change Management
- Version control this guide alongside the codebase. Changes require review from both VistterStream and VistterStudio leads.
- Maintain a compatibility matrix mapping Studio releases to minimum appliance firmware versions.
- Document deprecation timelines for command or schema changes and provide migration tooling where necessary.
