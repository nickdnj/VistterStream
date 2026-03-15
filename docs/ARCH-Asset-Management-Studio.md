# Software Architecture: VistterStream Asset Management Studio

**Version:** 1.0
**Last Updated:** 2026-03-15
**Author:** Nick DeMarco with AI Assistance
**Status:** Draft
**PRD Reference:** [PRD-Asset-Management-Studio.md](./PRD-Asset-Management-Studio.md)

---

## 1. Executive Summary

### 1.1 System Overview

The Asset Management Studio transforms VistterStream's existing five-type asset CRUD system into a full creative workflow with three pillars: a browsable Overlay Template Catalog, an in-browser Canvas Editor (Fabric.js), and comprehensive Asset Lifecycle features (versioning, scheduling, grouping, analytics). All new functionality is additive to the existing FastAPI/React/SQLite/FFmpeg stack -- no new infrastructure, no new databases, no new container services.

The architecture is designed around two core principles. First, the canvas editor produces static image assets (PNGs) that feed into the existing FFmpeg overlay compositing pipeline unchanged -- the studio is a "design-time" tool, not a "stream-time" rendering engine. Second, all new database tables and API endpoints are backward-compatible extensions; the existing Asset model, timeline system, and overlay preview panel continue to work without modification.

### 1.2 Key Architectural Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| ADR-1 | Canvas library | Fabric.js v6 | MIT license, mature serialization (toJSON/loadFromJSON), built-in object model, active maintenance, 28k GitHub stars |
| ADR-2 | Database | SQLite (unchanged) | Low user count (1-5 concurrent), WAL mode sufficient, no operational overhead |
| ADR-3 | Template storage | JSON definitions in DB + bundled preview PNGs in Docker image | Templates ship with the container; no external download. Config schemas stored as JSON columns |
| ADR-4 | Autosave strategy | Dual: localStorage (instant) + server (durable, 60s interval) | localStorage prevents data loss on browser crash; server save prevents loss across devices |
| ADR-5 | Weather overlays (Phase 1) | Pre-rendered images via TempestWeather API | Existing `api_image` pipeline works today; defers `data_bound` text rendering to Phase 2 |
| ADR-6 | Animations | Post-MVP | Removes FFmpeg filter graph complexity from initial scope; overlays are static composites |
| ADR-7 | Font system | Upload API + Google Fonts API with local caching | Maximum flexibility; fonts cached to `/data/fonts/` volume for FFmpeg `drawtext` access |
| ADR-8 | Color picker | react-colorful | 2KB gzipped, zero dependencies, React 19 compatible, accessible |

### 1.3 Technology Stack Summary

| Layer | Technology | Status |
|-------|------------|--------|
| Frontend | React 19, TypeScript, Tailwind CSS | Existing |
| Canvas Editor | Fabric.js v6 | **New** |
| Color Picker | react-colorful | **New** |
| Backend | Python 3.11, FastAPI 0.117, SQLAlchemy 2.0, Pydantic 2.11 | Existing |
| JSON Path | jsonpath-ng | **New** (Phase 2) |
| Database | SQLite with WAL mode | Existing |
| Migrations | Alembic 1.13 | Existing |
| Image Processing | Pillow 12.1 | Existing |
| Stream Engine | FFmpeg (filter_complex overlay compositing) | Existing |
| Deployment | Docker (multi-stage Python 3.11-slim-bookworm) | Existing |

---

## 2. System Context

### 2.1 Context Diagram

```
+------------------+          +----------------------------+
|                  |  HTTPS   |   VistterStream Appliance  |
|   Browser        |--------->|   (Docker on Ubuntu)       |
|   (Canvas Editor,|<---------|                            |
|    Template UI,  |          |  +--------+  +---------+   |
|    Asset Mgmt)   |          |  |FastAPI |  | React   |   |
|                  |          |  |Backend |  | Frontend|   |
+------------------+          |  +---+----+  +----+----+   |
                              |      |            |        |
                              |  +---v------------v----+   |
                              |  |     SQLite DB        |   |
                              |  +---------------------+   |
                              |      |                     |
                              |  +---v-----------------+   |
                              |  | FFmpeg Pipeline      |   |
                              |  | (overlay compositing)|   |
                              |  +---+-----------------+   |
                              |      |                     |
                              +------+---------------------+
                                     |
                              +------v-----+    +-----------+
                              | YouTube/   |    | TempestWx |
                              | Facebook/  |    | API       |
                              | Twitch     |    | :8036     |
                              +------------+    +-----------+
```

### 2.2 External Systems

| System | Purpose | Integration Type | Existing? |
|--------|---------|-----------------|-----------|
| TempestWeather API | Weather data + pre-rendered overlay images | HTTP REST (host.docker.internal:8036) | Yes |
| NOAA Tides API | Tide chart data | HTTP REST (api.tidesandcurrents.noaa.gov) | **New** |
| Google Fonts API | Font catalog and downloads | HTTP REST (fonts.googleapis.com) | **New** |
| YouTube/Facebook/Twitch | Stream destinations | RTMP push | Yes |
| FFmpeg | Overlay compositing into live stream | Process spawning | Yes |

### 2.3 Users and Actors

| Actor | Description | Key Interactions |
|-------|-------------|-----------------|
| Stream Operator | Primary user, manages overlays and streams | All features |
| Designer (Phase 3) | Creates assets, cannot manage streams | Canvas editor, templates, asset CRUD |
| Viewer (Phase 3) | Read-only dashboard and analytics | View analytics, view asset library |

---

## 3. Component Architecture

### 3.1 Component Diagram

```
+================================================================+
|                        FRONTEND (React)                         |
|                                                                 |
|  +------------------+  +------------------+  +---------------+  |
|  | Template Catalog  |  | Canvas Editor    |  | Asset Library |  |
|  | - Browser/Grid    |  | - Fabric.js      |  | - Grid View   |  |
|  | - Config Wizards  |  | - Tool Panels    |  | - Groups      |  |
|  | - Live Preview    |  | - Layer Panel    |  | - Scheduling  |  |
|  | - Import/Export   |  | - Properties     |  | - Versions    |  |
|  +--------+---------+  | - Export to PNG   |  | - Analytics   |  |
|           |             +--------+---------+  +-------+-------+  |
|           |                      |                    |          |
|  +--------v----------------------v--------------------v-------+  |
|  |              Shared Services Layer                         |  |
|  |  - api.ts (axios)  - AutosaveService  - FontService       |  |
|  |  - AssetService    - CanvasSerializer  - ToastNotifications|  |
|  +----------------------------+-------------------------------+  |
+================================|=================================+
                                 | HTTP REST (JSON)
+================================|=================================+
|                        BACKEND (FastAPI)                        |
|                                                                 |
|  +------------------+  +------------------+  +---------------+  |
|  | Template Router   |  | Canvas Router    |  | Asset Router  |  |
|  | /api/templates/*  |  | /api/canvas-*    |  | /api/assets/* |  |
|  +--------+---------+  +--------+---------+  +-------+-------+  |
|           |                      |                    |          |
|  +--------v----------------------v--------------------v-------+  |
|  |              Service Layer                                 |  |
|  |  - TemplateService    - CanvasProjectService               |  |
|  |  - FontService        - AssetVersionService                |  |
|  |  - AssetScheduleService  - AssetAnalyticsService           |  |
|  |  - AssetGroupService  - ImportExportService                |  |
|  +----------------------------+-------------------------------+  |
|                               |                                  |
|  +----------------------------v-------------------------------+  |
|  |              Data Layer (SQLAlchemy ORM)                   |  |
|  |  Existing: Asset, Timeline, TimelineCue, TimelineTrack     |  |
|  |  New: OverlayTemplate, TemplateInstance, CanvasProject,    |  |
|  |       AssetVersion, AssetGroup, AssetGroupMember,          |  |
|  |       AssetSchedule, AssetDisplayLog, Font                 |  |
|  +----------------------------+-------------------------------+  |
|                               |                                  |
|              +----------------v-----------------+                |
|              |        SQLite (WAL mode)         |                |
|              |   /data/vistterstream.db          |                |
|              +----------------------------------+                |
+================================================================+
```

