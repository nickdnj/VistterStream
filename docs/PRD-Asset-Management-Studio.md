# Product Requirements Document: VistterStream Asset Management Studio

**Version:** 1.0
**Last Updated:** 2026-03-15
**Author:** Nick DeMarco with AI Assistance
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Transform VistterStream's basic asset CRUD manager into a full **Asset Management Studio** -- a creative tool that makes it easy for anyone running a VistterStream appliance to create, manage, and deploy professional-quality stream overlays without requiring external design tools or video editing expertise.

The current asset system provides fundamental capabilities (five asset types, file upload, API-backed images, basic positioning and opacity controls, and integration with the timeline overlay system). The Asset Management Studio builds on this foundation with three product pillars: a pre-built **Overlay Catalog and Template System**, an in-browser **Asset Builder (Canvas Editor)**, and comprehensive **Asset Lifecycle and Intelligence** features.

### 1.2 Target Users

| User Persona | Description | Key Needs |
|---|---|---|
| **Beach/Marina Cam Operator** | Runs 24/7 unattended streams of waterfront scenes. Non-technical. Wants weather, tide, and time-of-day overlays. | Pre-built templates, simple configuration wizards, automated data-driven overlays |
| **Community Channel Producer** | Manages a small local broadcast with occasional live events. Moderate technical skill. | Canvas editor for ad creation, sponsor logos, lower thirds, asset scheduling |
| **Small Broadcaster / Content Creator** | Runs multi-camera streams for small events or businesses. Wants professional look. | Animation system, asset groups, responsive overlays, brand consistency |
| **Ad Spot Seller** | Monetizes stream viewership by selling overlay ad slots to local businesses. | Asset analytics (impressions), scheduling by time-of-day, rotation intervals, easy ad creation |

### 1.3 Success Metrics

| Metric | Target | How Measured |
|---|---|---|
| Time to first overlay | Under 5 minutes from template catalog to live stream | Instrumented onboarding flow |
| Template adoption rate | 80% of new VistterStream instances use at least one catalog template | Template usage telemetry |
| Canvas editor satisfaction | Users can create a branded lower third in under 3 minutes | Usability testing |
| Asset uptime | Overlay assets render correctly 99.9% of scheduled display time | Stream health monitoring |
| Ad overlay creation | Non-designer creates a usable ad overlay in under 10 minutes | Task completion testing |

---

## 2. Scope

### 2.1 In Scope

**Pillar 1 -- Overlay Catalog and Template System**
- Browsable template catalog with categories
- Configuration wizards per template (fill-in-the-blanks)
- Weather overlay templates (Tempest Weather integration)
- Tide chart and marine weather templates
- Time/date display templates
- Sponsor/ad rotation templates
- Lower third templates
- Social media feed display templates
- Template export/import between VistterStream instances

**Pillar 2 -- Asset Builder (Canvas Editor)**
- Browser-based canvas editor (HTML5 Canvas / Fabric.js)
- Drag-and-drop image import from file system
- Text layers with font selection, color, sizing, and effects
- Shape layers (rectangles, circles, lines, rounded rectangles)
- Multi-layer composition with z-ordering
- Position, resize, and rotate elements
- Opacity and blend modes per layer
- Snap-to-grid and alignment guides
- Export as PNG (static) or animated GIF/APNG (animated)
- Save canvas projects for later editing

**Pillar 3 -- Asset Lifecycle and Intelligence**
- Animation system (entrance/exit animations per asset)
- Responsive asset scaling for different output resolutions
- Live data bindings (text overlays bound to API data sources)
- Independent asset scheduling (time-of-day, rotation, day-of-week)
- Version history with revert capability
- Asset groups/composites (bundled related assets)
- Import/export of portable asset library packages
- Asset analytics (display time, impression counts)
- Multi-user editing with role-based permissions

### 2.2 Out of Scope

- Real-time video effects (chroma key, picture-in-picture) -- these are FFmpeg pipeline concerns
- Audio overlay editing
- 3D graphics or WebGL-based rendering
- Direct social media API integrations for fetching feed content (Phase 2+)
- Mobile app for asset editing (browser-based only)
- AI-generated overlay artwork
- Monetization/billing system for ad spots (analytics only, billing is external)
- VistterStudio cloud sync (tracked separately in VistterStudioIntegration.md)

### 2.3 Constraints

| Constraint | Detail |
|---|---|
| **Architecture** | Must integrate with existing FastAPI backend, React/TypeScript frontend, FFmpeg pipeline, and SQLite database |
| **Deployment** | Docker-based; runs on Ubuntu server at 192.168.86.38; no additional services required |
| **Database** | SQLite (may need migration strategy for new tables; consider WAL mode for concurrent access) |
| **Frontend** | Tailwind CSS; existing component patterns; no new CSS frameworks |
| **FFmpeg** | All overlay rendering happens in the FFmpeg filter graph at stream time; canvas editor produces static assets consumed by the existing compositing pipeline |
| **Backward Compatibility** | All changes must be backward-compatible with existing timeline/overlay system, Asset model, and API endpoints |
| **File Size** | Current 50MB upload limit remains; canvas exports are typically under 5MB |
| **Hardware** | Canvas editor must work without GPU (CPU-only rendering in browser); stream encoding uses existing hardware acceleration |
| **Performance** | Canvas editor interactions must feel responsive (targeting 60fps for drag operations) |

---

## 3. Functional Requirements

### 3.1 Overlay Catalog and Template System

#### 3.1.1 Template Catalog Browser

**User Story**
As a stream operator, I want to browse a catalog of pre-built overlay templates so that I can quickly add professional overlays to my stream without designing them from scratch.

