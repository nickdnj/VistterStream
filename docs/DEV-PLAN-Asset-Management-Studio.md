# Development Plan: VistterStream Asset Management Studio

**Version:** 1.0
**Date:** 2026-03-15
**Status:** Draft — pending review before GitHub issue creation
**Source Documents:**
- PRD: `PRD-Asset-Management-Studio.md`
- Architecture: `ARCH-Asset-Management-Studio.md`
- UX Spec: `UX-Asset-Management-Studio.md`

---

## How to Read This Document

Tasks are organized by the 4 PRD delivery phases. Within each phase, tasks are split into **Backend** and **Frontend** tracks that can be worked in parallel. Each task has:

- **Size:** S (half-day), M (1-2 days), L (3-5 days), XL (1+ week)
- **Deps:** Task IDs that must complete before this one starts
- **Acceptance criteria** drawn directly from the PRD/UX spec

A dependency map and parallel-work summary follows each phase.

---

## Conventions and Codebase Context

### Existing Patterns to Follow

- Routers live in `backend/routers/` and follow `assets.py` conventions (APIRouter, Depends(get_current_user), Depends(get_db))
- Models are in `backend/models/database.py` (single file currently); new models should go in new files per the architecture doc and imported into `database.py`
- Pydantic schemas live in `backend/models/schemas.py`
- All migrations via Alembic with `render_as_batch=True` for SQLite
- Frontend components in `frontend/src/components/`; existing page components are at that level (e.g., `AssetManagement.tsx`, `TimelineEditor.tsx`)
- Tailwind dark theme: `bg-dark-800`, `bg-dark-700`, `primary-500/600/700` accents
- Toast notifications: currently using `alert()` — the plan targets replacing these in Phase 4

### New File Locations (per Architecture Doc)

```
backend/
  models/
    template.py       # OverlayTemplate, TemplateInstance
    canvas.py         # CanvasProject
    asset_ext.py      # AssetVersion, AssetSchedule, AssetDisplayLog, AssetGroup, AssetGroupMember
    font.py           # Font
  routers/
    templates.py      # Template catalog and instances
    canvas_projects.py
    fonts.py
    asset_groups.py   # Phase 3
  services/
    template_service.py
    canvas_project_service.py
    font_service.py
    asset_version_service.py
    asset_schedule_service.py
    asset_analytics_service.py  # Phase 3
    asset_group_service.py      # Phase 3
    import_export_service.py    # Phase 3

frontend/src/components/
  AssetStudio.tsx          # Container/tab bar
  AssetLibrary.tsx         # Enhanced AssetManagement.tsx
  TemplateCatalog.tsx
  TemplateWizard.tsx
  CanvasEditorPage.tsx
  canvas/
    FabricCanvas.tsx
    EditorToolbar.tsx
    ToolPanel.tsx
    PropertiesPanel.tsx
    LayerPanel.tsx
    LayerItem.tsx
    TextProperties.tsx
    ShapeProperties.tsx
    ImageProperties.tsx
    PositionProperties.tsx
    AlignmentGuides.tsx
    Rulers.tsx
    SafeZoneOverlay.tsx
    ColorPicker.tsx
    FontPicker.tsx
  shared/
    PositionPicker.tsx     # 9-grid position picker (UX 6.1)
    SlideOver.tsx          # Reusable right-side slide-over panel
    SkeletonCard.tsx       # Loading skeleton for asset/template grids
```

---

## Phase 1: Foundation (Weeks 1–3)

**Goal:** Template catalog MVP and canvas editor MVP. Users can browse templates, configure a weather overlay, and create a simple graphic in the canvas editor.

**Exit criteria:**
- User can browse template catalog, configure a Tempest weather overlay in under 5 minutes
- User can create a simple branded lower third in the canvas editor and export it as an asset
- All new API endpoints have test coverage
- Existing asset functionality is unaffected (backward compatibility verified)

---

### Phase 1 — Backend Track

#### B1.1 — Database migrations (Phase 1 tables)
**Size:** M | **Deps:** none

Create Alembic migrations for all Phase 1 database tables and column additions. All migrations use `render_as_batch=True`.

**Migrations to write:**
- `001_create_overlay_templates` — `overlay_templates`, `template_instances` tables
- `002_create_canvas_projects` — `canvas_projects` table
- `003_create_fonts` — `fonts` table
- `004_add_asset_template_link` — add `assets.template_instance_id` (FK nullable) and `assets.canvas_project_id` (FK nullable)
- `005_extend_asset_types` — app-level enum extension (no DB change for SQLite; update schema validation in `assets.py` to accept `canvas_composite`)

**Acceptance criteria:**
- [ ] Each migration runs cleanly against a copy of the current production DB
- [ ] Each migration has a working `downgrade()` path
- [ ] `alembic upgrade head` on a fresh DB applies all migrations without error
- [ ] Existing rows in `assets` table are unaffected (no data loss)
- [ ] WAL mode is confirmed enabled in the SQLAlchemy engine config

---

#### B1.2 — New SQLAlchemy models (Phase 1)
**Size:** M | **Deps:** B1.1

Create model files per architecture doc Section 7.4 and import them in `models/database.py`.

**Files to create:**
- `backend/models/template.py` — `OverlayTemplate`, `TemplateInstance`
- `backend/models/canvas.py` — `CanvasProject`
- `backend/models/font.py` — `Font`

**Extend existing:**
- `backend/models/database.py` — add `template_instance_id`, `canvas_project_id` FK columns to `Asset` model; add import statements for new models

**Acceptance criteria:**
- [ ] All models have correct relationships (OverlayTemplate -> TemplateInstance -> Asset; CanvasProject -> Asset)
- [ ] Models are importable without error
- [ ] SQLAlchemy `relationship()` back-populates are consistent in both directions
- [ ] The `Asset` model's type field accepts `canvas_composite` (update string validation or enum)

---

#### B1.3 — Template catalog seeder
**Size:** M | **Deps:** B1.2

Implement the startup seeder that populates `overlay_templates` from bundled JSON definition files.

**File structure to create:**
```
backend/templates/catalog/
  tempest_current_conditions/
    definition.json
    preview.png          (placeholder/real preview)
  tempest_forecast/
    definition.json
    preview.png
  lower_third_basic/
    definition.json
    preview.png
    default_canvas.json  (Fabric.js JSON starting canvas)
  time_date_display/
    definition.json
    preview.png
  sponsor_ad_slot/
    definition.json
    preview.png
```

Definition files follow the config schema design in architecture doc Section 7.5. The Tempest Current Conditions definition is the reference implementation (full schema shown there).

**Seeder behavior:**
- On startup, check if each bundled template exists in DB by `name` + `is_bundled=True`
- Insert if absent (idempotent — never duplicates)
- Update `preview_path` to point to the bundled file on disk
- Seeder called from `main.py` lifespan startup

**Acceptance criteria:**
- [ ] Seeder is idempotent (safe to run on every startup)
- [ ] Running seeder twice does not create duplicate template records
- [ ] All 5 initial templates are seeded correctly with valid `config_schema` JSON
- [ ] Preview PNG paths resolve to real files on disk
- [ ] Seeder is covered by an integration test

---

#### B1.4 — Template router and TemplateService
**Size:** L | **Deps:** B1.2, B1.3

Implement `backend/routers/templates.py` and `backend/services/template_service.py`.

**Endpoints to implement (Phase 1 subset):**
```
GET  /api/templates                  list templates (filter by ?category=)
GET  /api/templates/{id}             template detail with config_schema
POST /api/templates/instances        create configured template instance
GET  /api/templates/instances        list configured instances
PUT  /api/templates/instances/{id}   update instance configuration
DELETE /api/templates/instances/{id} delete instance (also soft-deletes linked asset)
```

**TemplateService responsibilities:**
- `list_templates(db, category=None)` — query with optional category filter
- `get_template(db, id)` — raises 404 if not found
- `validate_config(template, config_values)` — validate user input against `config_schema` field definitions (type checking, required fields, pattern matching, min/max for numbers)
- `instantiate_template(db, template_id, config_values, current_user)` — validate, merge with defaults, generate Asset record properties, create both `TemplateInstance` and `Asset` records; for Tempest templates, construct the correct TempestWeather `api_url`; return `asset_id`
- `update_instance(db, instance_id, config_values)` — re-validate, update both records

**Pydantic schemas to add to `schemas.py`:**
- `TemplateRead` (id, name, category, description, config_schema, default_config, preview_path, version)
- `TemplateInstanceCreate` (template_id, config_values: dict)
- `TemplateInstanceRead` (id, template_id, asset_id, config_values, created_at, updated_at)
- `TemplateInstanceUpdate` (config_values: dict)

**Business rules:**
- Template definitions are read-only via API (bundled; no user create/edit of definitions in Phase 1)
- Creating an instance creates an `Asset` of type `api_image` (for Tempest templates) or `canvas_composite` (for canvas-based templates)
- Deleting an instance soft-deletes the linked asset (`is_active = False`)

**Acceptance criteria:**
- [ ] `GET /api/templates` returns all active templates, filterable by category
- [ ] `GET /api/templates/{id}` returns full config_schema for wizard rendering
- [ ] `POST /api/templates/instances` with valid Tempest config creates both `TemplateInstance` and `Asset` records
- [ ] `POST /api/templates/instances` with missing required field returns 422 with field-level error detail
- [ ] `POST /api/templates/instances` with invalid station_id format (non-numeric) returns 422
- [ ] Created Tempest asset has correct `api_url` pointing to TempestWeather with station ID, theme, units params
- [ ] All endpoints require authentication
- [ ] Integration tests cover happy path, 404, and validation error cases