### 3.2 Component Descriptions

#### 3.2.1 Template Catalog (Frontend)

- **Purpose:** Browsable catalog of pre-built overlay templates with category filtering and search
- **Responsibilities:**
  - Render template cards with preview thumbnails
  - Filter by category (Weather, Marine, Time/Date, Sponsor/Ad, Lower Thirds, Social Media)
  - Keyword search across template names and descriptions
  - Launch configuration wizards per template type
  - Handle template import/export file operations
- **Technology:** React component, Tailwind CSS card grid
- **Dependencies:** Template Router (backend), Asset Router (for creating template instances)

#### 3.2.2 Template Configuration Wizards (Frontend)

- **Purpose:** Step-by-step guided configuration for each template type
- **Responsibilities:**
  - Render template-specific form fields (required/optional with defaults)
  - Real-time preview of configured overlay using live data
  - Input validation (station ID format, URL validity, etc.)
  - "Test" button for data source connectivity verification
  - Submit to create a configured template instance and corresponding Asset record
- **Technology:** React multi-step form components
- **Dependencies:** Template Router, Asset Router, TempestWeather API (for weather previews)

#### 3.2.3 Canvas Editor (Frontend)

- **Purpose:** In-browser WYSIWYG overlay designer using HTML5 Canvas
- **Responsibilities:**
  - Initialize Fabric.js canvas at stream resolution (default 1920x1080, transparent background)
  - Provide drawing tools: Select, Text, Rectangle, Circle, Line, Image Import
  - Object manipulation: drag, resize, rotate, z-order, group/ungroup
  - Properties panel: font, color, opacity, stroke, shadow, alignment
  - Layer panel: z-order list with visibility toggle, lock, rename, reorder
  - Alignment: snap-to-grid, smart guides, alignment/distribution buttons, rulers
  - Undo/redo stack (50 levels) using Fabric.js state snapshots
  - Autosave: localStorage every 10 seconds, server every 60 seconds
  - Export: render to PNG via `canvas.toDataURL()`, upload as new asset
  - Serialize/deserialize via Fabric.js `toJSON()`/`loadFromJSON()`
- **Technology:** Fabric.js v6, react-colorful, custom React wrapper components
- **Dependencies:** Canvas Router (backend), Asset Router (for export), Font Service

#### 3.2.4 Asset Library (Frontend, Enhanced)

- **Purpose:** Grid view of all assets with new filtering, grouping, and lifecycle features
- **Responsibilities:**
  - Existing: card grid of assets with preview, edit, delete, duplicate, test
  - New: filter by type, group, search term, schedule status
  - New: asset group management (create, add/remove members)
  - New: version history panel (list versions, preview, revert)
  - New: schedule configuration (time-of-day, day-of-week, rotation)
  - New: analytics view (display time, impression counts)
- **Technology:** React components, Tailwind CSS
- **Dependencies:** Asset Router (backend)

#### 3.2.5 Template Router (Backend)

- **Purpose:** API endpoints for template catalog and template instances
- **Responsibilities:**
  - `GET /api/templates` -- list catalog templates with category filter
  - `GET /api/templates/{id}` -- template detail with config schema
  - `POST /api/templates/instances` -- create configured instance (runs wizard config, creates Asset)
  - `PUT /api/templates/instances/{id}` -- update instance configuration
  - `POST /api/templates/export/{id}` -- package template as `.vst-template` ZIP
  - `POST /api/templates/import` -- import `.vst-template` package
- **Technology:** FastAPI router, Pydantic schemas
- **Dependencies:** TemplateService, Asset model, database session

#### 3.2.6 Canvas Router (Backend)

- **Purpose:** API endpoints for canvas project CRUD and export
- **Responsibilities:**
  - `POST /api/canvas-projects` -- create new project
  - `GET /api/canvas-projects` -- list projects with thumbnails
  - `GET /api/canvas-projects/{id}` -- load project (returns Fabric.js JSON)
  - `PUT /api/canvas-projects/{id}` -- save project (manual and autosave)
  - `DELETE /api/canvas-projects/{id}` -- soft delete
  - `POST /api/canvas-projects/{id}/export` -- render PNG, create asset
  - `POST /api/canvas-projects/{id}/duplicate` -- clone project
- **Technology:** FastAPI router, Pydantic schemas
- **Dependencies:** CanvasProjectService, Asset Router (for export), Pillow (thumbnails)

#### 3.2.7 Asset Router (Backend, Extended)

- **Purpose:** Extended asset CRUD with versioning, scheduling, analytics, and groups
- **Responsibilities:**
  - Existing endpoints unchanged (backward compatible)
  - New: `GET /api/assets/{id}/versions` -- version history
  - New: `POST /api/assets/{id}/revert/{version}` -- revert to version
  - New: `GET/POST/DELETE /api/assets/{id}/schedule` -- schedule management
  - New: `GET /api/assets/{id}/analytics` -- display analytics
  - New: `GET/POST/PUT/DELETE /api/asset-groups/*` -- group management
  - Extended: asset list supports `?type=`, `?group_id=`, `?search=`, `?has_schedule=` filters
  - Extended: asset create/update accepts `data_bound` and `canvas_composite` types
- **Technology:** FastAPI router extensions
- **Dependencies:** AssetVersionService, AssetScheduleService, AssetAnalyticsService, AssetGroupService

#### 3.2.8 Font Router (Backend)

- **Purpose:** Font management API for upload and Google Fonts integration
- **Responsibilities:**
  - `GET /api/fonts` -- list available fonts (system + uploaded + Google cached)
  - `POST /api/fonts/upload` -- upload custom font file (.ttf, .otf, .woff2)
  - `GET /api/fonts/google` -- search Google Fonts catalog
  - `POST /api/fonts/google/install` -- download and cache a Google Font
  - `DELETE /api/fonts/{id}` -- remove uploaded font
  - Serve font files for both browser (CSS @font-face) and FFmpeg (drawtext filter)
- **Technology:** FastAPI router, httpx for Google Fonts API
- **Dependencies:** FontService, file system `/data/fonts/`

---

## 4. Data Architecture

### 4.1 Data Model -- New Tables