**Acceptance Criteria**
- [ ] Catalog is accessible from the main navigation as "Templates" or from within the Assets page
- [ ] Templates are organized by category: Weather, Marine, Time/Date, Sponsor/Ad, Lower Thirds, Social Media, Custom
- [ ] Each template shows a preview thumbnail, name, description, and required configuration fields
- [ ] User can search/filter templates by category and keyword
- [ ] Clicking a template opens its configuration wizard
- [ ] Templates ship with the VistterStream Docker image (bundled, no external download required)

**User Flow**
1. User navigates to Assets > Template Catalog
2. User browses categories or searches for "weather"
3. User selects "Current Conditions" weather template
4. Configuration wizard opens
5. User enters Tempest station ID and selects display options
6. User clicks "Create Asset" -- system generates the configured asset
7. Asset appears in the asset library, ready to be added to a timeline

**Business Rules**
- Templates define required fields, optional fields, and default values
- A template instance is a regular Asset record with a `template_id` foreign key linking back to the template definition
- Modifying a template instance does not affect other instances of the same template
- Template definitions are versioned; updating a template definition does not retroactively change existing instances

#### 3.1.2 Template Configuration Wizards

**User Story**
As a stream operator, I want a guided wizard for each template type so that I can configure it with my specific data without understanding the underlying technical details.

**Acceptance Criteria**
- [ ] Each template type has a dedicated configuration form
- [ ] Required fields are clearly marked; optional fields show defaults
- [ ] Wizard provides real-time preview of the configured overlay
- [ ] Wizard validates inputs before allowing creation (e.g., valid station ID format, valid URL)
- [ ] Wizard provides a "Test" button to verify data source connectivity (for API-backed templates)

**Template Configuration Specifications**

| Template | Required Fields | Optional Fields | Data Source |
|---|---|---|---|
| **Tempest Current Conditions** | Station ID | Position, size, refresh interval, theme (light/dark), units (F/C) | TempestWeather API (existing integration at `http://host.docker.internal:8036`) |
| **Tempest 5-Day Forecast** | Station ID | Position, size, refresh interval, compact/expanded mode | TempestWeather API |
| **Tide Chart** | Location (lat/lng or station name) | Position, size, time range, theme | NOAA Tides API |
| **Marine Weather** | Location | Position, size, wind/wave display options | NOAA Marine API or Tempest |
| **Time/Date Display** | Timezone | Format (12h/24h), font, color, position | System clock |
| **Sponsor/Ad Slot** | Business name, logo image | Rotation interval, position, animation, schedule | Local file upload |
| **Lower Third** | Title text | Subtitle, icon, theme, position, animation | Static text |
| **Social Media Feed** | Platform, handle/hashtag | Display count, refresh interval, theme | Platform API (Phase 2) |

#### 3.1.3 Weather Overlay Templates (Tempest Integration)

**User Story**
As a beach/marina cam operator, I want to display current weather conditions from my Tempest weather station directly on my stream so that viewers can see real-time conditions.

**Acceptance Criteria**
- [ ] Weather overlays fetch data from the existing TempestWeather API integration
- [ ] Current conditions template displays: temperature, humidity, wind speed/direction, barometric pressure, and conditions icon
- [ ] 5-day forecast template displays: daily high/low, conditions icon, and precipitation chance
- [ ] Templates support both imperial and metric units
- [ ] Templates support light and dark themes
- [ ] Data refreshes on a configurable interval (default: 60 seconds for conditions, 300 seconds for forecast)
- [ ] When weather API is unavailable, the overlay displays a "Data Unavailable" state rather than disappearing or showing stale data with no indication

**Technical Notes**
- The existing `api_image` asset type fetches pre-rendered images from the TempestWeather API. Weather templates extend this by supporting a new `data_bound` asset type that fetches JSON data and renders it client-side using a template definition.
- Alternatively, the TempestWeather service can be extended to render additional overlay images (current approach is simpler and keeps rendering in one place).
- Decision: Phase 1 uses the existing `api_image` approach with TempestWeather rendering the overlays. Phase 2 adds `data_bound` type for more flexible rendering.

#### 3.1.4 Template Import/Export

**User Story**
As a stream operator running multiple VistterStream instances, I want to export my configured templates from one instance and import them into another so that I can maintain consistent branding across sites.

**Acceptance Criteria**
- [ ] Export produces a `.vst-template` file (ZIP containing JSON definition + bundled assets)
- [ ] Import accepts `.vst-template` files and creates new template instances
- [ ] Import validates file integrity (checksum) and compatibility (schema version)
- [ ] Import resolves asset file conflicts (rename on collision)
- [ ] Export/import is available from the Template Catalog UI
- [ ] File format is documented for potential community sharing

**Data Format**
```
template-export.vst-template (ZIP)
  manifest.json          # Template metadata, schema version, asset manifest
  definition.json        # Template configuration and defaults
  assets/                # Bundled image/video files
    logo.png
    background.png
  preview.png            # Template preview thumbnail
```

---

### 3.2 Asset Builder (Canvas Editor)

#### 3.2.1 Canvas Editor Core

**User Story**
As a stream operator, I want an in-browser canvas editor so that I can create custom overlay graphics (ads, lower thirds, branded elements) without needing external design software.

**Acceptance Criteria**
- [ ] Canvas editor opens in a modal or dedicated page from the Assets section
- [ ] Canvas defaults to stream resolution (1920x1080 or as configured) with transparent background
- [ ] Editor provides a toolbar with: Select, Text, Rectangle, Circle, Line, Image Import tools
- [ ] Canvas supports zoom and pan for detailed editing
- [ ] Undo/redo with at least 50 levels of history
- [ ] Save project for later editing (stored as JSON in the database)
- [ ] Export to PNG with transparency
- [ ] Exported image is automatically registered as a new `static_image` asset
- [ ] Canvas interactions (drag, resize, rotate) maintain 60fps responsiveness

**Technical Approach**
- Use **Fabric.js** (MIT license, mature, well-documented) as the canvas rendering library
- Fabric.js provides built-in support for: object selection, grouping, z-ordering, serialization to JSON, export to PNG/SVG, text editing, image import, shape drawing
- Store canvas project JSON in a new `canvas_projects` database table
- Export renders to PNG via `canvas.toDataURL()`, then uploads via the existing `/api/assets/upload` endpoint