---

#### B1.5 — Canvas project router and CanvasProjectService
**Size:** L | **Deps:** B1.2

Implement `backend/routers/canvas_projects.py` and `backend/services/canvas_project_service.py`.

**Endpoints to implement:**
```
GET    /api/canvas-projects              list projects (active only, with thumbnail URLs)
POST   /api/canvas-projects              create new project (name, description, width, height)
GET    /api/canvas-projects/{id}         load project (returns full canvas_json)
PUT    /api/canvas-projects/{id}         save project (canvas_json, thumbnail_data base64)
DELETE /api/canvas-projects/{id}         soft delete (is_active = False)
POST   /api/canvas-projects/{id}/export  render PNG, create asset
POST   /api/canvas-projects/{id}/duplicate  clone project
```

**CanvasProjectService responsibilities:**
- `create_project(db, name, description, width, height, user_id)` — creates record with empty canvas JSON (blank Fabric.js state)
- `save_project(db, id, canvas_json, thumbnail_data)` — saves JSON, decodes base64 thumbnail and writes to `/data/uploads/canvas/{project_id}_thumb.png` using Pillow for validation
- `export_project(db, id, canvas_png_bytes, asset_name, user)` — saves PNG to `/data/uploads/assets/{uuid}.png`, creates `Asset` record with `type=canvas_composite`, `canvas_project_id=id`, returns asset_id
- `duplicate_project(db, id, user_id)` — creates new record with `name = "{original_name} (copy)"` and copied canvas_json, new timestamps

**Pydantic schemas:**
- `CanvasProjectCreate` (name, description, width=1920, height=1080)
- `CanvasProjectSave` (canvas_json: str, thumbnail_data: Optional[str] — base64 PNG)
- `CanvasProjectRead` (id, name, description, thumbnail_url, width, height, created_at, updated_at)
- `CanvasProjectDetail` (all CanvasProjectRead fields + canvas_json)
- `CanvasProjectExport` (asset_name: str)

**File storage:**
- Thumbnails: `/data/uploads/canvas/{project_id}_thumb.png`
- Exported PNGs: `/data/uploads/assets/{uuid}.png`
- Both directories created on first use

**Acceptance criteria:**
- [ ] Create, read, save, delete, duplicate work correctly
- [ ] Save endpoint handles both autosave calls (frequent) and manual saves without performance degradation
- [ ] Thumbnail data is validated as a valid PNG before writing (reject corrupt data gracefully)
- [ ] Export creates a new Asset record with `canvas_project_id` set and `type = "canvas_composite"`
- [ ] Soft delete returns 200; deleted project does not appear in list
- [ ] All endpoints require authentication
- [ ] Unit tests cover service methods; integration tests cover endpoints

---

#### B1.6 — Font router and FontService
**Size:** M | **Deps:** B1.2

Implement `backend/routers/fonts.py` and `backend/services/font_service.py`.

**Endpoints:**
```
GET  /api/fonts                 list available fonts (system + upload + google cached)
POST /api/fonts/upload          upload custom font file (.ttf, .otf, .woff2)
GET  /api/fonts/google          search Google Fonts catalog
POST /api/fonts/google/install  download and cache a Google Font
DELETE /api/fonts/{id}          remove uploaded/cached font (cannot remove system fonts)
```

**FontService responsibilities:**
- `scan_system_fonts()` — on startup, scan `/usr/share/fonts/` for installed fonts; register in DB with `source="system"` (idempotent)
- `upload_font(file, user)` — validate magic bytes (first 4 bytes for TTF: `\x00\x01\x00\x00` or `OTTO`; WOFF2: `wOF2`), save to `/data/fonts/uploads/{uuid}.{ext}`, extract font family/weight metadata, create `Font` record
- `search_google_fonts(query)` — call Google Fonts API `https://www.googleapis.com/webfonts/v1/webfonts` (requires API key or use CSS2 endpoint), return matching families
- `install_google_font(family, weights)` — download .ttf files from Google CDN, save to `/data/fonts/google/{family}/{weight}.ttf`, create `Font` records
- `list_fonts(db)` — return all active fonts grouped by source

**Docker additions (to be noted for deployment):**
- Add `fonts-liberation` and `fonts-dejavu-core` to Dockerfile apt install
- Add `/fonts` static file mount in `main.py`: `app.mount("/fonts", StaticFiles(directory=fonts_path), name="fonts")`

**Acceptance criteria:**
- [ ] System fonts are discovered and listed on startup
- [ ] Font upload validates magic bytes and rejects non-font files
- [ ] Font upload enforces 10MB size limit
- [ ] Google Fonts search returns results (mock in tests)
- [ ] Installed Google Fonts are served via `/fonts/google/{family}/{weight}.ttf`
- [ ] Font list endpoint returns system, uploaded, and Google fonts in a single response
- [ ] Integration tests cover upload happy path, invalid file rejection, and list endpoint

---

#### B1.7 — Asset router extensions (Phase 1)
**Size:** S | **Deps:** B1.4, B1.5

Extend the existing `backend/routers/assets.py` with Phase 1 additions.

**Changes:**
- Add `?type=`, `?search=` query parameters to `GET /api/assets` (existing endpoint)
- Accept `canvas_composite` as a valid asset type in `POST /api/assets` schema validation
- Add `template_instance_id` and `canvas_project_id` to `AssetRead` schema response
- Register new routers in `main.py`: `templates.router`, `canvas_projects.router`, `fonts.router`
- Mount `/fonts` static directory in `main.py`
- Call template seeder and font scanner in `main.py` lifespan startup
- Update CSP in `SecurityHeadersMiddleware` to allow Fabric.js canvas blob URLs, Google Fonts API, and font data URIs (per architecture doc Section 8.4)

**Acceptance criteria:**
- [ ] `GET /api/assets?type=canvas_composite` filters correctly
- [ ] `GET /api/assets?search=abc` filters by name/description (case-insensitive)
- [ ] New asset types do not break existing asset endpoints
- [ ] All new routers are mounted and accessible
- [ ] CSP header allows `blob:`, `data:` for images and `https://fonts.googleapis.com` for connect-src

---

#### B1.8 — Backend tests (Phase 1)
**Size:** M | **Deps:** B1.4, B1.5, B1.6, B1.7

Write test coverage for all Phase 1 backend work.

**Test files:**
- `backend/tests/test_templates.py` — endpoint + service tests
- `backend/tests/test_canvas_projects.py` — endpoint + service tests
- `backend/tests/test_fonts.py` — endpoint + service tests
- `backend/tests/test_migrations.py` — up/down for each migration

**Coverage targets:**
- Template: catalog list, detail, instance create (valid/invalid), instance update, delete
- Canvas: create, load, save, export, duplicate, soft delete
- Font: system scan, upload valid, upload invalid (wrong magic bytes), google search (mocked), list
- Seeder: idempotency (run twice, count unchanged)

**Acceptance criteria:**
- [ ] All new endpoints have at least one happy-path test and one error-path test
- [ ] Template config validation is tested with boundary values (missing required, invalid pattern, out-of-range number)
- [ ] Canvas export test verifies both the PNG file and the Asset record are created
- [ ] Migration downgrade tests restore the original schema

---

### Phase 1 — Frontend Track

#### F1.1 — Navigation update and Asset Studio shell
**Size:** M | **Deps:** none (can start in parallel with backend)

Update `Layout.tsx` sidebar navigation and create the `AssetStudio.tsx` container with tab routing.

**Changes to `Layout.tsx`:**
- Replace the existing single "Assets" link with an expandable "Assets" section
- Sub-items: Library (maps to existing `/assets`), Canvas Editor (`/assets/editor`), Templates (`/assets/templates`)
- Use `SwatchIcon` or `RectangleGroupIcon` from Heroicons for the parent nav item
- Match existing nav item styling patterns (active state, hover state, collapse behavior)

**Create `frontend/src/components/AssetStudio.tsx`:**
- Container component that renders the tab bar: My Assets | Template Catalog | Canvas Editor | Analytics
- Tab bar uses horizontal pills/tabs consistent with existing VistterStream tab patterns
- Active tab indicated by `border-b-2 border-primary-600` (or existing tab pattern)
- Routes: tab switches update URL (`/assets`, `/assets/templates`, `/assets/editor`, `/assets/analytics`)
- Each tab renders its child component (AssetLibrary, TemplateCatalog, CanvasEditorPage, AnalyticsDashboard)

**Add routes in `App.tsx`:**
```
/assets           -> AssetStudio (My Assets tab default)
/assets/templates -> AssetStudio (Template Catalog tab active)
/assets/editor    -> AssetStudio (Canvas Editor tab active, shows project list/new project)
/assets/editor/:id -> CanvasEditorPage (full-page, no tab bar)
/assets/analytics -> AssetStudio (Analytics tab active)
```

**Acceptance criteria:**
- [ ] Navigation renders correctly with expanded sub-items
- [ ] Active nav item is highlighted
- [ ] Navigating to each tab URL shows the correct tab as active
- [ ] Existing routes (Dashboard, Timelines, etc.) are unaffected
- [ ] Canvas Editor route (`/assets/editor/:id`) is full-page (no Asset Studio tab bar)
- [ ] Browser back/forward navigation works correctly between tabs

---

#### F1.2 — Asset Library enhancements (My Assets tab)
**Size:** M | **Deps:** F1.1

Enhance the existing `AssetManagement.tsx` (rename or replace with `AssetLibrary.tsx`) to match the UX spec My Assets layout.