```
+-------------------+       +---------------------+
| overlay_templates  |       | template_instances   |
+-------------------+       +---------------------+
| id (PK)           |<------| id (PK)              |
| name              |       | template_id (FK)     |
| category          |       | asset_id (FK) ------>| assets.id
| description       |       | config_values (JSON) |
| config_schema JSON |       | created_at           |
| default_config JSON|       | updated_at           |
| preview_path      |       +---------------------+
| version           |
| is_bundled        |       +---------------------+
| is_active         |       | canvas_projects      |
| created_at        |       +---------------------+
+-------------------+       | id (PK)              |
                            | name                 |
+-------------------+       | description          |
| asset_versions    |       | canvas_json (TEXT)   |
+-------------------+       | thumbnail_path       |
| id (PK)           |       | width                |
| asset_id (FK) --->|       | height               |
| version_number    |       | created_by (FK)      |
| file_path         |       | is_active            |
| metadata_snapshot |       | created_at           |
|   (JSON)          |       | updated_at           |
| thumbnail_path    |       +---------------------+
| created_at        |
| created_by (FK)   |       +---------------------+
| change_description|       | asset_schedules      |
+-------------------+       +---------------------+
                            | id (PK)              |
+-------------------+       | asset_id (FK) ------>| assets.id
| asset_groups      |       | schedule_type        |
+-------------------+       | config (JSON)        |
| id (PK)           |       | is_enabled           |
| name              |       | created_at           |
| description       |       | updated_at           |
| is_active         |       +---------------------+
| created_at        |
| updated_at        |       +---------------------+
+-------------------+       | asset_display_log    |
        |                   +---------------------+
        v                   | id (PK)              |
+---------------------+     | asset_id (FK)        |
| asset_group_members  |     | execution_id (FK)    |
+---------------------+     | started_at           |
| id (PK)              |     | ended_at             |
| group_id (FK)        |     | duration_seconds     |
| asset_id (FK, null)  |     +---------------------+
| child_group_id       |
|   (FK, nullable)     |     +---------------------+
| display_order        |     | fonts                |
+---------------------+     +---------------------+
                            | id (PK)              |
                            | name                 |
                            | family               |
                            | source (system/      |
                            |   upload/google)     |
                            | file_path            |
                            | weight               |
                            | style                |
                            | is_active            |
                            | created_at           |
                            +---------------------+
```

### 4.2 Existing Table Modifications

| Table | Column Addition | Type | Default | Purpose |
|-------|----------------|------|---------|---------|
| `assets` | `template_instance_id` | Integer FK, nullable | NULL | Links to template_instances.id |
| `assets` | `data_binding_config` | JSON, nullable | NULL | Phase 2: data binding specification |
| `assets` | `canvas_project_id` | Integer FK, nullable | NULL | Links to source canvas project |
| `assets` | `type` enum extension | String | -- | Add `data_bound`, `canvas_composite` values |
| `users` | `role` | String | `"admin"` | Phase 3: RBAC (admin/designer/operator/viewer) |

All additions are nullable or have backward-compatible defaults, so existing rows are unaffected.

### 4.3 Data Storage Decisions

| Data | Storage | Rationale |
|------|---------|-----------|
| Template definitions | `overlay_templates` table (JSON columns) | Config schemas are structured JSON; DB queries for catalog browsing |
| Template preview images | File system `/app/templates/catalog/` (bundled in Docker image) | Static assets, bundled at build time |
| Canvas project data | `canvas_projects.canvas_json` (TEXT column) | Fabric.js JSON serialization; typically 10-200KB per project |
| Canvas thumbnails | File system `/data/uploads/canvas/` | Generated PNG thumbnails, served via static files |
| Asset file versions | File system `/data/uploads/assets/versions/{asset_id}/{version}/` | Versioned copies of uploaded files |
| Font files | File system `/data/fonts/` | Shared between browser (served via HTTP) and FFmpeg (filesystem path) |
| Analytics logs | `asset_display_log` table | Append-only log; computed aggregates via SQL |
| Schedule configs | `asset_schedules.config` (JSON column) | Flexible schedule types (time_window, rotation, always_on) |

### 4.4 Data Flow -- Template Instantiation

```
User selects template in catalog
        |
        v
Frontend loads template config_schema from GET /api/templates/{id}
        |
        v
Wizard renders form fields from config_schema
        |
        v
User fills in fields (e.g., station_id, theme, position)
        |
        v
Frontend calls POST /api/templates/instances
  with { template_id, config_values: {...} }
        |
        v
Backend TemplateService:
  1. Validates config_values against config_schema
  2. Merges config_values with default_config
  3. Generates asset properties from merged config:
     - For weather: constructs api_url for TempestWeather
     - For lower third: no external URL, uses canvas_json
     - For time/date: no external URL, uses data_binding_config
  4. Creates Asset record (type=api_image or canvas_composite)
  5. Creates TemplateInstance record (links template -> asset)
  6. Returns asset_id
        |
        v
Frontend navigates to Asset Library (new asset visible)
        |
        v
User adds asset to Timeline overlay track (existing workflow)
```

### 4.5 Data Flow -- Canvas Editor Save and Export

```
User edits canvas in Fabric.js editor
        |
        +---> Every 10s: serialize to localStorage (crash recovery)
        |
        +---> Every 60s: PUT /api/canvas-projects/{id}
        |       with { canvas_json, thumbnail (base64) }
        |       Backend saves JSON to DB, thumbnail to filesystem
        |
        v
User clicks "Export as Asset"
        |
        v
Frontend: canvas.toDataURL('image/png') -> blob
        |
        v
Frontend: POST /api/canvas-projects/{id}/export
  with { canvas_png (multipart), name, description }
        |
        v
Backend CanvasProjectService:
  1. Saves PNG to /data/uploads/assets/{uuid}.png
  2. Creates Asset record:
     - type = "canvas_composite"
     - file_path = "/uploads/assets/{uuid}.png"
     - canvas_project_id = project.id
     - width/height from project dimensions
  3. Returns new asset_id
        |
        v
Asset now available in library + timeline overlay system
FFmpeg composites it via existing overlay filter graph
```

### 4.6 Data Flow -- Asset Versioning

```
User edits asset (any field change or file re-upload)
        |
        v
PUT /api/assets/{id} hits AssetVersionService pre-save hook:
  1. Snapshot current asset state to metadata_snapshot JSON
  2. If file-based: copy current file to
     /data/uploads/assets/versions/{asset_id}/{version_number}/
  3. Create AssetVersion record
  4. If version count > 50 for this asset: purge oldest
        |
        v
Apply the actual update to the Asset record
        |
        v
User later opens version history:
  GET /api/assets/{id}/versions
  -> Returns list of versions with timestamps and change descriptions
        |
        v
User clicks "Revert to version 3":
  POST /api/assets/{id}/revert/3
  1. Load metadata_snapshot from version 3
  2. If file-based: copy versioned file back to active path
  3. Apply snapshot to Asset record (creates NEW version = revert)
```

### 4.7 Data Retention

| Data | Retention | Archival Strategy |
|------|-----------|-------------------|
| Asset records | Indefinite (soft delete) | `is_active = False` hides from UI |
| Canvas projects | Indefinite (soft delete) | `is_active = False` hides from UI |
| Asset versions | 50 per asset | Oldest auto-purged on new version creation |
| Asset display logs | 90 days | Background cleanup task deletes old entries |
| Font files | Indefinite | Manual deletion via API |
| Template preview PNGs | Indefinite (bundled) | Updated with Docker image rebuilds |

---

## 5. API Design

### 5.1 API Style

REST over HTTP, consistent with the existing VistterStream API. All new endpoints follow existing patterns:
- Prefix: `/api/`
- Authentication: Bearer JWT via `get_current_user` dependency
- Request/response: JSON (Pydantic schemas)
- File uploads: multipart/form-data
- Errors: structured JSON `{"detail": "..."}`