#### 3.2.2 Text Layers

**User Story**
As a stream operator, I want to add text to my overlay designs with full control over font, size, color, and effects so that I can create professional-looking titles and labels.

**Acceptance Criteria**
- [ ] Add text with click-to-place on canvas
- [ ] Inline text editing (double-click to edit)
- [ ] Font selection from a curated list of web-safe and Google Fonts (at least 20 options)
- [ ] Font size: 8px to 200px
- [ ] Font color: color picker with hex input
- [ ] Font style: bold, italic, underline, strikethrough
- [ ] Text alignment: left, center, right
- [ ] Text background color (with opacity control) for readability on varied backgrounds
- [ ] Text shadow with configurable offset, blur, and color
- [ ] Text outline (stroke) with configurable width and color
- [ ] Multi-line text support with line height control

**Font Availability Note**
- Fonts used in the canvas editor must also be available to FFmpeg for `drawtext` filter rendering. For Phase 1, limit to system fonts that are guaranteed available in the Docker container. Phase 2 adds font management (upload custom fonts, install Google Fonts to the container).

#### 3.2.3 Shape Layers

**User Story**
As a stream operator, I want to add shapes to my overlay designs so that I can create backgrounds, borders, and decorative elements.

**Acceptance Criteria**
- [ ] Rectangle tool with configurable fill color, border color, border width, corner radius
- [ ] Circle/ellipse tool with configurable fill and border
- [ ] Line tool with configurable color, width, and dash pattern
- [ ] Rounded rectangle (for lower third backgrounds, info boxes)
- [ ] All shapes support: opacity, fill color, gradient fills (linear and radial), border/stroke
- [ ] Shapes can be used as text backgrounds (group text + shape)

#### 3.2.4 Image Import

**User Story**
As a stream operator, I want to import images (logos, photos, icons) into the canvas editor so that I can compose them with text and shapes into complete overlay designs.

**Acceptance Criteria**
- [ ] Drag-and-drop image import from desktop
- [ ] File browser import
- [ ] Import from existing asset library (select from already-uploaded assets)
- [ ] Supported formats: PNG, JPEG, SVG, WebP, GIF
- [ ] Imported images can be resized, rotated, and repositioned
- [ ] Image cropping within the canvas
- [ ] Image opacity control
- [ ] Maximum import size: 50MB (matching existing upload limit)

#### 3.2.5 Layer Management

**User Story**
As a stream operator, I want to manage multiple layers in my overlay design so that I can control which elements appear in front of or behind others.

**Acceptance Criteria**
- [ ] Layer panel shows all objects on the canvas in z-order
- [ ] Drag-to-reorder layers
- [ ] Toggle layer visibility (eye icon)
- [ ] Lock layer to prevent accidental edits (lock icon)
- [ ] Rename layers for organization
- [ ] Select object by clicking its layer entry
- [ ] Group/ungroup multiple objects
- [ ] Duplicate layer

#### 3.2.6 Alignment and Guides

**User Story**
As a stream operator, I want alignment tools and guides so that I can precisely position elements within my overlay design.

**Acceptance Criteria**
- [ ] Snap-to-grid (toggleable, configurable grid size)
- [ ] Smart guides (snap to edges and centers of other objects)
- [ ] Alignment buttons: align left, center, right, top, middle, bottom (relative to selection or canvas)
- [ ] Distribution buttons: distribute horizontally, distribute vertically (for 3+ selected objects)
- [ ] Rulers along top and left edges showing pixel coordinates
- [ ] Safe zone overlay showing title-safe and action-safe areas (standard broadcast margins)

#### 3.2.7 Canvas Project Management

**User Story**
As a stream operator, I want to save my canvas designs as editable projects so that I can return to them later for modifications without starting from scratch.

**Acceptance Criteria**
- [ ] Save project with a name and description
- [ ] Project saves all layers, positions, styles, and imported images
- [ ] List saved projects with thumbnails
- [ ] Open/resume editing a saved project
- [ ] Duplicate a project as a starting point for variations
- [ ] Delete projects
- [ ] Auto-save every 60 seconds while editing (prevent data loss)

**Data Model**
```
canvas_projects table:
  id: integer (primary key)
  name: string
  description: string (nullable)
  canvas_json: text (Fabric.js serialized JSON)
  thumbnail_path: string (auto-generated preview)
  width: integer
  height: integer
  created_at: datetime
  updated_at: datetime
  created_by: integer (FK to users)
  is_active: boolean (soft delete)
```

---

### 3.3 Asset Lifecycle and Intelligence

#### 3.3.1 Animation System

**User Story**
As a stream operator, I want to configure entrance and exit animations for my overlay assets so that they appear and disappear smoothly rather than popping in and out abruptly.

**Acceptance Criteria**
- [ ] Each asset in the timeline supports configurable entrance and exit animations
- [ ] Supported entrance animations: fade in, slide in (from left/right/top/bottom), zoom in, bounce in, wipe in
- [ ] Supported exit animations: fade out, slide out (to left/right/top/bottom), zoom out, bounce out, wipe out
- [ ] Animation duration is configurable (100ms to 5000ms, default 500ms)
- [ ] Animation easing is selectable: linear, ease-in, ease-out, ease-in-out, bounce
- [ ] Looping animations available for persistent overlays: pulse, breathe (slow opacity cycle), gentle float
- [ ] Animations are previewed in the timeline overlay preview panel
- [ ] Animations are implemented in the FFmpeg filter graph at render time

**Technical Implementation**
- Animations are stored as JSON in the existing `action_params` field of `timeline_cues`
- FFmpeg implementation uses time-based `overlay` filter expressions for position-based animations, and `blend`/opacity keyframes for fade effects
- For complex animations, consider pre-rendering animated overlays as short video clips (APNG or VP9 with alpha) rather than computing in real-time FFmpeg filters