**Changes:**
- Add sub-filter chip row: All | Images | Videos | API Images | Templates | Groups | Canvas Projects
- Add "New Canvas Project" secondary button to toolbar (alongside existing "New Asset")
- Skeleton loading state for asset cards (dark shimmer rectangles, same count as last render)
- Empty state: icon + "No overlays yet" message + two CTAs: "Browse Template Catalog" (tab switch) + "New Canvas Project"
- Enhanced asset card (per UX spec 5.1):
  - "Scheduled" green dot badge on preview area (top-left) when `has_schedule = true`
  - Version number + "Last edited X ago" in card metadata
  - Add "Schedule" button to card footer (opens slide-over Schedule tab)
  - Add "History" button to card footer (opens slide-over History tab)
  - Overflow menu: Duplicate, Test Connection (if api_image type), Export, Delete
- Connect sub-filter chips to `GET /api/assets?type=` query param
- Connect search input to `GET /api/assets?search=` (debounced, 300ms)

**Acceptance criteria:**
- [ ] Sub-filter chips filter the grid without page reload
- [ ] Search input filters assets by name/description (debounced)
- [ ] Empty state shows both CTAs and "Browse Template Catalog" navigates to the template tab
- [ ] Skeleton cards render during initial load
- [ ] Enhanced card fields (scheduled badge, version, last-edited) render correctly
- [ ] "New Canvas Project" button opens the new project dialog (see F1.5)
- [ ] Existing asset create/edit/delete functionality is unbroken

---

#### F1.3 — Shared SlideOver component
**Size:** S | **Deps:** F1.1

Create a reusable `SlideOver.tsx` component for right-side slide-over panels (used for template config wizard, asset detail, version history, scheduling).

**Props:**
- `isOpen: boolean`
- `onClose: () => void`
- `title: string`
- `subtitle?: string` (e.g., category badge)
- `width?: number` (default 480px for templates, 520px for asset detail)
- `children: ReactNode`
- `footer?: ReactNode` (sticky footer for action buttons)

**Behavior:**
- Slides in from the right on `isOpen = true`
- Backdrop overlay (semi-transparent dark) closes on click
- Escape key closes
- Scrollable content area; sticky footer
- CSS transition: `transform translate-x-full` -> `translate-x-0` with `transition-transform duration-300`
- Does not navigate; purely a UI overlay

**Acceptance criteria:**
- [ ] Opens and closes with smooth transition
- [ ] Backdrop closes on click
- [ ] Escape key closes
- [ ] Content scrolls independently of sticky footer
- [ ] Renders correctly at 480px and 520px widths
- [ ] Multiple instances do not conflict (only one is open at a time)

---

#### F1.4 — Shared PositionPicker component
**Size:** S | **Deps:** none

Create the 9-grid position picker component described in UX spec Section 6.1. This replaces raw X/Y float inputs for non-technical users.

**Props:**
- `value: { x: number, y: number }` (normalized 0.0–1.0)
- `onChange: (value: { x: number, y: number }) => void`
- `showRawInputs?: boolean` (default false; shows the raw X/Y inputs alongside for power users)

**Position map (9 cells -> normalized coords):**
- TL: (0.02, 0.02) | TC: (0.5, 0.02) | TR: (0.97, 0.02)
- ML: (0.02, 0.5) | MC: (0.5, 0.5) | MR: (0.97, 0.5)
- BL: (0.02, 0.97) | BC: (0.5, 0.97) | BR: (0.97, 0.97)

**Acceptance criteria:**
- [ ] Clicking a cell updates `value` to the mapped coordinates
- [ ] Currently selected cell is highlighted with `primary-600` fill
- [ ] Changing value prop from outside updates the selected cell
- [ ] When `showRawInputs=true`, X/Y inputs appear and update on cell click
- [ ] Accessible: cells are keyboard-navigable with arrow keys

---

#### F1.5 — Template Catalog tab
**Size:** L | **Deps:** F1.1, F1.3, B1.4 (API)

Implement `TemplateCatalog.tsx` per UX spec Section 5.2.

**Components:**
- Search bar (filters template name/description client-side; templates loaded once per session)
- Category chip filter row: All | Weather | Marine | Time/Date | Sponsor/Ad | Lower Thirds | Social Media (lock icon) | Custom
- Template card grid (3-col desktop, 2-col tablet, 1-col mobile)
- "Coming Soon" card variant (semi-transparent overlay, lock icon, "Notify Me" placeholder button)
- Template detail slide-over (open on "Use Template" click)

**Template card (UX spec 5.2):**
```
[Thumbnail 16:9]
[CATEGORY BADGE]
Template Name
Brief description (2 lines)
Requires: [required field summary]
★★★★☆  12 uses        (uses count from template_instances count)
[ Use Template ]
```

**Template detail slide-over:**
- Full-width preview thumbnail at top
- Dynamic form rendered from `config_schema.fields` array
- Field types to render: `text`, `select`, `position_picker` (use F1.4 component), `number` (slider or input), `size_picker`
- Required fields marked with asterisk
- "Test Connection" button for templates with a testable data source (Tempest station ID)
  - Calls `POST /api/templates/test` (or validate the station against TempestWeather inline)
  - States: default / loading / success (green + station name) / error (red + message)
- Live preview: thumbnail updates when Test Connection succeeds
- Sticky footer: Cancel + Create Asset
- On submit: `POST /api/templates/instances` -> success toast + navigate to My Assets tab

**Acceptance criteria:**
- [ ] All 5 seeded templates display with correct thumbnails
- [ ] Category filter chips filter the grid correctly; multi-select is supported
- [ ] Search filters by name and description instantly
- [ ] Social Media category shows templates with "Coming Soon" overlay
- [ ] Slide-over renders form fields based on config_schema dynamically (not hardcoded per template)
- [ ] Required fields prevent submission when empty
- [ ] Test Connection works for Tempest templates (success and error states)
- [ ] Creating an instance via the wizard shows a success toast and the new asset appears in My Assets
- [ ] "Notify Me" button on Coming Soon templates shows a stub confirmation (no backend action)

---

#### F1.6 — Canvas Editor page (Phase 1 MVP)
**Size:** XL | **Deps:** F1.1, F1.3, B1.5 (API)

Implement the full-page canvas editor at `/assets/editor/:id` and `/assets/editor/new`. This is the largest single frontend task.

**Phase 1 scope (not full feature set — see Phase 3 for enhancements):**
- Fabric.js initialized on a transparent 1920x1080 canvas (or configured resolution)
- Tools: Select (V), Text (T), Rectangle (R), Circle/Ellipse (C), Line, Image Import
- Properties panel (right, 280px): position, size, rotation, opacity; shape fill/border; text font/size/color/style
- Layer panel (left, 240px): z-order list, visibility toggle, lock toggle, rename (double-click), select by clicking
- Top breadcrumb bar: project name, save state indicator (Saved / Saving... / Unsaved changes), Export button, Save button
- Undo/redo: 50 levels using `CanvasHistoryManager` class (per architecture doc Section 6.3)
- Dual autosave: localStorage every 10 seconds + server PUT every 60 seconds
- Export dialog: filename, PNG format, resolution display, "Save as Asset" option
- New project dialog (before editor opens): name, description, canvas size picker
- Keyboard shortcuts: Ctrl+Z (undo), Ctrl+Shift+Z (redo), Ctrl+S (save), Delete (delete selected), Ctrl+D (duplicate), V/T/R/C (tool shortcuts)

**npm dependencies to install:**
- `fabric@^6` — canvas rendering library
- `react-colorful@^5` — color picker

**Component files to create (per architecture doc Section 6.2):**
- `CanvasEditorPage.tsx` — page layout, state orchestration
- `canvas/FabricCanvas.tsx` — Fabric.js canvas wrapper using `useRef`; all Fabric.js event bindings live here
- `canvas/EditorToolbar.tsx` — breadcrumb + project name + save state + export/save buttons
- `canvas/ToolPanel.tsx` — left drawing tool buttons
- `canvas/PropertiesPanel.tsx` — right properties (delegates to sub-panels below)
- `canvas/TextProperties.tsx` — font, size, color, bold/italic/underline, alignment, shadow, stroke, background
- `canvas/ShapeProperties.tsx` — fill, stroke, corner radius, opacity
- `canvas/ImageProperties.tsx` — opacity, flip H/V, blend mode
- `canvas/PositionProperties.tsx` — X, Y, W, H, rotation, aspect lock
- `canvas/LayerPanel.tsx` — z-order list
- `canvas/LayerItem.tsx` — individual layer row (eye icon, lock icon, name, type icon, overflow menu)
- `canvas/ColorPicker.tsx` — react-colorful wrapper with hex input and preset swatches
- `canvas/FontPicker.tsx` — searchable font dropdown, loads fonts from `GET /api/fonts`

**State management (per architecture doc Section 6.3):**
- Fabric.js canvas is the source of truth for object state
- React state tracks: selected object (synced from Fabric.js selection events), tool selection, panel visibility, project metadata (name, dirty flag), zoom level

**Known Fabric.js integration points:**
- Use `useRef` for the canvas element; initialize Fabric.js in `useEffect` with cleanup
- Sync layer list from `canvas.getObjects()` on every Fabric.js `object:added`, `object:removed`, `object:modified` event
- Sync selected object to React state on Fabric.js `selection:created`, `selection:updated`, `selection:cleared`
- Use Fabric.js `canvas.toDataURL('image/png')` for export
- Use `canvas.toJSON()` / `canvas.loadFromJSON()` for save/load