### 5.2 Authentication and Authorization

- **Authentication:** JWT tokens (existing), issued via `POST /api/auth/login`
- **Authorization (Phase 1):** All authenticated users have full access (current behavior)
- **Authorization (Phase 3):** Role-based access control
  - Admin: full access
  - Designer: create/edit/delete assets, canvas projects, templates
  - Operator: manage streams, add existing assets to timelines
  - Viewer: read-only dashboards and analytics

### 5.3 Key Endpoints

#### Templates

| Method | Path | Description | Phase |
|--------|------|-------------|-------|
| GET | `/api/templates` | List catalog templates | 1 |
| GET | `/api/templates/{id}` | Template detail + config_schema | 1 |
| POST | `/api/templates/instances` | Create configured template instance | 1 |
| GET | `/api/templates/instances` | List configured instances | 1 |
| PUT | `/api/templates/instances/{id}` | Update instance config | 1 |
| DELETE | `/api/templates/instances/{id}` | Delete instance | 1 |
| POST | `/api/templates/export/{id}` | Export as .vst-template | 3 |
| POST | `/api/templates/import` | Import .vst-template | 3 |

#### Canvas Projects

| Method | Path | Description | Phase |
|--------|------|-------------|-------|
| GET | `/api/canvas-projects` | List projects (with thumbnails) | 1 |
| POST | `/api/canvas-projects` | Create new project | 1 |
| GET | `/api/canvas-projects/{id}` | Load project JSON | 1 |
| PUT | `/api/canvas-projects/{id}` | Save project (autosave + manual) | 1 |
| DELETE | `/api/canvas-projects/{id}` | Soft delete | 1 |
| POST | `/api/canvas-projects/{id}/export` | Export as PNG asset | 1 |
| POST | `/api/canvas-projects/{id}/duplicate` | Duplicate project | 1 |

#### Fonts

| Method | Path | Description | Phase |
|--------|------|-------------|-------|
| GET | `/api/fonts` | List available fonts | 1 |
| POST | `/api/fonts/upload` | Upload custom font | 1 |
| GET | `/api/fonts/google` | Search Google Fonts catalog | 1 |
| POST | `/api/fonts/google/install` | Download + cache Google Font | 1 |
| DELETE | `/api/fonts/{id}` | Remove uploaded font | 1 |

#### Asset Extensions

| Method | Path | Description | Phase |
|--------|------|-------------|-------|
| GET | `/api/assets/{id}/versions` | Version history | 2 |
| POST | `/api/assets/{id}/revert/{version}` | Revert to version | 2 |
| GET | `/api/assets/{id}/analytics` | Display analytics | 3 |
| GET | `/api/assets/analytics/summary` | Analytics summary | 3 |
| POST | `/api/assets/{id}/schedule` | Set schedule | 2 |
| GET | `/api/assets/{id}/schedule` | Get schedule | 2 |
| DELETE | `/api/assets/{id}/schedule` | Remove schedule | 2 |

#### Asset Groups

| Method | Path | Description | Phase |
|--------|------|-------------|-------|
| GET | `/api/asset-groups` | List groups | 3 |
| POST | `/api/asset-groups` | Create group | 3 |
| GET | `/api/asset-groups/{id}` | Group with members | 3 |
| PUT | `/api/asset-groups/{id}` | Update group | 3 |
| DELETE | `/api/asset-groups/{id}` | Delete group | 3 |
| POST | `/api/asset-groups/{id}/members` | Add member | 3 |
| DELETE | `/api/asset-groups/{id}/members/{mid}` | Remove member | 3 |

### 5.4 Error Handling

All errors follow the existing FastAPI HTTPException pattern:

```json
{
  "detail": "Canvas project not found"
}
```

Structured validation errors (Pydantic):

```json
{
  "detail": [
    {
      "loc": ["body", "config_values", "station_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 5.5 Rate Limiting

| Endpoint Group | Limit | Rationale |
|---------------|-------|-----------|
| Asset upload | 100/min | Prevent storage abuse |
| Canvas autosave | 60/min | One save per second max |
| Template instantiation | 30/min | Prevent mass creation |
| Font upload | 10/min | Large files, limited storage |
| All other endpoints | Existing global limits | Unchanged |

---

## 6. Frontend Architecture

### 6.1 Component Hierarchy

```
App.tsx
+-- Layout.tsx (sidebar navigation -- add "Assets" subnav)
    +-- /assets -> AssetStudio.tsx (NEW - container for all asset features)
    |   +-- AssetLibrary.tsx (enhanced existing AssetManagement.tsx)
    |   +-- CanvasEditorPage.tsx (NEW - full-page canvas editor)
    |   +-- TemplateCatalog.tsx (NEW - template browser)
    |   +-- TemplateWizard.tsx (NEW - per-template config)
    |
    +-- /assets/editor/:id -> CanvasEditorPage.tsx (edit existing project)
    +-- /assets/templates -> TemplateCatalog.tsx
```

### 6.2 Canvas Editor Component Architecture

```
CanvasEditorPage.tsx
+-- EditorToolbar.tsx (top: project name, save, export, undo/redo, zoom)
+-- CanvasWorkspace.tsx (center: Fabric.js canvas with zoom/pan)
|   +-- FabricCanvas.tsx (Fabric.js wrapper, event handling)
|   +-- AlignmentGuides.tsx (smart guide rendering)
|   +-- Rulers.tsx (pixel rulers along edges)
|   +-- SafeZoneOverlay.tsx (broadcast safe zone indicators)
|
+-- ToolPanel.tsx (left sidebar: drawing tools)
|   +-- SelectTool, TextTool, RectTool, CircleTool, LineTool, ImageTool
|
+-- PropertiesPanel.tsx (right sidebar: selected object properties)
|   +-- TextProperties.tsx (font, size, color, alignment, shadow, stroke)
|   +-- ShapeProperties.tsx (fill, stroke, corner radius, opacity)
|   +-- ImageProperties.tsx (crop, opacity, filters)
|   +-- PositionProperties.tsx (x, y, width, height, rotation, lock aspect)
|
+-- LayerPanel.tsx (right sidebar, collapsible: z-order management)
|   +-- LayerItem.tsx (visibility toggle, lock, rename, drag-to-reorder)
|
+-- FontPicker.tsx (shared: font selection with preview)
+-- ColorPicker.tsx (shared: react-colorful wrapper with hex input + presets)
```

### 6.3 State Management

The canvas editor uses a combination of Fabric.js internal state and React state:

| State | Owner | Persistence |
|-------|-------|-------------|
| Canvas objects (layers, positions, styles) | Fabric.js canvas instance | `canvas.toJSON()` serialization |
| Selected object | Fabric.js + React state sync | Not persisted |
| Undo/redo history | Custom history manager (array of JSON snapshots) | localStorage (current session) |
| Project metadata (name, description) | React state | Server (PUT /api/canvas-projects/{id}) |
| Tool selection | React state (useState) | Not persisted |
| Panel visibility (layer panel, properties panel) | React state (useState) | localStorage |
| Autosave timer | React effect (useEffect + setInterval) | N/A |
| Zoom level | Fabric.js viewport transform | localStorage |

**Autosave Implementation:**

```typescript
// Dual autosave strategy
useEffect(() => {
  // Fast local save (crash recovery)
  const localTimer = setInterval(() => {
    const json = canvas.toJSON();
    localStorage.setItem(`canvas-project-${projectId}`, JSON.stringify(json));
  }, 10_000); // every 10 seconds

  // Durable server save
  const serverTimer = setInterval(async () => {
    const json = canvas.toJSON();
    const thumbnail = canvas.toDataURL({ format: 'png', multiplier: 0.25 });
    await api.put(`/canvas-projects/${projectId}`, {
      canvas_json: JSON.stringify(json),
      thumbnail_data: thumbnail,
    });
  }, 60_000); // every 60 seconds

  return () => {
    clearInterval(localTimer);
    clearInterval(serverTimer);
  };
}, [canvas, projectId]);
```

**Undo/Redo Implementation:**

```typescript
class CanvasHistoryManager {
  private history: string[] = [];
  private pointer: number = -1;
  private maxSize: number = 50;