**Animation Data Schema**
```json
{
  "entrance": {
    "type": "fade_in",
    "duration_ms": 500,
    "easing": "ease-in-out",
    "delay_ms": 0
  },
  "exit": {
    "type": "slide_out_bottom",
    "duration_ms": 300,
    "easing": "ease-in"
  },
  "loop": {
    "type": "pulse",
    "period_ms": 2000,
    "intensity": 0.15
  }
}
```

#### 3.3.2 Responsive Asset Scaling

**User Story**
As a stream operator who streams at different resolutions (720p, 1080p, 4K), I want my overlay assets to automatically scale to the correct proportions regardless of output resolution.

**Acceptance Criteria**
- [ ] Assets store position and size in normalized coordinates (0.0 to 1.0) -- already implemented
- [ ] When stream resolution changes, overlays automatically reposition and resize proportionally
- [ ] High-resolution source assets are downscaled for lower resolutions (no upscaling artifacts)
- [ ] Canvas editor supports resolution presets (720p, 1080p, 1440p, 4K) for previewing how overlays look at each resolution
- [ ] Overlays maintain aspect ratio when scaled

**Business Rules**
- Current system already uses normalized 0-1 positioning (`position_x`, `position_y`); this is extended to also normalize width/height
- Pixel dimensions stored on the Asset are treated as "designed-for" dimensions at the reference resolution (timeline's configured resolution)
- FFmpeg filter graph scales overlay inputs to match the output resolution proportionally

#### 3.3.3 Live Data Bindings

**User Story**
As a stream operator, I want to bind text overlays to live data sources so that information like temperature, tide levels, or custom metrics update automatically on my stream without manual intervention.

**Acceptance Criteria**
- [ ] New asset type: `data_bound` -- a text or composite overlay driven by a JSON data source
- [ ] Data source configuration: URL, authentication (optional), refresh interval, JSON path expression for extracting values
- [ ] Template string support: `"Current Temp: {{temperature}}F | Wind: {{wind_speed}}mph {{wind_direction}}"` where `{{field}}` placeholders are replaced with live data
- [ ] Multiple data source bindings per asset
- [ ] Fallback text when data source is unavailable
- [ ] Data source test button to verify connectivity and preview extracted values
- [ ] SSRF protection applies to data source URLs (using existing `_validate_url` function)

**Data Flow**
```
Data Source (HTTP JSON API)
    |
    v
Backend fetch (on refresh interval)
    |
    v
Extract values via JSON path
    |
    v
Render text overlay via FFmpeg drawtext
    |
    v
Composite onto stream
```

**Data Binding Schema**
```json
{
  "bindings": [
    {
      "source_url": "http://192.168.86.38:8036/api/current",
      "refresh_interval_seconds": 60,
      "auth_header": null,
      "field_map": {
        "temperature": "$.current.temperature",
        "wind_speed": "$.current.wind_speed",
        "wind_direction": "$.current.wind_direction_cardinal"
      },
      "fallback_values": {
        "temperature": "--",
        "wind_speed": "--",
        "wind_direction": "--"
      }
    }
  ],
  "template": "{{temperature}}F | Wind: {{wind_speed}}mph {{wind_direction}}",
  "font": "Arial",
  "font_size": 36,
  "font_color": "#FFFFFF",
  "background_color": "rgba(0,0,0,0.6)",
  "position": "bottom_right"
}
```

#### 3.3.4 Asset Scheduling

**User Story**
As a stream operator, I want to schedule individual assets to display at specific times of day or on specific days of the week so that I can automate overlay changes (e.g., morning greeting vs. evening sign-off, weekday vs. weekend sponsors).

**Acceptance Criteria**
- [ ] Each asset supports an independent display schedule (separate from timeline scheduling)
- [ ] Schedule options: always on, time-of-day window (start/end time), days-of-week, rotation interval
- [ ] Rotation mode: cycle through a set of assets at a configurable interval (e.g., rotate sponsor logos every 30 seconds)
- [ ] Schedule respects the appliance timezone (from Settings)
- [ ] Schedule is evaluated at the FFmpeg pipeline level -- assets are included/excluded from the filter graph based on schedule
- [ ] Schedule conflicts are detected and warned (e.g., two assets scheduled for the same position at the same time)
- [ ] UI shows a visual schedule overview (weekly calendar view) for all scheduled assets

**Asset Schedule Schema**
```json
{
  "schedule_type": "time_window",
  "timezone": "America/New_York",
  "days_of_week": [0, 1, 2, 3, 4],
  "start_time": "06:00",
  "end_time": "22:00",
  "rotation": {
    "enabled": true,
    "interval_seconds": 30,
    "group_id": "sponsor_rotation_1"
  }
}
```

#### 3.3.5 Version History

**User Story**
As a stream operator, I want to see previous versions of an asset and revert to an earlier version if a change does not look right on the stream.

**Acceptance Criteria**
- [ ] Every update to an asset creates a version record
- [ ] Version history shows: version number, timestamp, who made the change, and a preview thumbnail
- [ ] User can preview any previous version
- [ ] User can revert to any previous version (creates a new version with the old content)
- [ ] Version history is limited to the last 50 versions per asset (oldest auto-purge)
- [ ] File-based assets (static_image, video) store previous file versions in a versioned directory structure

**Data Model**
```
asset_versions table:
  id: integer (primary key)
  asset_id: integer (FK to assets)
  version_number: integer
  file_path: string (nullable, for file-based assets)
  metadata_snapshot: text (JSON snapshot of asset properties at this version)
  thumbnail_path: string (nullable)
  created_at: datetime
  created_by: integer (FK to users)
  change_description: string (nullable, auto-generated or user-provided)
```

#### 3.3.6 Asset Groups and Composites

**User Story**
As a stream operator, I want to group related assets together (e.g., a weather widget composed of a conditions image, forecast image, and text ticker) so that I can manage and schedule them as a single unit.

**Acceptance Criteria**
- [ ] Create an asset group with a name and description
- [ ] Add/remove assets to/from a group
- [ ] Groups appear in the asset library alongside individual assets
- [ ] Adding a group to a timeline adds all member assets at their configured positions
- [ ] Scheduling a group applies the schedule to all member assets
- [ ] Toggling a group on/off in the timeline toggles all member assets
- [ ] Groups can be nested (a group can contain other groups) -- max depth: 3 levels
- [ ] Groups can be exported/imported as part of template packages

**Data Model**
```
asset_groups table:
  id: integer (primary key)
  name: string
  description: string (nullable)
  created_at: datetime
  updated_at: datetime
  is_active: boolean

asset_group_members table:
  id: integer (primary key)
  group_id: integer (FK to asset_groups)
  asset_id: integer (FK to assets, nullable)
  child_group_id: integer (FK to asset_groups, nullable)
  display_order: integer
```

#### 3.3.7 Import/Export Asset Library

**User Story**
As a stream operator, I want to export my entire asset library (or selected assets) as a portable package so that I can back it up or deploy it to another VistterStream instance.

**Acceptance Criteria**
- [ ] Export selected assets or entire library as a `.vst-assets` file (ZIP)
- [ ] Package includes: asset metadata, files, canvas projects, template instances, groups, and schedules
- [ ] Import validates package integrity and handles conflicts (skip, overwrite, rename)
- [ ] Import/export is available from the Assets page toolbar
- [ ] Large exports (over 500MB) show progress indication
- [ ] Package format is versioned for forward compatibility

#### 3.3.8 Asset Analytics

**User Story**
As a stream operator who sells ad overlay spots, I want to track how long each asset has been displayed and how many "impressions" it has received so that I can report viewership data to advertisers.

**Acceptance Criteria**
- [ ] Track cumulative display time per asset (total seconds displayed on stream)
- [ ] Track display count (number of times the asset was shown -- entrance events)
- [ ] Track display sessions (start/end timestamps for each display period)
- [ ] Analytics dashboard shows per-asset statistics with date range filtering
- [ ] Export analytics data as CSV
- [ ] Analytics are computed from timeline execution history and stream uptime data
- [ ] Analytics do not impact stream performance (computed asynchronously/batch)

**Data Model**
```
asset_display_log table:
  id: integer (primary key)
  asset_id: integer (FK to assets)
  timeline_execution_id: integer (FK to timeline_executions)
  started_at: datetime
  ended_at: datetime (nullable, null if currently displaying)
  duration_seconds: float (computed on end)
```

#### 3.3.9 Multi-User Editing and Permissions

**User Story**
As a stream operator managing a team, I want role-based permissions on asset management so that designers can create and edit assets but cannot start/stop streams, and operators can manage streams but cannot accidentally modify overlay designs.

**Acceptance Criteria**
- [ ] User roles: Admin, Designer, Operator, Viewer
- [ ] Admin: full access to all features
- [ ] Designer: create/edit/delete assets, canvas projects, templates; cannot start/stop streams or manage cameras
- [ ] Operator: start/stop streams, manage timelines, add existing assets to timelines; cannot create/edit assets
- [ ] Viewer: read-only access to dashboards and analytics
- [ ] Role assignment is managed by Admin users
- [ ] Asset-level locking: a user can lock an asset to prevent concurrent edits
- [ ] Concurrent edit detection: warn user if an asset was modified by someone else since they loaded it

**Technical Notes**
- The current system has a single `users` table with no role column. This feature adds a `role` column with a default of `admin` for backward compatibility.
- Asset locking uses optimistic concurrency (check `last_updated` timestamp before saving).

---

## 4. Non-Functional Requirements

### 4.1 Performance

| Requirement | Target |
|---|---|
| Canvas editor frame rate | 60fps during drag/resize operations with up to 50 objects |
| Canvas editor load time | Under 2 seconds for a project with 20 layers |
| Asset library page load | Under 1 second for 200 assets |
| Template catalog load | Under 500ms |
| API image proxy response | Under 500ms (existing requirement, maintained) |
| Overlay render latency | Under 100ms added latency to FFmpeg pipeline per overlay |
| Canvas PNG export | Under 3 seconds for a 1920x1080 canvas |

### 4.2 Scalability

| Dimension | Target |
|---|---|
| Maximum assets per instance | 1,000 |
| Maximum canvas layers per project | 100 |
| Maximum concurrent overlay assets in a stream | 10 (FFmpeg filter graph complexity limit) |
| Maximum template catalog size | 50 templates |
| Maximum asset versions stored | 50 per asset |
| Maximum canvas projects | 500 |
| Storage: asset files | Up to 10GB total (configurable, with cleanup warnings) |

### 4.3 Security

- All asset upload endpoints require authentication (existing `get_current_user` dependency, maintained)
- SSRF protection on all URL-based inputs (API URLs, data source URLs) using existing `_validate_url` function
- File upload validation: MIME type checking, file size limits, malware scan via ClamAV (optional, Phase 2)
- Canvas project JSON is sanitized on load to prevent XSS via stored SVG/script injection
- Role-based access control enforced at the API level (not just UI)
- API rate limiting on asset creation/upload: 100 requests per minute per user
- Exported template/asset packages are signed with HMAC for integrity verification on import

### 4.4 Reliability

| Requirement | Target |
|---|---|
| Auto-save frequency (canvas editor) | Every 60 seconds |
| Data loss tolerance | Zero -- all changes must be persisted before confirmation |
| Asset file durability | Files stored on Docker volume mount; backup is the operator's responsibility |
| Graceful degradation | If an asset fails to load at stream time, FFmpeg skips it rather than failing the stream (existing behavior, maintained) |
| Database migration safety | All schema changes use Alembic migrations with rollback support |

### 4.5 Accessibility

- Canvas editor provides keyboard shortcuts for all major operations (Ctrl+Z undo, Ctrl+S save, Delete remove, arrow keys nudge)
- Color contrast ratios in the UI meet WCAG 2.1 AA standards
- Form fields have proper labels and ARIA attributes
- Template wizard steps are navigable via keyboard
- Asset library cards are navigable and actionable via keyboard

---

## 5. Technical Requirements

### 5.1 Technology Stack

**Required (existing)**
- Backend: Python 3.12+, FastAPI, SQLAlchemy, Pydantic
- Frontend: React 18, TypeScript, Tailwind CSS
- Database: SQLite (with WAL mode for concurrent access)
- Stream engine: FFmpeg (with filter_complex for overlay compositing)
- Deployment: Docker, Ubuntu

**New dependencies (to be added)**
- Frontend: Fabric.js v6 (MIT license) for canvas editor
- Frontend: @simonwep/pickr or react-colorful for color picker
- Backend: jsonpath-ng (for data binding JSON path extraction)
- Backend: Pillow (already present) for thumbnail generation of canvas exports

**Prohibited**
- No additional database engines (PostgreSQL, MySQL) -- SQLite only
- No WebSocket-based real-time collaboration (too complex for Phase 1; use optimistic locking instead)
- No server-side rendering of canvas -- all canvas rendering happens in the browser

### 5.2 Integrations

| Integration | Purpose | Protocol |
|---|---|---|
| TempestWeather API | Weather overlay data | HTTP REST, existing at `http://host.docker.internal:8036` |
| NOAA Tides/Currents API | Tide chart data | HTTP REST, `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter` |
| FFmpeg filter_complex | Overlay compositing at stream time | Process spawning, existing pipeline |
| Existing Asset API (`/api/assets`) | Extended with new endpoints | HTTP REST, backward-compatible |
| Existing Timeline system | Assets referenced by timeline overlay cues | SQLAlchemy relationships, existing |

### 5.3 Data Requirements

**New Database Tables**

| Table | Purpose | Key Fields |
|---|---|---|
| `overlay_templates` | Template definitions (catalog) | id, name, category, description, config_schema (JSON), default_config (JSON), preview_path, version |
| `template_instances` | Configured instances of templates | id, template_id (FK), asset_id (FK), config_values (JSON) |
| `canvas_projects` | Saved canvas editor projects | id, name, canvas_json (TEXT), thumbnail_path, width, height, created_by |
| `asset_versions` | Version history | id, asset_id (FK), version_number, metadata_snapshot (JSON), file_path |
| `asset_groups` | Asset grouping | id, name, description |
| `asset_group_members` | Group membership | id, group_id (FK), asset_id (FK), child_group_id (FK), display_order |
| `asset_schedules` | Independent asset schedules | id, asset_id (FK), schedule_type, config (JSON), is_enabled |
| `asset_display_log` | Analytics: display events | id, asset_id (FK), execution_id (FK), started_at, ended_at, duration_seconds |

**Existing Table Modifications**

| Table | Change |
|---|---|
| `assets` | Add columns: `template_instance_id` (FK, nullable), `animation_config` (JSON, nullable), `data_binding_config` (JSON, nullable), `group_id` (FK, nullable) |
| `assets` | Extend `type` enum to include: `data_bound`, `canvas_composite` |
| `users` | Add column: `role` (string, default "admin") |
| `timeline_cues.action_params` | Extend JSON schema to include animation configuration |

**Migration Strategy**
- All migrations via Alembic (existing migration framework)
- New tables are additive (no breaking changes to existing tables)
- Column additions use `nullable=True` or have defaults for backward compatibility
- Migration scripts tested against production database snapshot before deployment

### 5.4 Infrastructure

- No new infrastructure required; all features run within the existing Docker container
- Storage: asset files use the existing `/data/uploads/assets` Docker volume mount
- Canvas project thumbnails stored alongside asset uploads
- Template catalog files bundled in the Docker image at build time (`/app/templates/catalog/`)
- Estimated additional Docker image size: approximately 10MB (template assets and Fabric.js)

---

## 6. User Experience

### 6.1 Key User Journeys

**Journey 1: First-Time Overlay Setup (Template Path)**
1. User installs VistterStream, configures cameras, creates a timeline
2. User navigates to "Templates" in the main nav
3. User sees categorized template catalog with preview cards
4. User selects "Tempest Current Conditions" weather template
5. Wizard asks for Tempest station ID; user enters it
6. Wizard shows live preview of the overlay with real data
7. User adjusts position and size preferences
8. User clicks "Create" -- overlay asset is created
9. User navigates to Timeline Editor, adds the new asset to an overlay track
10. Overlay appears in the stream preview panel

**Journey 2: Custom Ad Creation (Canvas Editor Path)**
1. User navigates to Assets and clicks "Create in Canvas Editor"
2. Canvas editor opens with a 1920x1080 transparent canvas
3. User imports a sponsor logo (drag and drop)
4. User adds text: "Visit Bob's Bait Shop - Open Daily 6AM-6PM"
5. User adds a semi-transparent rounded rectangle behind the text
6. User arranges layers, adjusts colors, and positions elements
7. User clicks "Export as Asset" -- PNG is generated and saved as a new asset
8. User configures the asset with schedule: display Mon-Fri, 6am-6pm, rotate every 30 seconds with other sponsor ads

**Journey 3: Updating an Existing Overlay**
1. User navigates to Assets, finds "Marina Weather Widget"
2. User clicks Edit, makes changes to the configuration
3. System auto-saves previous version to version history
4. User saves changes; overlay updates on the next refresh cycle
5. User notices the change looks wrong on stream
6. User opens version history, previews previous version, clicks "Revert"
7. Previous version is restored (as a new version); stream displays the original

### 6.2 UI/UX Guidelines

**Consistent with existing VistterStream UI:**
- Dark theme (bg-dark-800, bg-dark-700 backgrounds)
- Primary accent color (primary-500/600/700)
- Tailwind CSS utility classes
- Heroicons for icons
- Modal-based forms for create/edit operations
- Card grid layout for asset browsing
- Toast notifications for success/error feedback (replace current `alert()` calls)

**Canvas Editor specific:**
- Floating toolbar (left side) for drawing tools
- Properties panel (right side) for selected object properties
- Layer panel (collapsible, right side) for z-order management
- Top toolbar for project actions (save, export, undo/redo, zoom)
- Canvas fills the remaining space
- Keyboard shortcuts match industry standards (Photoshop/Canva conventions)

**Template Catalog:**
- Card layout with large preview thumbnails
- Category tabs or sidebar filter
- Search bar with instant filtering
- Wizard flow: step-by-step with preview pane showing live result

### 6.3 Error Handling

| Error Scenario | User-Facing Behavior |
|---|---|
| Canvas export fails | "Export failed. Your project is saved -- try exporting again." with retry button |
| Template data source unreachable | Wizard shows inline error: "Could not connect to [source]. Check URL and try again." with test button |
| File upload exceeds size limit | "File too large (52MB). Maximum allowed is 50MB." with clear file size shown before upload attempt |
| Concurrent edit detected | "This asset was modified by [user] at [time]. Load their changes or overwrite?" |
| FFmpeg cannot render overlay | Skip overlay silently in stream; log error; show warning in dashboard: "Overlay [name] failed to render" |
| Import file corrupted | "Import failed: package is corrupted or incompatible. Expected version [X], found [Y]." |
| Database migration failure | Abort startup with clear log message; do not serve partial schema |

### 6.4 Navigation Changes

The main navigation currently has: Dashboard, Timeline, Assets, ReelForge, Settings.

**Updated navigation:**
- Dashboard
- Timeline
- **Assets** (existing, enhanced)
  - Asset Library (existing page, enhanced with groups and analytics)
  - **Canvas Editor** (new)
  - **Template Catalog** (new)
- ReelForge
- Settings

---

## 7. Dependencies and Assumptions

### 7.1 Dependencies

| Dependency | Impact if Unavailable |
|---|---|
| TempestWeather API (`host.docker.internal:8036`) | Weather templates cannot fetch data; show "Data Unavailable" fallback |
| NOAA Tides API | Tide chart templates cannot fetch data; show "Data Unavailable" fallback |
| Fabric.js npm package | Canvas editor cannot function; would need alternative library |
| FFmpeg with filter_complex support | Overlay compositing fails; streams run without overlays (graceful degradation) |
| Existing Asset API endpoints | New features build on top; breaking changes to existing endpoints would break everything |
| Docker volume mount (`/data`) | Asset file storage unavailable; uploads fail |
| Alembic migrations | Database schema changes cannot be applied; feature deployment blocked |

### 7.2 Assumptions

- The existing `api_image` asset type and proxy endpoint are stable and performant enough to support additional template-based overlays
- TempestWeather API will be extended to render additional overlay image formats (forecast, tide chart) -- or Phase 2 switches to `data_bound` rendering
- SQLite WAL mode provides sufficient concurrent access for multi-user editing scenarios (expected: 2-5 concurrent users maximum)
- The Docker container has sufficient CPU and memory to run the Fabric.js canvas editor in the browser while FFmpeg encodes streams (canvas runs client-side, so this is primarily a browser constraint)
- Users have modern browsers (Chrome 90+, Firefox 90+, Safari 15+, Edge 90+) for canvas editor compatibility
- The existing 50MB upload limit is sufficient for all asset types; canvas exports are typically 1-5MB
- FFmpeg filter graph complexity can support up to 10 simultaneous overlays at 1080p without dropping below real-time encoding on the target hardware

---

## 8. API Specification

### 8.1 New Endpoints

**Template Catalog**
```
GET    /api/templates                    # List all templates (catalog)
GET    /api/templates/{id}               # Get template details
POST   /api/templates/instances          # Create template instance (configure a template)
GET    /api/templates/instances          # List configured template instances
PUT    /api/templates/instances/{id}     # Update template instance configuration
DELETE /api/templates/instances/{id}     # Remove template instance
POST   /api/templates/export/{id}        # Export template as .vst-template
POST   /api/templates/import             # Import .vst-template file
```

**Canvas Editor**
```
GET    /api/canvas-projects              # List saved projects
POST   /api/canvas-projects              # Create new project
GET    /api/canvas-projects/{id}         # Load project (returns canvas JSON)
PUT    /api/canvas-projects/{id}         # Save project (auto-save and manual)
DELETE /api/canvas-projects/{id}         # Delete project
POST   /api/canvas-projects/{id}/export  # Export project as PNG asset
POST   /api/canvas-projects/{id}/duplicate  # Duplicate project
```

**Asset Extensions**
```
GET    /api/assets/{id}/versions         # Get version history
POST   /api/assets/{id}/revert/{version} # Revert to specific version
GET    /api/assets/{id}/analytics        # Get display analytics
GET    /api/assets/analytics/summary     # Get analytics summary across all assets
POST   /api/assets/{id}/schedule         # Set asset schedule
GET    /api/assets/{id}/schedule         # Get asset schedule
DELETE /api/assets/{id}/schedule         # Remove asset schedule
```

**Asset Groups**
```
GET    /api/asset-groups                 # List groups
POST   /api/asset-groups                 # Create group
GET    /api/asset-groups/{id}            # Get group with members
PUT    /api/asset-groups/{id}            # Update group
DELETE /api/asset-groups/{id}            # Delete group
POST   /api/asset-groups/{id}/members    # Add member to group
DELETE /api/asset-groups/{id}/members/{member_id}  # Remove member
```

**Asset Library Export/Import**
```
POST   /api/assets/export                # Export selected assets as .vst-assets
POST   /api/assets/import                # Import .vst-assets package
```

### 8.2 Extended Existing Endpoints

```
GET    /api/assets                       # Extended: add ?group_id, ?type, ?search, ?has_schedule filters
PUT    /api/assets/{id}                  # Extended: accepts animation_config, data_binding_config
POST   /api/assets                       # Extended: accepts new types (data_bound, canvas_composite)
```

---

## 9. Phased Delivery Plan

### Phase 1: Foundation (Weeks 1-3)

**Goal:** Template catalog MVP and canvas editor MVP. Users can browse templates, configure weather overlays, and create simple graphics in the canvas editor.

| Week | Deliverables |
|---|---|
| **Week 1** | Database migrations for new tables. Template catalog data model and seeder. Template catalog browser UI (read-only listing with previews). Weather template integration with TempestWeather (Current Conditions). |
| **Week 2** | Template configuration wizard framework. Weather template wizard (station ID, position, theme). Canvas editor: Fabric.js integration, basic tools (text, rectangle, image import), save/load projects. |
| **Week 3** | Canvas editor: export to PNG asset, layer panel, alignment guides. Template catalog: Lower Third template, Time/Date template. Testing and polish. |

**Exit Criteria:**
- User can browse template catalog and configure a Tempest weather overlay in under 5 minutes
- User can create a simple branded lower third in the canvas editor and export it as an asset
- All new API endpoints have test coverage
- Existing asset functionality is unaffected (backward compatibility verified)

### Phase 2: Lifecycle (Weeks 4-6)

**Goal:** Asset scheduling, version history, animation system. Users can schedule overlays to display at specific times and configure entrance/exit animations.

| Week | Deliverables |
|---|---|
| **Week 4** | Asset version history (auto-versioning on update, version list, revert). Asset scheduling data model and UI (time-of-day, day-of-week, rotation). |
| **Week 5** | Animation system: data model, configuration UI in timeline editor, FFmpeg filter implementation for fade in/out and slide animations. |
| **Week 6** | Responsive asset scaling implementation. Data binding MVP (data_bound type, template strings, TempestWeather JSON source). Testing and polish. |

**Exit Criteria:**
- User can schedule an asset to display Mon-Fri 6am-6pm
- User can configure fade-in/fade-out animations on overlay cues
- Version history tracks changes with revert capability
- Data-bound text overlay pulls live data from TempestWeather API

### Phase 3: Intelligence (Weeks 7-9)

**Goal:** Asset groups, analytics, import/export, multi-user permissions. Users can bundle assets, track display metrics, and manage team access.

| Week | Deliverables |
|---|---|
| **Week 7** | Asset groups: data model, UI for creating/managing groups, timeline integration. Import/export: asset library packages (.vst-assets format). |
| **Week 8** | Asset analytics: display logging, analytics dashboard, CSV export. Template import/export (.vst-template format). |
| **Week 9** | Multi-user roles: role column, API-level permission enforcement, UI adjustments. Canvas editor enhancements: more shapes, gradient fills, font selection. |

**Exit Criteria:**
- User can create a "Weather Widget" group containing 3 related overlay assets
- Analytics dashboard shows display time and impression counts per asset
- Templates can be exported and imported between VistterStream instances
- Designer role can create assets but cannot start streams

### Phase 4: Polish and Advanced Templates (Weeks 10-12)

**Goal:** Additional templates, advanced canvas features, performance optimization, and production hardening.

| Week | Deliverables |
|---|---|
| **Week 10** | Additional templates: Tide Chart (NOAA integration), Marine Weather, Sponsor/Ad Rotation. Canvas editor: text effects (shadow, outline), advanced shapes. |
| **Week 11** | Performance optimization: canvas editor rendering, FFmpeg filter graph efficiency with many overlays. Schedule conflict detection and visual calendar view. |
| **Week 12** | Toast notification system (replace all `alert()` calls). End-to-end testing. Documentation. Bug fixes. Production deployment. |

**Exit Criteria:**
- Template catalog has at least 8 templates across all categories
- Canvas editor handles 50+ objects at 60fps
- All `alert()` calls replaced with toast notifications
- Full test suite passes; no P0 bugs
- User documentation covers all new features

---

## 10. Open Questions

- [x] **SQLite scaling**: **Decision: Stay with SQLite.** User load will be low. Migrate to PostgreSQL only if scaling issues arise. WAL mode should be sufficient.
- [x] **Font management**: **Decision: Option C (both).** Support font upload API for custom brand fonts AND Google Fonts integration with caching. Maximum flexibility.
- [x] **TempestWeather rendering vs. data binding**: **Decision: Pre-rendered Phase 1, data binding Phase 2.** Weather templates use existing TempestWeather pre-rendered PNGs initially; data-bound text overlays added as an option in Phase 2.
- [x] **Canvas editor autosave**: **Decision: Both.** localStorage for instant recovery, server-side for durability. Dual autosave approach.
- [x] **Animation complexity in FFmpeg**: **Decision: Animations are post-MVP.** Keep overlays static for now. Animation support (entrance/exit transitions) will be added in a future phase after the core asset studio is solid. This simplifies the FFmpeg pipeline work significantly.
- [x] **Tide data source**: **Decision: Call NOAA API directly, no local caching.** NOAA rate limits are generous enough for single-instance use. Add caching later only if rate limits become an issue.
- [x] **Social media feed templates**: **Decision: Include as "Coming Soon" placeholder** in the catalog UI. No data source integration until a future phase.

---

## 11. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-03-15 | Nick DeMarco (AI-assisted) | Initial comprehensive PRD covering all three pillars |
| 1.1 | 2026-03-15 | Nick DeMarco (AI-assisted) | Resolved all 7 open questions: SQLite stays, both font options, pre-rendered weather Phase 1, dual autosave, animations post-MVP, no tide caching, social feeds as placeholder |