**Acceptance criteria:**
- [ ] New project dialog opens before editor; project is created via API on "Create"
- [ ] Canvas initializes with the correct dimensions and transparent background (checkerboard pattern)
- [ ] Text tool: click to place text, double-click to edit inline, properties panel shows text controls
- [ ] Rectangle tool: click-drag to draw; fill color, border, opacity editable in properties
- [ ] Circle tool: click-drag to draw ellipse
- [ ] Image import: file picker opens, selected image is added to canvas as a new layer
- [ ] Image import: drag-and-drop from OS onto canvas adds image as new layer
- [ ] Layer panel: all objects listed in z-order (top of list = top of canvas)
- [ ] Layer panel: visibility toggle hides/shows object on canvas
- [ ] Layer panel: lock toggle prevents selection/editing of object
- [ ] Layer panel: double-click name enters inline edit mode
- [ ] Layer panel: clicking row selects the corresponding canvas object
- [ ] Undo/redo works for all add/delete/modify operations (at least 50 levels)
- [ ] Autosave fires every 60 seconds with "Saving..." indicator; localStorage save every 10 seconds
- [ ] Manual Save button triggers immediate server save
- [ ] Export dialog opens, allows naming, format choice (PNG), and "Save as Asset" option
- [ ] Export creates a new Asset record and shows success toast with "View in My Assets" link
- [ ] Keyboard shortcuts work: V, T, R, C (tools), Ctrl+Z/Shift+Z (undo/redo), Delete (remove), Ctrl+S (save)
- [ ] Navigating away with unsaved changes shows a confirmation prompt
- [ ] Editor loads an existing project from API and populates canvas from stored JSON

---

#### F1.7 — Frontend integration and polish (Phase 1)
**Size:** S | **Deps:** F1.2, F1.5, F1.6

Integration work and polish to finish Phase 1.

**Tasks:**
- Wire up "New Canvas Project" button in AssetLibrary to open the new project dialog from F1.6
- Wire up "Edit in Canvas Editor" action on canvas_composite asset cards (opens `/assets/editor/{canvas_project_id}`)
- Confirm template-created assets appear immediately in My Assets after wizard completion (refresh or optimistic update)
- Add toast notification system if not already present (can be a simple fixed-position toast using React state for Phase 1; full replacement of `alert()` in Phase 4)
- Verify backward compatibility: all existing asset operations (upload, edit, delete, test connection) still work

**Acceptance criteria:**
- [ ] End-to-end flow: Template Catalog -> configure weather template -> see asset in My Assets
- [ ] End-to-end flow: New Canvas Project -> add text + image + shape -> Export -> asset in My Assets
- [ ] No regressions in existing asset management functionality
- [ ] Toast notifications appear for success/error states in template wizard and canvas export

---

### Phase 1 — Dependency Map

```
B1.1 (migrations)
  └── B1.2 (models)
        ├── B1.3 (seeder)
        │     └── B1.4 (template router)
        ├── B1.5 (canvas router)
        ├── B1.6 (font router)
        └── B1.7 (asset router ext.)

B1.4, B1.5, B1.6, B1.7 -> B1.8 (tests)

F1.1 (nav + shell) [no backend dep — start immediately]
  ├── F1.2 (asset library) [uses existing API]
  ├── F1.3 (SlideOver) [no API dep]
  ├── F1.5 (template catalog) [needs B1.4]
  └── F1.6 (canvas editor) [needs B1.5]

F1.4 (PositionPicker) [no deps — start anytime]
F1.7 (integration) [needs F1.2, F1.5, F1.6]
```

**Parallel work opportunities:**
- Backend track (B1.1 -> B1.8) and frontend track (F1.1 -> F1.4) can run fully in parallel for the first week
- F1.5 (Template Catalog) needs B1.4 for the API; frontend can use mock data until B1.4 is ready
- F1.6 (Canvas Editor) needs B1.5 for save/load; the canvas editing experience itself has no backend dependency — Fabric.js can be integrated with localStorage-only save until B1.5 is ready

---

## Phase 2: Lifecycle (Weeks 4–6)

**Goal:** Asset scheduling, version history, and live data bindings. Users can schedule overlays to display at specific times and track asset versions.

**Note:** Animations are confirmed post-MVP (ADR-006). They are not included in this phase.

**Exit criteria:**
- User can schedule an asset to display Mon-Fri 6am-6pm
- Version history tracks changes with revert capability
- Data-bound text overlay pulls live data from TempestWeather API

---

### Phase 2 — Backend Track

#### B2.1 — Database migrations (Phase 2 tables)
**Size:** S | **Deps:** B1.8 (Phase 1 complete)

Create Alembic migrations for Phase 2 tables.

**Migrations:**
- `006_create_asset_versions` — `asset_versions` table
- `007_create_asset_schedules` — `asset_schedules` table
- `008_add_data_binding` — add `assets.data_binding_config` (JSON, nullable)

**Acceptance criteria:**
- [ ] Each migration runs cleanly against a Phase 1 DB state
- [ ] Downgrade paths restore Phase 1 DB state
- [ ] No impact on existing `assets` rows

---

#### B2.2 — New SQLAlchemy models (Phase 2)
**Size:** S | **Deps:** B2.1

Create `backend/models/asset_ext.py` with `AssetVersion`, `AssetSchedule`, `AssetDisplayLog` (preview — log table created in Phase 2 even though analytics display is Phase 3).

Add `data_binding_config` JSON column to `Asset` model in `database.py`.

**Acceptance criteria:**
- [ ] Models are correctly defined with relationships to `Asset`
- [ ] `AssetDisplayLog` references `timeline_executions.id` FK correctly
- [ ] All models importable without error

---

#### B2.3 — Asset versioning (AssetVersionService + router extension)
**Size:** M | **Deps:** B2.2

Implement `backend/services/asset_version_service.py` and extend `backend/routers/assets.py` with versioning endpoints.

**Service responsibilities:**
- `create_version_snapshot(db, asset, user_id, change_description=None)` — called as a pre-save hook in the asset update path
  - Snapshot current asset state to `metadata_snapshot` JSON
  - If file-based asset: copy file to `/data/uploads/assets/versions/{asset_id}/{version_number}/{filename}`
  - Create `AssetVersion` record with the next version number
  - If version count > 50 for this asset: delete the oldest version record and its file copy
- `get_version_history(db, asset_id)` — return list of versions, most recent first
- `revert_to_version(db, asset_id, version_number, user_id)` — load snapshot, apply to Asset record, copy versioned file back to active path; this creates a NEW version (does not overwrite)

**Router additions to `assets.py`:**
```
GET  /api/assets/{id}/versions          version history list
POST /api/assets/{id}/revert/{version}  revert to version
```

**Hook into existing update path:**
- In `PUT /api/assets/{id}` handler, call `create_version_snapshot()` before applying the update

**Pydantic schemas:**
- `AssetVersionRead` (id, version_number, created_at, created_by, change_description, thumbnail_path, metadata_snapshot)

**Acceptance criteria:**
- [ ] Updating an asset creates a new version record automatically
- [ ] Version snapshot includes all asset fields at time of snapshot (not just changed fields)
- [ ] File-based assets have their file copied to the versioned directory on update
- [ ] `GET /api/assets/{id}/versions` returns versions newest-first
- [ ] Reverting to version 3 creates a new version N with version 3 content, not overwriting v3
- [ ] Version count is capped at 50; oldest purged when exceeded
- [ ] Unit tests cover: snapshot creation, file copy, version limit, revert

---

#### B2.4 — Asset scheduling (AssetScheduleService + router extension)
**Size:** M | **Deps:** B2.2

Implement `backend/services/asset_schedule_service.py` and extend `backend/routers/assets.py` with schedule endpoints.