  push(state: string): void {
    // Truncate forward history on new action
    this.history = this.history.slice(0, this.pointer + 1);
    this.history.push(state);
    if (this.history.length > this.maxSize) {
      this.history.shift();
    } else {
      this.pointer++;
    }
  }

  undo(): string | null {
    if (this.pointer <= 0) return null;
    return this.history[--this.pointer];
  }

  redo(): string | null {
    if (this.pointer >= this.history.length - 1) return null;
    return this.history[++this.pointer];
  }
}
```

### 6.4 Keyboard Shortcuts

| Shortcut | Action | Context |
|----------|--------|---------|
| Ctrl+Z | Undo | Canvas editor |
| Ctrl+Shift+Z / Ctrl+Y | Redo | Canvas editor |
| Ctrl+S | Save project | Canvas editor |
| Ctrl+E | Export as PNG | Canvas editor |
| Delete / Backspace | Delete selected object(s) | Canvas editor |
| Ctrl+C / Ctrl+V | Copy / Paste object | Canvas editor |
| Ctrl+D | Duplicate selected | Canvas editor |
| Ctrl+A | Select all | Canvas editor |
| Ctrl+G | Group selected | Canvas editor |
| Ctrl+Shift+G | Ungroup | Canvas editor |
| Arrow keys | Nudge selected 1px | Canvas editor |
| Shift+Arrow | Nudge selected 10px | Canvas editor |
| Ctrl+0 | Zoom to fit | Canvas editor |
| Ctrl++ / Ctrl+- | Zoom in / out | Canvas editor |
| T | Text tool | Canvas editor |
| R | Rectangle tool | Canvas editor |
| C | Circle tool | Canvas editor |
| V | Select tool | Canvas editor |

### 6.5 Navigation Changes

The sidebar navigation adds an "Assets" section that expands into sub-routes:

```typescript
// Layout.tsx navigation update
const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Timelines', href: '/timelines', icon: FilmIcon },
  {
    name: 'Assets',
    href: '/assets',
    icon: SwatchIcon,
    children: [
      { name: 'Library', href: '/assets' },
      { name: 'Canvas Editor', href: '/assets/editor' },
      { name: 'Templates', href: '/assets/templates' },
    ],
  },
  { name: 'ReelForge', href: '/reelforge', icon: SparklesIcon },
  { name: 'Settings', href: '/settings', icon: Cog6ToothIcon },
];
```

### 6.6 New Frontend Dependencies

| Package | Version | Size (gzipped) | Purpose |
|---------|---------|----------------|---------|
| fabric | ^6.x | ~90KB | Canvas rendering library |
| react-colorful | ^5.x | ~2KB | Color picker component |

Both packages are MIT-licensed and have no transitive dependencies of concern. Fabric.js v6 is the latest major version with ESM support and TypeScript definitions.

---

## 7. Backend Architecture

### 7.1 New Routers

```
backend/routers/
  assets.py          # Existing - extended with version/schedule/analytics endpoints
  templates.py       # NEW - template catalog and instances
  canvas_projects.py # NEW - canvas project CRUD and export
  fonts.py           # NEW - font management
  asset_groups.py    # NEW (Phase 3) - asset grouping
```

### 7.2 New Services

```
backend/services/
  template_service.py         # Template catalog, instantiation, config validation
  canvas_project_service.py   # Project CRUD, thumbnail generation, PNG export
  font_service.py             # Font upload, Google Fonts download, font catalog
  asset_version_service.py    # Auto-versioning, snapshot, file copy, revert
  asset_schedule_service.py   # Schedule CRUD, evaluation (is asset active now?)
  asset_analytics_service.py  # Display log aggregation, CSV export
  asset_group_service.py      # Group CRUD, member management (Phase 3)
  import_export_service.py    # .vst-template and .vst-assets packaging (Phase 3)
```

### 7.3 New Models

```
backend/models/
  database.py    # Existing - add new model imports
  template.py    # NEW - OverlayTemplate, TemplateInstance
  canvas.py      # NEW - CanvasProject
  asset_ext.py   # NEW - AssetVersion, AssetSchedule, AssetDisplayLog,
                 #        AssetGroup, AssetGroupMember
  font.py        # NEW - Font
```

### 7.4 Database Model Definitions

```python
# backend/models/template.py

class OverlayTemplate(Base):
    __tablename__ = "overlay_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # weather, marine, time_date, sponsor_ad, lower_third, social_media
    description = Column(String)
    config_schema = Column(JSON, nullable=False)  # JSON Schema defining required/optional fields
    default_config = Column(JSON, nullable=False)  # Default values for optional fields
    preview_path = Column(String)  # Path to preview thumbnail
    version = Column(Integer, default=1)
    is_bundled = Column(Boolean, default=True)  # Ships with Docker image
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    instances = relationship("TemplateInstance", back_populates="template")


class TemplateInstance(Base):
    __tablename__ = "template_instances"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("overlay_templates.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    config_values = Column(JSON, nullable=False)  # User-provided configuration
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    template = relationship("OverlayTemplate", back_populates="instances")
    asset = relationship("Asset")
```

```python
# backend/models/canvas.py

class CanvasProject(Base):
    __tablename__ = "canvas_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    canvas_json = Column(String, nullable=False)  # Fabric.js serialized JSON (TEXT)
    thumbnail_path = Column(String)
    width = Column(Integer, default=1920)
    height = Column(Integer, default=1080)
    created_by = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
```

```python
# backend/models/asset_ext.py

class AssetVersion(Base):
    __tablename__ = "asset_versions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String)  # Versioned file copy (nullable for non-file assets)
    metadata_snapshot = Column(JSON, nullable=False)  # Full asset state at this version
    thumbnail_path = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(Integer, ForeignKey("users.id"))
    change_description = Column(String)

    asset = relationship("Asset")


class AssetSchedule(Base):
    __tablename__ = "asset_schedules"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, unique=True)
    schedule_type = Column(String, nullable=False)  # always_on, time_window, rotation
    config = Column(JSON, nullable=False)
    # config example for time_window:
    # {"timezone": "America/New_York", "days_of_week": [0,1,2,3,4],
    #  "start_time": "06:00", "end_time": "22:00"}
    # config example for rotation:
    # {"interval_seconds": 30, "group_id": "sponsors_1"}
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    asset = relationship("Asset")


class AssetDisplayLog(Base):
    __tablename__ = "asset_display_log"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timeline_execution_id = Column(Integer, ForeignKey("timeline_executions.id"))
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    duration_seconds = Column(Float)

    asset = relationship("Asset")


