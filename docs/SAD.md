# VistterStream Software Specification (Raspberry Pi + Mac Development)

## System Design

* Local appliance containerized with Docker.
* Provides a **web interface** for camera management, PTZ presets, and live previews.
* Ingests RTSP/RTMP feeds from IP cameras.
* Executes PTZ preset moves on supported cameras.
* Uses **FFmpeg** for ingest, overlays, and streaming outputs.
* Receives overlay/timeline instructions from **VistterStudio**.
* Designed to run consistently on **Mac (x86_64)** for dev and **Raspberry Pi (ARM64)** for production.

## Architecture Pattern

* **Single-container modular architecture**:

  * **Web UI** (React frontend + served statics).
  * **API Backend** (FastAPI or Node.js for REST APIs).
  * **Controller** (manages camera configs, PTZ, state).
  * **Stream Engine** (FFmpeg wrapper, controlled via API).
* Separation of concerns: UI ↔ API/Controller ↔ Stream Engine.

## State Management

* **SQLite** for persistent local storage.
* Stores camera configs, PTZ presets, user auth, destinations.
* Runtime state (active streams, health metrics) cached in memory.
* APIs expose state to UI + VistterStudio.

## Data Flow

1. User logs in via **Web UI** → adds/configures cameras.
2. Config stored in **SQLite**.
3. **Controller** launches FFmpeg streams via Stream Engine.
4. FFmpeg ingests, applies overlays, pushes to streaming destinations.
5. Health & status metrics reported back to Controller → UI.
6. VistterStudio sends timeline instructions → Controller switches camera/PTZ presets accordingly.

## Technical Stack

* **Frontend:** React + Tailwind.
* **Backend API:** FastAPI (Python) or Node.js/Express.
* **Database:** SQLite.
* **Streaming Engine:** FFmpeg (multi-arch build).
* **Containerization:** Docker with Buildx (multi-arch: x86_64 & ARM64).
* **Build Process:** CI/CD generates multi-platform images with manifest lists.

## Authentication Process

* Local username/password auth.
* Passwords hashed (bcrypt).
* Configurable via UI.
* Session cookies or JWT for web sessions (local-only).

## Route Design

* **/auth** → login, change password.
* **/cameras** → CRUD for cameras, connection test, health.
* **/presets** → CRUD for PTZ presets, move/test.
* **/streams** → start/stop streams, status.
* **/status** → system metrics (CPU, memory, camera health).
* **/overlays** → sync overlays from VistterStudio.

## API Design

* REST API with JSON.
* Example camera add:

```http
POST /cameras
{
  "name": "Reolink Front",
  "type": "PTZ",
  "protocol": "RTSP",
  "address": "rtsp://user:pass@192.168.1.50:554/stream1"
}
```

* Example PTZ preset:

```http
POST /cameras/{id}/presets
{ "name": "shot1", "pan": 0, "tilt": 30, "zoom": 2 }
```

## Database Design ERD

```mermaid
erDiagram
  USER {
    int id PK
    string username
    string password_hash
  }

  CAMERA {
    int id PK
    string name
    string type
    string protocol
    string address
    string username
    string password_enc
  }

  PRESET {
    int id PK
    int camera_id FK
    string name
    float pan
    float tilt
    float zoom
  }

  STREAM {
    int id PK
    int camera_id FK
    string destination
    string status
    datetime started_at
  }

  USER ||--o{ CAMERA : manages
  CAMERA ||--o{ PRESET : has
  CAMERA ||--o{ STREAM : streams
```