**Service responsibilities:**
- `set_schedule(db, asset_id, schedule_type, config)` — create or update `AssetSchedule` record; validate config matches expected shape for schedule_type
- `get_schedule(db, asset_id)` — return schedule or None
- `delete_schedule(db, asset_id)` — remove schedule record
- `is_active_now(db, asset_id, reference_time=None)` — core evaluation logic:
  - `always_on`: return True
  - `time_window`: parse `days_of_week`, `start_time`, `end_time`, `timezone` from config; evaluate against reference_time (default `datetime.now()` in asset's configured timezone); return True if current time is in window
  - `rotation`: for rotation groups, this service does not decide which asset in the group is shown — that is handled by the stream executor's rotation logic (rotation management TBD as future work)

**Router additions to `assets.py`:**
```
POST   /api/assets/{id}/schedule   create/update schedule
GET    /api/assets/{id}/schedule   get schedule (404 if none)
DELETE /api/assets/{id}/schedule   remove schedule
```

**Schedule config validation:**
- `time_window` requires: `timezone` (valid IANA timezone), `days_of_week` (list of 0-6), `start_time` and `end_time` (HH:MM format), optional `rotation`
- `always_on` requires no additional fields
- `rotation` requires: `interval_seconds` (positive int), `group_name` (string)

**FFmpeg pipeline hook (stream-time enforcement):**
- Add a call to `AssetScheduleService.is_active_now()` in `SeamlessTimelineExecutor._build_overlay_filters()` in `stream-engine/` (or equivalent) to skip scheduled-off assets
- This change must be backward-compatible: assets without a schedule are always included

**Acceptance criteria:**
- [ ] `POST /api/assets/{id}/schedule` with `time_window` config saves correctly
- [ ] `is_active_now()` returns False when current time is outside the configured window
- [ ] `is_active_now()` handles timezone correctly (test with non-UTC timezone)
- [ ] `is_active_now()` returns True for `always_on` regardless of time
- [ ] FFmpeg executor skips assets where `is_active_now()` returns False
- [ ] Schedule CRUD endpoints all require authentication
- [ ] Unit tests cover `is_active_now()` across all schedule types and edge cases (midnight crossover, DST transitions)

---

#### B2.5 — Live data bindings (data_bound asset type)
**Size:** L | **Deps:** B2.2

Implement the `data_bound` asset type that binds text overlays to JSON API data sources.

**New asset type behavior:**
- `data_bound` assets have a `data_binding_config` JSON column (see PRD Section 3.3.3 for schema)
- The backend periodically fetches data from the `source_url`, extracts values using JSON path expressions (`jsonpath-ng` library), fills the template string, and either:
  - Pre-renders the text as a PNG overlay (stored as a file, updated on refresh) — **simpler approach for Phase 2**
  - Or exposes a render endpoint for FFmpeg to fetch on-demand
- Use the simpler approach: a background task fetches and re-renders the overlay image on the configured `refresh_interval_seconds`

**Implementation:**
- Add `jsonpath-ng` to `requirements.txt`
- Create a background refresh task in `main.py` lifespan that runs on a schedule (check all data_bound assets every 30 seconds; re-render if past their refresh interval)
- Use Pillow to render text onto a transparent PNG using system fonts from `/data/fonts/`
- Save rendered PNG to `/data/uploads/assets/{asset_id}_rendered.png`; update asset `file_path` on each render
- SSRF validation: all `source_url` values must pass the existing `_validate_url()` check
- Fallback: if fetch fails, use `fallback_values` from the binding config; if no fallback, skip re-render (keep existing image)

**API additions:**
- `POST /api/assets/{id}/test-binding` — test data source connectivity and preview the template string output (for the wizard "Test" button)
- Extend `POST /api/assets` to accept `type = "data_bound"` with `data_binding_config`

**Pydantic schemas:**
- `DataBindingConfig` (bindings: list of binding objects, template: str, font: str, font_size: int, font_color: str, background_color: str, position: str)
- `DataBindingTest` request/response schemas

**Acceptance criteria:**
- [ ] Creating a `data_bound` asset with a valid TempestWeather URL renders a PNG within 30 seconds
- [ ] The rendered PNG is served by FFmpeg as a normal overlay
- [ ] Template strings with `{{field}}` placeholders are correctly filled from JSON path extraction
- [ ] `is_active_now()` and refresh logic do not conflict (data refresh is independent of scheduling)
- [ ] SSRF validation blocks `127.0.0.1`, `10.x.x.x`, `host.docker.internal` as source URLs
- [ ] Fallback values are used when the data source is unreachable
- [ ] `POST /api/assets/{id}/test-binding` returns extracted field values and rendered template preview string

---

#### B2.6 — Backend tests (Phase 2)
**Size:** M | **Deps:** B2.3, B2.4, B2.5

**Test files:**
- `backend/tests/test_asset_versions.py` — snapshot, file copy, version limit, revert
- `backend/tests/test_asset_schedules.py` — CRUD, `is_active_now()` unit tests (timezone handling, DST, midnight crossover)
- `backend/tests/test_data_binding.py` — fetch, JSON path extraction, template rendering, SSRF validation, fallback

**Acceptance criteria:**
- [ ] `is_active_now()` is tested with at least 10 time scenarios including edge cases
- [ ] Data binding SSRF test covers all blocked network ranges
- [ ] Version revert test verifies file system state as well as DB state

---

### Phase 2 — Frontend Track

#### F2.1 — Asset detail slide-over (Settings + Schedule + History tabs)
**Size:** L | **Deps:** F1.3 (SlideOver), B2.3, B2.4

Implement the asset detail slide-over as described in UX spec Section 5.4. This replaces or supplements the current asset edit flow.

**Tab 1 — Settings:**
- Preview thumbnail (16:9 aspect ratio)
- Name and description fields
- Position picker (use F1.4 PositionPicker component) + raw X/Y inputs alongside
- Width/height inputs + opacity slider
- Save/Delete/Cancel buttons in sticky footer

**Tab 2 — Schedule:**
- Schedule type selector: Always On / Time Window / Rotation Group (radio buttons)
- Time Window controls (conditional): days-of-week checkboxes (M T W T F S S), start time + end time inputs, timezone display
- Rotation Group controls (conditional): group name input, rotation interval slider (5-300s), asset member list with "Remove" buttons, "Add asset to group" multi-select picker
- Weekly calendar preview grid (7-day x hourly visualization, shaded for active hours)
- Save Schedule / Remove Schedule buttons

**Tab 3 — History:**
- List of `AssetVersion` records (newest first)
- Each entry: version number, timestamp, who changed it (username), change_description, thumbnail
- Current version labeled "Current" with no action buttons
- Older versions: "Preview" (opens version thumbnail in a lightbox or expanded state) + "Revert to vN" button
- Revert confirmation: "This creates a new version (vN+1) with vN content. Current version is not deleted."
- Success toast after revert: "Reverted to version N."

**Acceptance criteria:**
- [ ] All three tabs render and switch correctly without closing the slide-over
- [ ] Settings tab save triggers `PUT /api/assets/{id}` and shows success toast
- [ ] Schedule tab save calls `POST /api/assets/{id}/schedule` correctly for each schedule type
- [ ] Schedule tab "Remove Schedule" calls `DELETE /api/assets/{id}/schedule` with confirmation
- [ ] Weekly calendar preview updates reactively when days/hours change
- [ ] History tab lists versions from API; "Revert" shows confirmation before calling API
- [ ] Reverting to a version refreshes the asset in My Assets grid

---

#### F2.2 — Data binding wizard (data_bound asset creation)
**Size:** M | **Deps:** F1.3, B2.5

Add a "Create Data Binding" path to the asset creation flow (or as a new template category "Data Bound" in the Template Catalog with a wizard).

**UX approach:** Add a new template entry in the Template Catalog called "Live Data Overlay" under a "Data" category (or extend the existing wizard framework). When configured:
- URL input for data source
- "Test Connection" button (calls `POST /api/assets/{id}/test-binding` after first fetch)
- JSON path inputs for extracting fields (key name + JSON path expression)
- Template string editor with `{{field}}` placeholder syntax + live preview of filled string
- Font/color/position controls
- Fallback values per field

**Acceptance criteria:**
- [ ] User can create a data_bound asset pointed at TempestWeather
- [ ] "Test Connection" shows extracted values from the API
- [ ] Template preview shows the filled string with real values
- [ ] Fallback values are configurable per field
- [ ] Created asset renders correctly in My Assets

---

#### F2.3 — Frontend tests (Phase 2)
**Size:** S | **Deps:** F2.1, F2.2

**Tests to write:**
- `AssetDetailSlideOver.test.tsx` — tab switching, schedule form validation, history revert flow
- `DataBindingWizard.test.tsx` — form validation, test connection states
- `ScheduleCalendarPreview.test.tsx` — calendar renders correct shaded hours

---

### Phase 2 — Dependency Map

```
B1.8 (Phase 1 complete)
  └── B2.1 (migrations)
        └── B2.2 (models)
              ├── B2.3 (versioning)
              ├── B2.4 (scheduling)
              └── B2.5 (data binding)

B2.3, B2.4, B2.5 -> B2.6 (tests)

F1.3 (SlideOver — Phase 1)
  └── F2.1 (asset detail) [needs B2.3, B2.4]

F2.2 (data binding wizard) [needs B2.5]
F2.1, F2.2 -> F2.3 (tests)
```

---

## Phase 3: Intelligence (Weeks 7–9)

**Goal:** Asset groups, analytics dashboard, import/export, and multi-user role-based permissions.

**Exit criteria:**
- User can create a "Weather Widget" group containing 3 related overlay assets
- Analytics dashboard shows display time and impression counts per asset
- Templates can be exported and imported between VistterStream instances
- Designer role can create assets but cannot start streams

---

### Phase 3 — Backend Track

#### B3.1 — Database migrations (Phase 3 tables)
**Size:** S | **Deps:** B2.6

**Migrations:**
- `009_create_asset_groups` — `asset_groups`, `asset_group_members` tables
- `010_create_display_log` — `asset_display_log` table
- `011_add_user_roles` — add `users.role` column (string, default `"admin"`)

---

#### B3.2 — New SQLAlchemy models (Phase 3)
**Size:** S | **Deps:** B3.1

Add `AssetGroup`, `AssetGroupMember` to `asset_ext.py`. These are already shown in architecture doc Section 7.4. Add the `role` column to the `User` model in `database.py`.

---

#### B3.3 — Asset groups (AssetGroupService + router)
**Size:** M | **Deps:** B3.2

Create `backend/routers/asset_groups.py` and `backend/services/asset_group_service.py`.

**Endpoints:**
```
GET    /api/asset-groups               list groups
POST   /api/asset-groups               create group
GET    /api/asset-groups/{id}          group with members (eager load)
PUT    /api/asset-groups/{id}          update name/description
DELETE /api/asset-groups/{id}          soft delete
POST   /api/asset-groups/{id}/members  add member (asset_id or child_group_id)
DELETE /api/asset-groups/{id}/members/{member_id}  remove member
```

**Business rules:**
- Groups can contain assets and/or child groups (max nesting depth: 3)
- Deleting a group does not delete member assets (only removes membership)
- Adding a group to a timeline (in existing timeline system) should add all member assets at their configured positions — this requires extending the timeline cue creation flow (spike needed to assess effort)
- Scheduling a group applies schedule to all member assets

**Acceptance criteria:**
- [ ] CRUD endpoints work correctly
- [ ] Adding a member with a `child_group_id` that would create a cycle returns 400
- [ ] Nesting depth limit (3) is enforced at the API level
- [ ] Scheduling a group broadcasts the schedule to all member assets

---

#### B3.4 — Asset analytics (AssetAnalyticsService + router)
**Size:** M | **Deps:** B3.2

Implement analytics logging and the analytics dashboard API.

**Display log integration:**
- The stream executor (in `stream-engine/`) should log to `asset_display_log` when:
  - An overlay asset becomes active (insert row with `started_at`, `asset_id`, `timeline_execution_id`)
  - An overlay asset deactivates (update row with `ended_at`, compute `duration_seconds`)
- This requires extending the stream executor to call an analytics service; assess whether this is direct DB write or an async queue (direct write via SQLAlchemy is acceptable for Phase 3)

**Service responsibilities:**
- `get_asset_analytics(db, asset_id, start_date, end_date)` — aggregates from `asset_display_log`; returns `total_display_seconds`, `impression_count`, `sessions` list
- `get_analytics_summary(db, start_date, end_date)` — per-asset summary table; returns top/least shown
- `export_analytics_csv(db, start_date, end_date)` — generates CSV bytes
- Background cleanup: delete `asset_display_log` rows older than 90 days (run daily via a `lifespan` background task)

**Router additions to `assets.py`:**
```
GET /api/assets/{id}/analytics        per-asset analytics
GET /api/assets/analytics/summary     all-assets summary (with date range)
GET /api/assets/analytics/export      CSV download
```

**Acceptance criteria:**
- [ ] Display events are logged when a stream overlay appears/disappears
- [ ] Per-asset analytics aggregate correctly over a date range
- [ ] Summary endpoint returns correct top/least shown assets
- [ ] CSV export includes all assets with correct totals
- [ ] 90-day cleanup runs without disrupting active stream sessions
- [ ] Analytics query performance is acceptable for 10,000 display events (add index on `asset_id`, `started_at`)

---

#### B3.5 — Role-based access control (RBAC)
**Size:** M | **Deps:** B3.2

Implement RBAC for the four roles defined in PRD Section 3.3.9: Admin, Designer, Operator, Viewer.

**Role enforcement at API level:**
- Create a `require_role(*roles)` FastAPI dependency that checks `current_user.role` against the allowed roles; raises 403 if not permitted
- Role permissions matrix:

| Endpoint Group | Admin | Designer | Operator | Viewer |
|---|---|---|---|---|
| Asset CRUD (create/edit/delete) | Y | Y | N | N |
| Canvas project CRUD | Y | Y | N | N |
| Template instance create/edit | Y | Y | N | N |
| Stream start/stop | Y | N | Y | N |
| Timeline CRUD | Y | N | Y | N |
| Asset read (list, detail) | Y | Y | Y | Y |
| Analytics read | Y | Y | Y | Y |
| User management (role assignment) | Y | N | N | N |

- Existing endpoints default to Admin-only behavior (effectively unchanged since all current users are Admin)
- Add `role` to the `UserRead` schema response
- Add user management endpoints (or extend existing settings): `PUT /api/users/{id}/role` — Admin only

**Acceptance criteria:**
- [ ] Designer cannot call `POST /api/streams/start`
- [ ] Operator cannot call `POST /api/assets` (upload/create)
- [ ] Viewer gets 403 on any write endpoint
- [ ] Admin can update any user's role via the API
- [ ] All existing users default to `admin` role (backward compatible)
- [ ] Role enforcement is at the API level, not just UI

---

#### B3.6 — Import/export (templates and asset library)
**Size:** L | **Deps:** B3.3

Implement `backend/services/import_export_service.py` and the import/export endpoints.

**Template export/import (`/api/templates/export/{id}` and `/api/templates/import`):**
- Export: ZIP file containing `manifest.json`, `definition.json`, `assets/` (bundled image files), `preview.png`
- Import: unzip, validate HMAC signature (sign with app secret key from env), check schema version, resolve file conflicts (rename on collision), create template records
- File format documented in PRD Section 3.1.4

**Asset library export/import (`/api/assets/export` and `/api/assets/import`):**
- Export: ZIP file with `manifest.json` (asset metadata array + schema version), asset files, canvas JSON for canvas_composite assets
- Import: parse manifest, validate, create asset records, save files, handle conflicts (skip/overwrite/rename based on query param)
- Large export (>500MB): use streaming response rather than buffering entire ZIP in memory

**HMAC integrity:**
- Sign the `manifest.json` content with `HMAC-SHA256` using a configurable app secret
- Verify signature on import before processing
- Reject packages where signature does not match

**Acceptance criteria:**
- [ ] Template export creates a valid ZIP with all required files
- [ ] Template import creates a new `OverlayTemplate` record (or `TemplateInstance` for a configured instance)
- [ ] Import validates HMAC signature and rejects tampered packages
- [ ] Import resolves file name conflicts by appending `_1`, `_2`, etc.
- [ ] Asset library export includes all selected assets' files and metadata
- [ ] Asset library import handles a 100-asset package without memory issues
- [ ] Both import endpoints return structured error messages for corrupt/incompatible packages

---

#### B3.7 — Backend tests (Phase 3)
**Size:** M | **Deps:** B3.3, B3.4, B3.5, B3.6

Test coverage for all Phase 3 backend work. Emphasis on:
- RBAC: each role attempting each forbidden operation
- Analytics: aggregation correctness with known fixture data
- Import/export: round-trip test (export then import, verify all records match)
- Asset groups: nesting depth enforcement, cycle detection

---

### Phase 3 — Frontend Track

#### F3.1 — Asset groups UI
**Size:** M | **Deps:** F1.2, B3.3

Add asset group management to the My Assets tab.

**UI additions:**
- "Groups" sub-filter chip in the asset library shows groups as cards (with member count badge)
- "New Group" button in toolbar when "Groups" filter is active
- Group creation dialog: name, description, member asset picker (multi-select searchable list)
- Group card: shows member asset thumbnails (stacked), name, member count
- Group detail slide-over (or expand inline): member list with remove buttons, "Add Assets" button, group name/description edit
- Asset cards that belong to a group show a "Group" badge

**Acceptance criteria:**
- [ ] Creating a group and adding assets works end-to-end
- [ ] Group cards display correctly in the asset grid
- [ ] Removing a member asset from a group updates the group card
- [ ] Scheduling a group applies the schedule to all member assets (shows confirmation: "This will schedule N assets")

---

#### F3.2 — Analytics dashboard
**Size:** M | **Deps:** F1.1, B3.4

Implement the Analytics tab (`/assets/analytics`) as described in UX spec Section 5.5.

**Components:**
- Date range selector (preset dropdown + custom date picker)
- Summary cards (4): Total Display Time, Total Impressions, Most Shown Asset, Least Shown Asset
- Per-asset table: sortable columns (Name, Type, Display Time, Impressions, Last On)
- "Export CSV" button (downloads `GET /api/assets/analytics/export` response)

**Acceptance criteria:**
- [ ] Analytics tab loads summary and per-asset data from API
- [ ] Date range selector presets (Today, Last 7 days, Last 30 days) update the data
- [ ] Columns are sortable client-side
- [ ] "Export CSV" triggers file download
- [ ] Each asset row in the table opens the asset detail slide-over on click
- [ ] Empty state when no analytics data exists shows appropriate message

---

#### F3.3 — Import/export UI
**Size:** S | **Deps:** F1.2, F1.5, B3.6

Add import and export buttons to the My Assets and Template Catalog toolbars.

**My Assets toolbar:**
- "Export" button: opens a dialog to select assets (multi-select checkboxes on cards, or "Export All") then triggers download
- "Import" button: file picker accepting `.vst-assets` files; shows progress and success/error result

**Template Catalog toolbar:**
- "Import" button: file picker accepting `.vst-template` files; imports template
- Export is per-template via the "..." overflow menu on each template card

**Acceptance criteria:**
- [ ] Asset library export downloads a valid `.vst-assets` file
- [ ] Asset library import shows success count and error count
- [ ] Template import creates the template and shows it in the catalog
- [ ] Template export from card overflow menu downloads `.vst-template`
- [ ] Large export shows progress indicator (upload/download progress bar)

---

#### F3.4 — Role-based UI adjustments
**Size:** S | **Deps:** B3.5

Add frontend RBAC: hide or disable action buttons based on `current_user.role`.

**Approach:**
- Add `role` to the auth context (`AuthContext` in `contexts/`)
- Create a `usePermission(action)` hook that checks role
- Hide write actions (Create, Edit, Delete asset/template/canvas) for Operator and Viewer roles
- Show read-only UI for Viewer
- Operator sees streams/timelines management but not asset creation

**Acceptance criteria:**
- [ ] Designer user cannot see "Start Stream" button
- [ ] Operator user cannot see "New Asset", "New Canvas Project", "Use Template" buttons
- [ ] Viewer user sees only read-only dashboards and analytics
- [ ] API still enforces roles independently (frontend RBAC is UX, not security)
- [ ] Role is fetched as part of the auth/me endpoint and stored in auth context

---

### Phase 3 — Dependency Map

```
B2.6 (Phase 2 complete)
  └── B3.1 (migrations)
        └── B3.2 (models)
              ├── B3.3 (asset groups)
              ├── B3.4 (analytics)
              ├── B3.5 (RBAC)
              └── B3.6 (import/export)

B3.3, B3.4, B3.5, B3.6 -> B3.7 (tests)

F3.1 (groups UI) [needs B3.3]
F3.2 (analytics) [needs B3.4]
F3.3 (import/export UI) [needs B3.6]
F3.4 (RBAC UI) [needs B3.5]
```

---

## Phase 4: Polish and Advanced Templates (Weeks 10–12)

**Goal:** Additional templates, canvas editor enhancements, performance optimization, and production hardening.

**Exit criteria:**
- Template catalog has at least 8 templates across all categories
- Canvas editor handles 50+ objects at 60fps
- All `alert()` calls replaced with toast notifications
- Full test suite passes; no P0 bugs

---

### Phase 4 — Backend Track

#### B4.1 — NOAA Tides API integration
**Size:** M | **Deps:** B1.4 (template seeder)

Add Tide Chart and Marine Weather templates backed by the NOAA Tides and Currents API.

**NOAA API details:**
- Endpoint: `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
- No API key required for public data
- Required params: `begin_date`, `end_date`, `station`, `product` (water_level, predictions, wind, air_temperature), `datum`, `time_zone`, `units`, `application`, `format=json`

**New template definitions to add:**
```
backend/templates/catalog/
  tide_chart/
    definition.json    (station name or lat/lng, date range, theme)
    preview.png
  marine_weather/
    definition.json    (location, wind/wave display options, theme)
    preview.png
```

**TempestWeather approach for Phase 2 (simplest):** The backend periodically fetches tide data from NOAA and pre-renders a PNG overlay using Pillow. Tile data is cached for 1 hour (tide predictions don't change minute-to-minute). For Marine Weather, either use Tempest wind data or NOAA marine API.

**New endpoints (or template service extension):**
- `GET /api/templates/test-noaa?station={station}&product={product}` — test NOAA connectivity and return sample data for wizard preview

**Acceptance criteria:**
- [ ] Tide Chart template definition is seeded and appears in catalog under "Marine" category
- [ ] Marine Weather template appears in catalog
- [ ] Configuring a Tide Chart template with a valid NOAA station ID creates a working asset
- [ ] NOAA fetch respects rate limits (cache results, do not poll more than once per hour)
- [ ] "Test Connection" in wizard correctly tests NOAA station reachability

---

#### B4.2 — Sponsor/Ad Rotation template
**Size:** S | **Deps:** B1.4, B2.4 (scheduling)

Add the Sponsor/Ad Slot template backed by local file upload and the scheduling system.

**Template definition:**
- Required: business name, logo image (file upload during wizard)
- Optional: rotation interval (default 30s), position, schedule (time window)
- Creates a `static_image` asset with an `asset_schedule` record for rotation

This template differs from others: the wizard includes a file upload step (upload the logo, then configure schedule). The created asset is linked to any other sponsor assets in a rotation group via the scheduling system.

**Acceptance criteria:**
- [ ] Wizard allows uploading a logo image as step 1
- [ ] Wizard allows configuring rotation settings as step 2
- [ ] Created asset has an `always_on` or `time_window` schedule automatically applied
- [ ] Multiple sponsor assets can be grouped for rotation via the existing scheduling UI

---

#### B4.3 — Schedule conflict detection
**Size:** M | **Deps:** B2.4

Implement schedule conflict detection as described in PRD Section 3.3.4.

**Conflict definition:** Two assets with the same `position_x`/`position_y` (within 0.05 tolerance) that have overlapping schedule time windows.

**Implementation:**
- On `POST /api/assets/{id}/schedule`, after saving, query for other assets at a similar position with overlapping schedules
- Return a warnings array in the response: `{"saved": true, "warnings": ["Asset 'Bay View Marina' at the same position is scheduled during these same hours"]}`
- This is advisory (does not block the save)

**Acceptance criteria:**
- [ ] Overlapping schedules at the same position produce a warning in the API response
- [ ] Warning is displayed to the user in the schedule UI (non-blocking, dismissible)
- [ ] Non-overlapping schedules at the same position produce no warning
- [ ] Assets at different positions do not trigger warnings regardless of schedule overlap

---

#### B4.4 — End-to-end tests (Phase 4)
**Size:** M | **Deps:** all prior phases

Write end-to-end test scenarios as described in architecture doc Section 12.3:
1. Browse catalog -> configure weather template -> asset created -> add to timeline
2. Open canvas editor -> add text + image + shape -> export PNG -> asset in library
3. Edit asset -> version created -> view history -> revert to previous version
4. Upload custom font -> use in canvas editor -> export PNG renders correctly
5. Import `.vst-template` -> template instance created -> assets functional

Additionally: schedule conflict detection test, RBAC end-to-end (designer cannot start stream).

---

### Phase 4 — Frontend Track

#### F4.1 — Toast notification system (replace alert() calls)
**Size:** M | **Deps:** F1.7 (partial implementation in Phase 1)

Replace all `window.alert()` and `window.confirm()` calls across the entire codebase with a toast notification system.

**Implementation:**
- Create `ToastContext` and `useToast()` hook in `contexts/`
- Toast component: fixed bottom-right stack, auto-dismiss after 4 seconds, manual dismiss X button
- Toast types: success (green), error (red), warning (yellow), info (blue)
- Confirmation dialogs (replacing `confirm()`): use a modal with confirm/cancel buttons (`ConfirmModal.tsx`)
- Audit all existing components for `alert()` and `confirm()` calls and replace

**Files likely to need changes (based on codebase patterns):**
- `AssetManagement.tsx` (existing) — upload success/error alerts
- `StreamManagement.tsx` — stream start/stop alerts
- `CameraManagement.tsx` — camera test alerts
- Any component using `window.alert()` or `window.confirm()`

**Acceptance criteria:**
- [ ] Zero `window.alert()` calls remain in the codebase
- [ ] Zero `window.confirm()` calls remain (replaced with ConfirmModal)
- [ ] Toast notifications appear for all success/error states across the app
- [ ] Toasts auto-dismiss after 4 seconds; can be manually dismissed
- [ ] Multiple toasts stack correctly (not overlapping)
- [ ] Error toasts remain until dismissed (longer than success toasts)

---

#### F4.2 — Canvas editor enhancements
**Size:** L | **Deps:** F1.6

Extend the Phase 1 canvas editor with the advanced features deferred from Phase 1.

**Enhancements to implement:**
- Text effects: shadow (enable/disable toggle, offset X/Y, blur radius, color), stroke/outline (enable/disable, width, color), text background (enable/disable, color, opacity)
- Advanced shapes: gradient fills (linear and radial) via `Fill` type selector in ShapeProperties panel
- Alignment and distribution panel: align left/center/right/top/middle/bottom; distribute horizontally/vertically (activate when 2+ objects selected)
- Rulers along top and left edges with pixel coordinates
- Safe zone overlay toggle (show title-safe 90% and action-safe 80% boundary lines)
- Snap-to-grid (toggleable, default grid: 10px; configurable) with visual grid overlay
- Smart guides (snap to edges and centers of other objects during drag) — Fabric.js has built-in snapping but may need custom guide rendering
- Image import from existing asset library (not just file system) — opens an asset picker modal showing existing `static_image` assets
- Image cropping (Fabric.js ClipPath on the selected image object)

**Acceptance criteria:**
- [ ] Text shadow renders correctly on export (PNG shows shadow)
- [ ] Gradient fills render correctly on export
- [ ] Alignment buttons align objects relative to each other and the canvas
- [ ] Rulers show correct pixel coordinates at any zoom level
- [ ] Safe zone overlay toggles on/off and shows correct percentages
- [ ] Snap-to-grid snaps objects to the configured grid interval
- [ ] Smart guides appear during drag and indicate edge/center alignment
- [ ] Image picker shows existing assets for import into canvas
- [ ] Image cropping can be applied and is preserved in the canvas JSON

---

#### F4.3 — Schedule visual calendar view
**Size:** M | **Deps:** F2.1 (asset detail slide-over)

Enhance the schedule panel's weekly calendar preview into a full visual calendar for all scheduled assets.

**Calendar view additions:**
- Expand the schedule tab's weekly calendar preview into a more detailed visualization
- Add a new "Schedule Overview" panel or page (possibly within the My Assets tab or the Analytics tab) showing a 7-day calendar grid with all scheduled assets' active time blocks color-coded

**Acceptance criteria:**
- [ ] Each asset's schedule is shown as colored blocks on the 7-day grid
- [ ] Hovering a block shows the asset name and schedule details
- [ ] Blocks that overlap (potential conflicts) are highlighted in yellow/orange
- [ ] The calendar respects the configured timezone from Settings

---

#### F4.4 — Performance optimization and testing
**Size:** M | **Deps:** all prior phases

Performance auditing and optimization pass.

**Areas to optimize:**
- Canvas editor: profile Fabric.js rendering with 50+ objects; ensure 60fps during drag/resize on target hardware; Fabric.js render batching (`canvas.renderAll()` throttling)
- Asset library: virtual scrolling for 200+ asset grids (if needed; assess at this stage)
- Template catalog: ensure templates load under 500ms (verify thumbnail loading with lazy loading via `loading="lazy"` on img tags)
- API response times: add indexes to the most-queried asset columns (`type`, `is_active`, `created_at`)

**Testing:**
- Run existing test suite and fix any failures introduced during phases
- Manual testing of all UX spec user flows with the full feature set
- Browser compatibility check: Chrome, Firefox, Safari, Edge (Canvas Editor specifically)

**Acceptance criteria:**
- [ ] Canvas editor with 50 objects maintains 60fps during drag (measured via browser DevTools Performance panel)
- [ ] Asset library loads under 1 second for 200 assets
- [ ] Template catalog loads under 500ms
- [ ] All existing tests pass
- [ ] No P0 bugs in any user flow from the UX spec

---

#### F4.5 — Documentation and user guide
**Size:** S | **Deps:** all Phase 4

Write user-facing documentation for the new features.

**Deliverables:**
- Update `README.md` with Asset Management Studio overview
- Create `docs/USER-GUIDE-Asset-Management-Studio.md` covering:
  - Template catalog walkthrough (adding a weather overlay)
  - Canvas editor walkthrough (creating a lower third)
  - Scheduling overview
  - Version history and revert
  - Import/export

**Acceptance criteria:**
- [ ] Documentation covers all three product pillars
- [ ] Canvas editor keyboard shortcuts table is included
- [ ] Screenshots or diagrams illustrate key flows

---

### Phase 4 — Dependency Map

```
Phase 3 complete
  ├── B4.1 (NOAA templates) [can start at Phase 3 end]
  ├── B4.2 (sponsor template)
  ├── B4.3 (conflict detection)
  └── B4.4 (e2e tests) [needs all prior]

F4.1 (toast system) [can start anytime in Phase 4]
F4.2 (canvas enhancements) [needs F1.6]
F4.3 (schedule calendar) [needs F2.1]
F4.4 (performance + testing) [needs all prior]
F4.5 (docs) [needs all prior]
```

---

## Full Task Summary

### Phase 1 (Foundation — Weeks 1–3)

| ID | Task | Track | Size | Deps |
|----|------|-------|------|------|
| B1.1 | Database migrations (Phase 1) | BE | M | — |
| B1.2 | SQLAlchemy models (Phase 1) | BE | M | B1.1 |
| B1.3 | Template catalog seeder | BE | M | B1.2 |
| B1.4 | Template router + TemplateService | BE | L | B1.2, B1.3 |
| B1.5 | Canvas project router + CanvasProjectService | BE | L | B1.2 |
| B1.6 | Font router + FontService | BE | M | B1.2 |
| B1.7 | Asset router extensions + wiring | BE | S | B1.4, B1.5 |
| B1.8 | Backend tests (Phase 1) | BE | M | B1.4–B1.7 |
| F1.1 | Navigation update + Asset Studio shell | FE | M | — |
| F1.2 | Asset Library enhancements | FE | M | F1.1 |
| F1.3 | Shared SlideOver component | FE | S | F1.1 |
| F1.4 | Shared PositionPicker component | FE | S | — |
| F1.5 | Template Catalog tab | FE | L | F1.1, F1.3, B1.4 |
| F1.6 | Canvas Editor page (Phase 1 MVP) | FE | XL | F1.1, F1.3, B1.5 |
| F1.7 | Frontend integration + polish | FE | S | F1.2, F1.5, F1.6 |

### Phase 2 (Lifecycle — Weeks 4–6)

| ID | Task | Track | Size | Deps |
|----|------|-------|------|------|
| B2.1 | Database migrations (Phase 2) | BE | S | B1.8 |
| B2.2 | SQLAlchemy models (Phase 2) | BE | S | B2.1 |
| B2.3 | Asset versioning | BE | M | B2.2 |
| B2.4 | Asset scheduling | BE | M | B2.2 |
| B2.5 | Live data bindings (data_bound) | BE | L | B2.2 |
| B2.6 | Backend tests (Phase 2) | BE | M | B2.3–B2.5 |
| F2.1 | Asset detail slide-over (3 tabs) | FE | L | F1.3, B2.3, B2.4 |
| F2.2 | Data binding wizard | FE | M | F1.3, B2.5 |
| F2.3 | Frontend tests (Phase 2) | FE | S | F2.1, F2.2 |

### Phase 3 (Intelligence — Weeks 7–9)

| ID | Task | Track | Size | Deps |
|----|------|-------|------|------|
| B3.1 | Database migrations (Phase 3) | BE | S | B2.6 |
| B3.2 | SQLAlchemy models (Phase 3) | BE | S | B3.1 |
| B3.3 | Asset groups router + service | BE | M | B3.2 |
| B3.4 | Asset analytics router + service | BE | M | B3.2 |
| B3.5 | Role-based access control | BE | M | B3.2 |
| B3.6 | Import/export service + endpoints | BE | L | B3.3 |
| B3.7 | Backend tests (Phase 3) | BE | M | B3.3–B3.6 |
| F3.1 | Asset groups UI | FE | M | F1.2, B3.3 |
| F3.2 | Analytics dashboard | FE | M | F1.1, B3.4 |
| F3.3 | Import/export UI | FE | S | F1.2, F1.5, B3.6 |
| F3.4 | Role-based UI adjustments | FE | S | B3.5 |

### Phase 4 (Polish — Weeks 10–12)

| ID | Task | Track | Size | Deps |
|----|------|-------|------|------|
| B4.1 | NOAA Tides API integration | BE | M | B1.4 |
| B4.2 | Sponsor/Ad Rotation template | BE | S | B1.4, B2.4 |
| B4.3 | Schedule conflict detection | BE | M | B2.4 |
| B4.4 | End-to-end tests | BE | M | all phases |
| F4.1 | Toast notification system | FE | M | F1.7 |
| F4.2 | Canvas editor enhancements | FE | L | F1.6 |
| F4.3 | Schedule visual calendar | FE | M | F2.1 |
| F4.4 | Performance optimization + testing | FE | M | all phases |
| F4.5 | Documentation | FE | S | all phases |

---

## Task Count and Size Totals

| Phase | BE Tasks | FE Tasks | S Count | M Count | L Count | XL Count |
|-------|----------|----------|---------|---------|---------|----------|
| Phase 1 | 8 | 7 | 3 | 7 | 4 | 1 |
| Phase 2 | 6 | 3 | 3 | 5 | 1 | 0 |
| Phase 3 | 7 | 4 | 3 | 7 | 1 | 0 |
| Phase 4 | 4 | 5 | 1 | 6 | 2 | 0 |
| **Total** | **25** | **19** | **10** | **25** | **8** | **1** |

**44 tasks total.** Rough person-week estimate (S=0.5, M=1.5, L=3.5, XL=6):
- 10 × S = 5 person-weeks
- 25 × M = 37.5 person-weeks
- 8 × L = 28 person-weeks
- 1 × XL = 6 person-weeks
- **Total: ~76 person-weeks** across BE+FE parallel tracks over 12 calendar weeks

---

## Key Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fabric.js v6 React integration complexity (imperative vs. declarative) | Medium | High (F1.6 is already XL) | Allocate the first 2-3 days of F1.6 as a Fabric.js spike; build a minimal working prototype before committing to the full architecture |
| Canvas editor 60fps performance with 50+ objects | Medium | Medium | Benchmark early in Phase 1; if needed, throttle `renderAll()` and batch state updates; Fabric.js `renderOnAddRemove: false` helps |
| Template seeder idempotency and JSON schema design | Low | Medium | Seed is tested with an integration test; JSON schema is simple (not standard JSON Schema spec) |
| NOAA API rate limits or endpoint changes | Low | Low | Cache NOAA responses for 1 hour; add a test for the tide chart template using a mocked NOAA response |
| Asset versioning file storage growth | Low | Medium | 50-version cap per asset + soft deletes; add a storage usage warning in Settings when `/data` exceeds a configurable threshold |
| SQLite WAL mode contention with analytics logging | Low | Low | Analytics writes are append-only and infrequent; WAL mode handles this well for 2-5 concurrent users |
| Stream executor modification (B2.4 scheduling hook) | Medium | Medium | The stream engine may need careful modification to avoid disrupting active streams; test scheduling hook changes with a stream running |

---

## Spikes Recommended Before Committing

### Spike 1: Fabric.js v6 + React Integration (1-2 days)
**Before F1.6 begins.** Goal: prove out the `useRef` + `useEffect` initialization pattern, Fabric.js event -> React state sync, and undo/redo using the `CanvasHistoryManager`. Output: a working prototype with Text tool, Rectangle tool, layer list, and undo/redo. This validates F1.6's complexity estimate.

### Spike 2: Asset Groups + Timeline Integration (1 day)
**Before B3.3.** Goal: assess the effort of making the existing Timeline editor understand asset groups (adding a group to a timeline adds all member assets). This is described in PRD Section 3.3.6 but the existing Timeline system may need non-trivial changes. Output: a recommendation for either Phase 3 or defer to Phase 4+.

### Spike 3: Data-bound Asset Rendering via Pillow (0.5 days)
**Before B2.5.** Goal: validate that Pillow can render a multi-line text overlay with transparency and an installed font, producing a PNG that FFmpeg can composite. Test with the Liberation Sans system font (available in the Docker container). Output: a working `render_data_binding()` function prototype.

---

## Open Items Before Development Starts

1. **Google Fonts API key:** The `GET /api/fonts/google` search endpoint may require a Google Fonts API key (`AIza...`). Determine if the `webfonts/v1` endpoint will be used (requires key) or if only the CSS2 endpoint is used (keyless). If a key is needed, add it to the `env.sample` file.

2. **TempestWeather "Test Connection" proxy:** The template wizard "Test Connection" for Tempest stations calls the TempestWeather service at `host.docker.internal:8036`. The browser cannot reach `host.docker.internal` directly; the backend must proxy this test. Confirm that `POST /api/templates/instances` (or a `/test` endpoint) correctly proxies the connectivity check, since `host.docker.internal` is currently in the blocked hostname list in `_validate_url()` — this will need a carve-out for Tempest-specific URLs.

3. **Font rendering in Pillow for data_bound assets:** Confirm that the Liberation fonts installed in the Docker container are compatible with Pillow's `ImageFont.truetype()` and FFmpeg's `drawtext` filter. A quick test in the existing environment before Phase 2 begins will avoid surprises.

4. **Stream executor access pattern for scheduling (B2.4):** The scheduling enforcement hook in the FFmpeg pipeline needs to be placed in the stream executor. Identify the exact file and function in `stream-engine/` where overlay assets are added to the filter graph, to scope B2.4 accurately.