class AssetGroup(Base):
    __tablename__ = "asset_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, onupdate=lambda: datetime.now(timezone.utc))

    members = relationship("AssetGroupMember", back_populates="group",
                          cascade="all, delete-orphan")


class AssetGroupMember(Base):
    __tablename__ = "asset_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("asset_groups.id"), nullable=False)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=True)
    child_group_id = Column(Integer, ForeignKey("asset_groups.id"), nullable=True)
    display_order = Column(Integer, default=0)

    group = relationship("AssetGroup", back_populates="members",
                        foreign_keys=[group_id])
```

```python
# backend/models/font.py

class Font(Base):
    __tablename__ = "fonts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # Display name
    family = Column(String, nullable=False)  # CSS font-family value
    source = Column(String, nullable=False)  # "system", "upload", "google"
    file_path = Column(String)  # Path to .ttf/.otf file (null for system fonts)
    weight = Column(String, default="400")  # "400", "700", etc.
    style = Column(String, default="normal")  # "normal", "italic"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### 7.5 Template Configuration Schema Design

Templates define their configuration using a JSON Schema-like structure stored in `config_schema`. This enables the frontend wizard to dynamically render form fields.

```json
{
  "template_id": "tempest_current_conditions",
  "name": "Tempest Current Conditions",
  "category": "weather",
  "config_schema": {
    "fields": [
      {
        "key": "station_id",
        "label": "Tempest Station ID",
        "type": "text",
        "required": true,
        "placeholder": "e.g., 12345",
        "validation": {"pattern": "^\\d+$", "message": "Must be a numeric station ID"}
      },
      {
        "key": "position",
        "label": "Overlay Position",
        "type": "position_picker",
        "required": false,
        "default": {"x": 0.02, "y": 0.02}
      },
      {
        "key": "theme",
        "label": "Theme",
        "type": "select",
        "required": false,
        "default": "dark",
        "options": [
          {"value": "dark", "label": "Dark"},
          {"value": "light", "label": "Light"}
        ]
      },
      {
        "key": "units",
        "label": "Units",
        "type": "select",
        "required": false,
        "default": "imperial",
        "options": [
          {"value": "imperial", "label": "Fahrenheit / mph"},
          {"value": "metric", "label": "Celsius / km/h"}
        ]
      },
      {
        "key": "refresh_interval",
        "label": "Refresh Interval (seconds)",
        "type": "number",
        "required": false,
        "default": 60,
        "validation": {"min": 10, "max": 600}
      },
      {
        "key": "size",
        "label": "Overlay Size",
        "type": "size_picker",
        "required": false,
        "default": {"width": 400, "height": 300}
      }
    ]
  },
  "default_config": {
    "theme": "dark",
    "units": "imperial",
    "refresh_interval": 60,
    "position": {"x": 0.02, "y": 0.02},
    "size": {"width": 400, "height": 300}
  }
}
```

The `TemplateService` uses the config schema to:
1. Validate user input against field types and validation rules
2. Merge user config with defaults for omitted optional fields
3. Generate the appropriate Asset record properties (e.g., construct the TempestWeather API URL from station_id, theme, and units)

### 7.6 Template Catalog Seeding

Bundled templates are seeded into the database on application startup if not already present. The seeder reads JSON definition files from `/app/templates/catalog/`:

```
/app/templates/catalog/
  tempest_current_conditions/
    definition.json        # Template definition (name, category, config_schema)
    preview.png            # Catalog thumbnail
  tempest_forecast/
    definition.json
    preview.png
  lower_third_basic/
    definition.json
    preview.png
    default_canvas.json    # Fabric.js JSON for canvas-based templates
  time_date_display/
    definition.json
    preview.png
  sponsor_ad_slot/
    definition.json
    preview.png
```

The seeder runs in `main.py` lifespan startup:

```python
async def lifespan(app: FastAPI):
    # ... existing startup code ...
    # Seed template catalog
    from services.template_service import seed_template_catalog
    with get_session() as db:
        seed_template_catalog(db)
    # ...
```

### 7.7 Font Service Architecture

```
Font Discovery Flow:
  1. On startup, scan Docker container for system fonts (/usr/share/fonts/)
  2. Register system fonts in DB with source="system"
  3. Scan /data/fonts/ for previously uploaded/cached fonts
  4. Register those with source="upload" or source="google"

Font Upload Flow:
  1. User uploads .ttf/.otf/.woff2 via POST /api/fonts/upload
  2. Backend validates file (magic bytes, extension)
  3. Saves to /data/fonts/uploads/{uuid}.{ext}
  4. Extracts font metadata (family, weight, style) using fontTools or Pillow
  5. Creates Font DB record
  6. Returns font metadata + CSS @font-face URL

Google Fonts Install Flow:
  1. User searches via GET /api/fonts/google?q=Roboto
  2. Backend queries Google Fonts API (fonts.googleapis.com/css2)
  3. Returns matching font families with variants
  4. User selects font via POST /api/fonts/google/install {family, weights}
  5. Backend downloads .ttf files from Google CDN
  6. Saves to /data/fonts/google/{family}/{weight}.ttf
  7. Creates Font DB records
  8. Returns installed font metadata

Font Serving:
  - Browser: GET /fonts/{filename} (static file serve from /data/fonts/)
  - FFmpeg: filesystem path /data/fonts/{source}/{filename}
    Used in drawtext filter: fontfile=/data/fonts/google/Roboto/400.ttf
```

### 7.8 Registration in main.py

```python
# main.py additions

# Import new routers
from routers import templates, canvas_projects, fonts
# Phase 3: from routers import asset_groups

# Include new routers
app.include_router(templates.router)      # Template catalog
app.include_router(canvas_projects.router) # Canvas projects
app.include_router(fonts.router)           # Font management
# Phase 3: app.include_router(asset_groups.router)

# Mount font files for browser access
fonts_path = Path(os.getenv("FONTS_DIR", "/data/fonts"))
fonts_path.mkdir(parents=True, exist_ok=True)
app.mount("/fonts", StaticFiles(directory=fonts_path), name="fonts")
```

---

## 8. Integration with Existing Systems

### 8.1 Timeline Integration

The existing timeline system uses `TimelineCue` records with `action_type = "show_overlay"` and `action_params` containing `asset_id`. This integration is **unchanged** for Phase 1:

```json
// Existing TimelineCue.action_params for overlay
{
  "asset_id": 42,
  "position_x": 0.8,
  "position_y": 0.05,
  "width": 400,
  "height": 300,
  "opacity": 1.0
}
```

New asset types (`canvas_composite`, `data_bound`) are consumed by the timeline system identically to existing `static_image` and `api_image` types because:
- `canvas_composite` assets have a `file_path` pointing to the exported PNG -- treated like `static_image`
- `data_bound` assets (Phase 2) will have an `api_url` pointing to a backend render endpoint -- treated like `api_image`

### 8.2 FFmpeg Pipeline Integration

The `SeamlessTimelineExecutor` builds FFmpeg filter graphs that composite overlay assets onto the video stream. The integration points:

**Existing overlay compositing (unchanged):**
```
[camera_input] -> [scale to resolution] -> [overlay asset_1] -> [overlay asset_2] -> [encode] -> [rtmp output]
```

**New: Schedule-aware overlay inclusion (Phase 2):**

The `SeamlessTimelineExecutor` currently includes all overlay cues unconditionally. With asset scheduling, the executor will call `AssetScheduleService.is_active_now(asset_id)` before including an asset in the filter graph:

```python
# In SeamlessTimelineExecutor._build_overlay_filters()
for cue in overlay_cues:
    asset_id = cue.action_params.get("asset_id")
    if asset_schedule_service.is_active_now(asset_id, db):
        # Include in filter graph
        overlay_filters.append(build_overlay_filter(cue, asset))
    else:
        # Skip this overlay for the current time window
        pass
```

**New: Font path for drawtext (Phase 2, data_bound assets):**

```
drawtext=fontfile=/data/fonts/google/Roboto/400.ttf:text='72F | Wind 15mph NE':...
```

### 8.3 File Storage Integration

All file storage uses the existing Docker volume mount at `/data/`:

```
/data/
  vistterstream.db           # SQLite database (existing)
  uploads/
    assets/                  # Existing: uploaded asset files
      {uuid}.png
      {uuid}.mp4
      versions/              # NEW: versioned file copies
        {asset_id}/
          {version}/
            {filename}
    canvas/                  # NEW: canvas project thumbnails
      {project_id}_thumb.png
  fonts/                     # NEW: font files
    system/                  # Symlinks or copies of system fonts
    uploads/                 # User-uploaded fonts
      {uuid}.ttf
    google/                  # Cached Google Fonts
      Roboto/
        400.ttf
        700.ttf
```

### 8.4 Content Security Policy Update

The existing CSP in `SecurityHeadersMiddleware` needs updating to allow Fabric.js canvas operations and font loading:

```python
# Updated CSP for canvas editor support
"Content-Security-Policy": (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.youtube.com https://www.gstatic.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: http: https:; "
    "font-src 'self' data: https://fonts.gstatic.com; "  # Allow Google Fonts CDN + data: URIs
    "frame-src https://www.youtube.com; "
    "connect-src 'self' ws: wss: https://fonts.googleapis.com"  # Allow Google Fonts API
)
```

---

## 9. Security Considerations

### 9.1 Input Validation

| Input | Validation | Implementation |
|-------|-----------|----------------|
| Canvas JSON (load) | Sanitize to prevent XSS via stored SVG/script | Strip `<script>` tags, validate object types against Fabric.js allowlist |
| Template config values | Validate against config_schema | Pydantic model + custom validator per field type |
| Font uploads | Validate magic bytes match declared extension | Check file header matches .ttf/.otf/.woff2 |
| Template import packages | HMAC integrity check + schema version validation | Sign with app secret, verify on import |
| Data binding URLs (Phase 2) | SSRF protection | Reuse existing `_validate_url()` function |

### 9.2 Canvas JSON Sanitization

When loading a canvas project from the database, the backend does not need to sanitize (it stores and returns raw JSON). The frontend Fabric.js `loadFromJSON()` only instantiates known Fabric object types, which provides natural sandboxing. However, if custom SVG is imported:

```typescript
// Frontend: sanitize SVG before adding to canvas
function sanitizeSvg(svgString: string): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgString, 'image/svg+xml');
  // Remove script elements
  doc.querySelectorAll('script').forEach(el => el.remove());
  // Remove event handler attributes
  doc.querySelectorAll('*').forEach(el => {
    Array.from(el.attributes).forEach(attr => {
      if (attr.name.startsWith('on')) el.removeAttribute(attr.name);
    });
  });
  return new XMLSerializer().serializeToString(doc);
}
```

### 9.3 File Upload Security

The existing asset upload endpoint validates MIME types and enforces the 50MB limit. New font uploads add:
- Font-specific MIME type validation (font/ttf, font/otf, font/woff2)
- Magic byte verification (check first bytes match font format)
- Maximum font file size: 10MB (fonts should not be large)

---

## 10. Database Migration Strategy

### 10.1 Migration Sequence

All migrations use Alembic with `render_as_batch=True` for SQLite compatibility. Migrations are ordered to match the phased delivery:

| Migration | Phase | Tables/Columns | Reversible |
|-----------|-------|----------------|------------|
| `001_create_overlay_templates` | 1 | Create `overlay_templates`, `template_instances` | Yes (drop tables) |
| `002_create_canvas_projects` | 1 | Create `canvas_projects` | Yes (drop table) |
| `003_create_fonts` | 1 | Create `fonts` | Yes (drop table) |
| `004_add_asset_template_link` | 1 | Add `assets.template_instance_id`, `assets.canvas_project_id` | Yes (drop columns) |
| `005_extend_asset_types` | 1 | Extend `assets.type` validation (app-level, no DB change for SQLite) | N/A |
| `006_create_asset_versions` | 2 | Create `asset_versions` | Yes (drop table) |
| `007_create_asset_schedules` | 2 | Create `asset_schedules` | Yes (drop table) |
| `008_add_data_binding` | 2 | Add `assets.data_binding_config` | Yes (drop column) |
| `009_create_asset_groups` | 3 | Create `asset_groups`, `asset_group_members` | Yes (drop tables) |
| `010_create_display_log` | 3 | Create `asset_display_log` | Yes (drop table) |
| `011_add_user_roles` | 3 | Add `users.role` (default "admin") | Yes (drop column) |

### 10.2 SQLite Considerations

- All migrations use Alembic batch mode (`render_as_batch=True`) because SQLite does not support `ALTER TABLE ... ADD COLUMN` with foreign keys natively
- WAL mode is enabled for concurrent read/write access: `PRAGMA journal_mode=WAL;` (set in engine configuration)
- JSON columns use SQLite's TEXT type with SQLAlchemy's `JSON` type adapter
- No full-text search indexes (SQLite FTS5 could be added later for template/asset search optimization)

---

## 11. Deployment and Infrastructure

### 11.1 Docker Image Changes

The existing Dockerfile needs these additions:

```dockerfile
# In the runtime stage, add font-related packages
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       # ... existing packages ...
       fonts-liberation \
       fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy bundled template catalog
COPY templates/catalog/ /app/templates/catalog/

# Create font directory
RUN mkdir -p /data/fonts
```

The frontend build step in the CI/CD pipeline needs to install the new npm packages (fabric, react-colorful) before `npm run build`.

### 11.2 Volume Mounts

The existing `/data` volume mount is sufficient. New subdirectories are created automatically by the application:

```yaml
# docker-compose.yml (no changes needed)
volumes:
  - /path/to/data:/data
  # /data/vistterstream.db      (existing)
  # /data/uploads/assets/        (existing)
  # /data/uploads/canvas/        (new, auto-created)
  # /data/fonts/                  (new, auto-created)
```

### 11.3 Estimated Resource Impact

| Resource | Current | After Studio | Notes |
|----------|---------|-------------|-------|
| Docker image size | ~250MB | ~260MB | +10MB for template assets and system fonts |
| SQLite DB size | ~100KB | ~500KB-5MB | Canvas JSON can be large (50-200KB per project) |
| Disk storage | Varies | +10-50MB typical | Font cache + versioned files + canvas thumbnails |
| Memory (backend) | ~80MB | ~85MB | Minimal new service overhead |
| Memory (frontend/browser) | ~50MB | ~100-150MB | Fabric.js canvas with many objects |
| CPU (backend) | Low | Low | Thumbnail generation is occasional Pillow work |
| CPU (browser) | Low | Moderate during editing | Fabric.js canvas rendering (targets 60fps) |

---

## 12. Testing Strategy

### 12.1 Backend Testing

| Area | Type | Coverage Target |
|------|------|-----------------|
| Template CRUD | Unit + Integration | All endpoints, config validation |
| Canvas project CRUD | Unit + Integration | Save/load JSON roundtrip, export |
| Font upload | Unit + Integration | Valid/invalid files, Google Fonts mock |
| Asset versioning | Unit | Snapshot/restore, version limit purge |
| Asset scheduling | Unit | Time window evaluation across timezones |
| Template seeder | Integration | Idempotent catalog seeding |
| Migration scripts | Integration | Up/down for each migration |

### 12.2 Frontend Testing

| Area | Type | Coverage Target |
|------|------|-----------------|
| Template catalog | Component | Rendering, filtering, search |
| Template wizard | Component | Form validation, submit flow |
| Canvas editor | Integration | Tool selection, object creation, save/load |
| Layer panel | Component | Reorder, visibility toggle, lock |
| Autosave | Unit | Timer behavior, localStorage/server dual save |
| Undo/redo | Unit | History stack, boundary conditions |

### 12.3 End-to-End Scenarios

1. Browse catalog -> configure weather template -> asset created -> add to timeline
2. Open canvas editor -> add text + image + shape -> export PNG -> asset in library
3. Edit asset -> version created -> view history -> revert to previous version
4. Upload custom font -> use in canvas editor -> export PNG renders correctly
5. Import .vst-template -> template instance created -> assets functional

---

## 13. Architectural Decision Records

### ADR-001: Fabric.js as Canvas Library

**Status:** Accepted
**Date:** 2026-03-15

**Context:**
The Asset Management Studio needs an in-browser canvas editor for creating overlay graphics. The library must support text, shapes, images, z-ordering, serialization, and PNG export.

**Decision:**
Use Fabric.js v6 as the canvas rendering library.

**Alternatives Considered:**

| Option | Pros | Cons |
|--------|------|------|
| **Fabric.js v6** | Mature (10+ years), MIT license, built-in serialization (toJSON/loadFromJSON), object model with selection/grouping, active maintenance, 28k stars, TypeScript support | 90KB gzipped, monolithic API, learning curve for advanced features |
| **Konva.js** | Reactive model, good React integration (react-konva), smaller bundle | No built-in serialization format, less mature text editing, manual z-order management |
| **Custom Canvas API** | Full control, minimal bundle | Massive development effort for selection, grouping, serialization, text editing |
| **SVG (via D3 or raw)** | Resolution independent, DOM-based | Poor performance with many elements, complex export to raster PNG |

**Consequences:**
- Positive: Rapid development of canvas features using built-in Fabric.js capabilities
- Positive: JSON serialization enables save/load without custom format design
- Positive: Well-documented library with large community
- Negative: 90KB added to frontend bundle (acceptable for the feature complexity)
- Negative: Fabric.js patterns (imperative canvas API) differ from React's declarative model; requires careful ref management

---

### ADR-002: Dual Autosave Strategy

**Status:** Accepted
**Date:** 2026-03-15

**Context:**
The canvas editor must prevent data loss. Users expect modern auto-save behavior.

**Decision:**
Implement dual autosave: localStorage every 10 seconds + server save every 60 seconds.

**Alternatives Considered:**

| Option | Pros | Cons |
|--------|------|------|
| **Server-only autosave** | Simple, durable | Network latency, data loss if browser crashes between saves |
| **localStorage-only autosave** | Instant, no network | Lost if user clears browser data or uses different device |
| **Dual autosave (chosen)** | Best of both: instant crash recovery + cross-device durability | Slightly more complex implementation |

**Consequences:**
- Positive: Near-zero data loss risk
- Positive: Fast recovery after browser crash (localStorage is instant)
- Positive: Server saves enable opening projects on different devices
- Negative: Need to handle conflict resolution if localStorage state differs from server state (simple: server wins, show "recovered from local" notification)

---

### ADR-003: Template Config as JSON Schema in Database

**Status:** Accepted
**Date:** 2026-03-15

**Context:**
Templates need a way to define their configuration fields so the frontend wizard can dynamically render forms.

**Decision:**
Store template configuration schemas as JSON in the `config_schema` column. The frontend interprets the schema to render form fields dynamically.

**Alternatives Considered:**

| Option | Pros | Cons |
|--------|------|------|
| **Hardcoded frontend forms per template** | Maximum control, simpler data model | Adding templates requires code changes, not extensible |
| **JSON Schema (standard)** | Industry standard, validation libraries exist | Complex spec, overkill for simple forms |
| **Custom JSON config schema (chosen)** | Simple, tailored to our needs, easy to render | Non-standard, must build own renderer |

**Consequences:**
- Positive: New templates can be added by writing JSON definition files, no code changes
- Positive: Community templates can ship as JSON packages
- Negative: Custom schema format requires custom validation logic (but it is simple)

---

### ADR-004: Static PNG Export (Not Real-Time Canvas Rendering)

**Status:** Accepted
**Date:** 2026-03-15

**Context:**
The canvas editor produces overlay designs. These need to be composited onto the live stream by FFmpeg.

**Decision:**
The canvas editor exports static PNG images that are consumed by the existing FFmpeg overlay pipeline. There is no real-time rendering from canvas JSON at stream time.

**Consequences:**
- Positive: Zero changes to the FFmpeg pipeline for canvas-based overlays
- Positive: No additional CPU load at stream time for canvas rendering
- Positive: Canvas exports are pre-rasterized at the correct resolution
- Negative: To update a canvas-based overlay, user must re-export (not automatic)
- Negative: Dynamic text in canvas overlays requires re-export (Phase 2 `data_bound` type addresses this separately)

---

### ADR-005: Font Files Shared Between Browser and FFmpeg via Filesystem

**Status:** Accepted
**Date:** 2026-03-15

**Context:**
Fonts used in the canvas editor must also be available to FFmpeg's `drawtext` filter for data-bound text rendering (Phase 2). The browser loads fonts via CSS @font-face; FFmpeg loads them via filesystem path.

**Decision:**
Store all fonts in `/data/fonts/` on the Docker volume. Serve them to the browser via a static file mount (`/fonts/`). Reference them by filesystem path in FFmpeg commands.

**Consequences:**
- Positive: Single source of truth for font files
- Positive: Fonts persist across container rebuilds (volume mount)
- Positive: Both browser and FFmpeg access the same files
- Negative: Font files must be in formats FFmpeg understands (.ttf, .otf -- not .woff2 for FFmpeg)

---

## 14. Open Questions and Future Considerations

### Open Questions

All original PRD open questions have been resolved. No new architectural questions remain.

### Future Considerations

1. **WebSocket autosave** -- If multi-user editing is added, WebSocket could replace polling-based autosave for real-time collaboration (currently out of scope)
2. **Canvas rendering service** -- For data-bound overlays that need dynamic text, a headless canvas renderer (using Puppeteer or node-canvas) could generate PNGs server-side on a schedule, avoiding FFmpeg drawtext complexity
3. **Template marketplace** -- If community template sharing becomes a feature, a centralized template registry could be built as a separate service
4. **Undo/redo optimization** -- The current approach stores full canvas JSON snapshots. For large canvases, delta-based undo (storing only diffs) would reduce memory usage
5. **IndexedDB for large projects** -- If canvas projects exceed localStorage limits (typically 5-10MB), IndexedDB provides larger client-side storage

---

## 15. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-15 | Nick DeMarco (AI-assisted) | Initial architecture document covering all three pillars |
