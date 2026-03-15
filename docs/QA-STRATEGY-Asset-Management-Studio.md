# QA Strategy: VistterStream Asset Management Studio

**Version:** 1.0
**Last Updated:** 2026-03-15
**Author:** Nick DeMarco with AI Assistance
**Status:** Draft
**PRD Reference:** [PRD-Asset-Management-Studio.md](./PRD-Asset-Management-Studio.md)
**Architecture Reference:** [ARCH-Asset-Management-Studio.md](./ARCH-Asset-Management-Studio.md)
**UX Reference:** [UX-Asset-Management-Studio.md](./UX-Asset-Management-Studio.md)

---

## 1. Executive Summary

### 1.1 Test Objectives

The Asset Management Studio adds three interconnected pillars to VistterStream: a Template Catalog with configuration wizards, an in-browser Canvas Editor (Fabric.js), and Asset Lifecycle features (versioning, scheduling, groups, analytics). Each pillar introduces distinct testing challenges.

The primary objectives of this QA strategy are:

- Protect the existing streaming pipeline -- no regression to timeline, overlay compositing, or FFmpeg behavior
- Validate the Canvas Editor's correctness and performance without GPU-assisted tooling
- Confirm the template-to-stream pipeline: wizard config produces an Asset that FFmpeg can composite correctly
- Verify all security controls on file upload, SSRF, and template import
- Ensure database migrations are safe, reversible, and backward-compatible with existing data

### 1.2 Quality Goals

| Metric | Target |
|--------|--------|
| Backend API test coverage | >= 80% line coverage on new routers and services |
| Frontend component coverage | >= 70% on new components (excluding Fabric.js internals) |
| P0 defects at release | 0 |
| P1 defects at release | <= 2 (with documented workarounds) |
| Canvas editor responsiveness | 60fps during drag/resize with 50 objects (measured via browser DevTools) |
| PNG export correctness | Exported PNG composites correctly in FFmpeg filter graph |
| Regression: existing asset API | 100% of existing tests continue to pass |
| Migration safety | Zero data-loss on forward and rollback migration |

### 1.3 Phased Scope

The PRD defines three delivery phases. QA gates are defined per-phase. Phase 1 is the primary focus of this document.

| Phase | Key Features | QA Priority |
|-------|-------------|-------------|
| Phase 1 | Template Catalog, Configuration Wizards, Canvas Editor (core), Canvas Export, Font Management, Backward-Compat Migration | Primary focus |
| Phase 2 | Asset Versioning, Asset Scheduling, Data Bindings (data_bound type) | Secondary focus |
| Phase 3 | Asset Groups, Analytics, RBAC, Import/Export | Deferred |

---

## 2. Current Test Infrastructure Baseline

### 2.1 What Already Exists

The existing test suite establishes patterns that new tests must follow:

**Backend (pytest + FastAPI TestClient)**
- Framework: `pytest` with `asyncio_mode = "auto"` (pyproject.toml)
- Test root: `backend/tests/` (per-router test files)
- Secondary test root: `tests/` (top-level, for service-level tests like `test_ffmpeg_manager.py`)
- Fixture pattern: `conftest.py` provides `db_session` (in-memory SQLite, per-test clean) and `client` (FastAPI TestClient with DB override)
- Auth helper: `_get_auth_header(client, db_session)` pattern used consistently across test files
- Rate limiting: disabled in tests via `_auth_module.limiter.enabled = False`
- Coverage areas: auth (login, registration, password validation), assets (CRUD, type validation), timelines (tracks, cues, copy, broadcast metadata), SSRF validation, audit logging, destinations, streams, cameras

**Frontend (React Testing Library + Jest)**
- Framework: Create React App default (Jest + `@testing-library/react`)
- Only existing test: `App.test.tsx` (renders app without crashing)
- No component-level tests exist yet -- this strategy establishes the pattern

**Integration / Service**
- `tests/test_ffmpeg_manager.py`: async tests for FFmpeg process manager using `unittest.mock`
- `docker/docker-compose.test.yml`: defines test environment stack but no automated E2E runner is currently configured

### 2.2 Gaps to Fill

| Gap | Action |
|-----|--------|
| No frontend component tests | Add Vitest + React Testing Library tests per section 5 |
| No E2E test runner | Add Playwright as the E2E framework (section 6) |
| No migration tests | Add dedicated Alembic migration test suite (section 4.3) |
| No performance benchmarks | Add canvas performance test script (section 7) |
| No canvas-specific test tooling | Use jsdom-based unit tests for canvas logic; manual protocol for visual correctness |

---

## 3. Testing Pyramid and Proportions

```
                    ┌──────────────────┐
                    │   E2E / Manual   │  ~5% -- critical user journeys only
                    │   (Playwright)   │  kept small due to canvas complexity
                    ├──────────────────┤
                    │   Integration    │  ~25% -- API flows, pipeline tests
                    │   (pytest)       │  asset->timeline->FFmpeg chain
                    ├──────────────────┤
                    │   Component      │  ~30% -- React component tests
                    │   (Vitest+RTL)   │  forms, panels, state transitions
                    ├──────────────────┤
                    │   Unit           │  ~40% -- services, validators, utils
                    │   (pytest/Jest)  │  the fastest, most stable layer
                    └──────────────────┘
```

**Rationale for this shape:**
- The Canvas Editor (Fabric.js) is inherently difficult to test in a headless environment. The pyramid is flatter at the top than usual -- visual correctness is verified through a manual checklist (section 9) rather than automated pixel diffing, which would be fragile.
- The FFmpeg pipeline is tested at the integration level with mocked subprocesses, not at full E2E, because spinning up real FFmpeg in CI is expensive and flaky.
- The existing backend already has strong unit and integration tests; new additions follow the same pattern.

---

## 4. Backend Test Strategy

### 4.1 Unit Tests -- Services

Each new service gets a corresponding test file in `backend/tests/`. Services are tested in isolation using in-memory SQLite and mocked external dependencies.

#### 4.1.1 TemplateService Tests

File: `backend/tests/test_template_service.py`

| Test ID | Description | Priority |
|---------|-------------|----------|
| TS-001 | `instantiate_weather_template` -- valid station ID produces correct `api_url` | P0 |
| TS-002 | `instantiate_weather_template` -- missing required field raises `ValueError` | P0 |
| TS-003 | `instantiate_weather_template` -- merges user config with defaults correctly | P0 |
| TS-004 | `instantiate_lower_third_template` -- static text template produces `canvas_composite` asset type | P1 |
| TS-005 | `instantiate_time_date_template` -- produces `data_bound` asset with correct timezone field | P1 |
| TS-006 | `validate_config_against_schema` -- extra fields are stripped (not rejected) | P2 |
| TS-007 | `validate_config_against_schema` -- invalid field type (string where int expected) raises error | P1 |
| TS-008 | `get_template_catalog` -- returns only `is_active=True` templates | P1 |
| TS-009 | `get_template_catalog` -- category filter returns correct subset | P1 |
| TS-010 | Template instantiation creates both `TemplateInstance` and `Asset` records atomically | P0 |

#### 4.1.2 CanvasProjectService Tests

File: `backend/tests/test_canvas_project_service.py`

| Test ID | Description | Priority |
|---------|-------------|----------|
| CP-001 | `create_project` -- stores Fabric.js JSON correctly | P0 |
| CP-002 | `save_project` -- updates `canvas_json` and `updated_at` | P0 |
| CP-003 | `save_project` -- thumbnail base64 PNG is decoded and written to filesystem | P0 |
| CP-004 | `export_project` -- creates `canvas_composite` Asset with correct `file_path` | P0 |
| CP-005 | `export_project` -- exported PNG file exists on filesystem | P0 |
| CP-006 | `duplicate_project` -- new project has different `id` and `created_at` | P1 |
| CP-007 | `delete_project` -- sets `is_active=False` (soft delete) | P1 |
| CP-008 | `list_projects` -- soft-deleted projects are excluded | P1 |
| CP-009 | `save_project` -- concurrent autosave (second save after first pending) does not corrupt data | P1 |
| CP-010 | `export_project` -- oversized canvas_json (> 5MB) is rejected with 400 | P2 |

#### 4.1.3 FontService Tests

File: `backend/tests/test_font_service.py`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FS-001 | Upload `.ttf` file -- font record created, file saved to `/data/fonts/` | P0 |
| FS-002 | Upload `.otf` file -- accepted | P1 |
| FS-003 | Upload `.woff2` file -- accepted | P1 |
| FS-004 | Upload `.exe` file -- rejected with 400 | P0 |
| FS-005 | Upload file with forged MIME type (text/plain renamed to font.ttf) -- rejected | P0 |
| FS-006 | `install_google_font` -- font is downloaded and cached to `/data/fonts/` | P1 |
| FS-007 | `install_google_font` -- font already cached; does not re-download | P2 |
| FS-008 | `delete_font` -- soft delete; font file remains on disk (not immediately purged) | P2 |
| FS-009 | `list_fonts` -- returns system fonts, uploaded fonts, and cached Google fonts | P1 |

#### 4.1.4 AssetVersionService Tests

File: `backend/tests/test_asset_version_service.py`

| Test ID | Description | Priority |
|---------|-------------|----------|
| AV-001 | `create_version` -- snapshot contains all asset field values at time of save | P0 |
| AV-002 | `create_version` -- version numbers increment sequentially per asset | P0 |
| AV-003 | `create_version` -- file-based asset copies file to versioned directory | P0 |
| AV-004 | `revert_to_version` -- restores asset fields from snapshot | P0 |
| AV-005 | `revert_to_version` -- creates a new version record (revert is itself versioned) | P0 |
| AV-006 | `revert_to_version` -- non-existent version_number returns 404 | P1 |
| AV-007 | Version count > 50 -- oldest version is purged | P1 |
| AV-008 | Version purge -- purged version's file is deleted from filesystem | P2 |
| AV-009 | `get_versions` -- returns versions in descending order (newest first) | P1 |

#### 4.1.5 AssetScheduleService Tests

File: `backend/tests/test_asset_schedule_service.py`

| Test ID | Description | Priority |
|---------|-------------|----------|
| AS-001 | `is_asset_active_now` -- `always_on` type returns `True` | P0 |
| AS-002 | `is_asset_active_now` -- `time_window` within window returns `True` | P0 |
| AS-003 | `is_asset_active_now` -- `time_window` outside window returns `False` | P0 |
| AS-004 | `is_asset_active_now` -- `time_window` on excluded day-of-week returns `False` | P0 |
| AS-005 | `is_asset_active_now` -- timezone conversion is applied before window check | P0 |
| AS-006 | `is_asset_active_now` -- midnight boundary (window: 22:00-06:00) handled correctly | P1 |
| AS-007 | `detect_schedule_conflicts` -- two assets at same position during overlapping window returns warning | P1 |
| AS-008 | `update_schedule` -- invalid cron expression raises 400 | P2 |

### 4.2 Integration Tests -- API Endpoints

New API endpoint tests follow the exact same pattern as existing tests: `conftest.py` fixtures, `_get_auth_header` helper, in-memory SQLite, no external dependencies.

#### 4.2.1 Template Catalog Endpoints

File: `backend/tests/test_templates.py`

| Test ID | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| TC-API-001 | GET /api/templates | Unauthenticated request returns 401 | P0 |
| TC-API-002 | GET /api/templates | Returns list of active templates | P0 |
| TC-API-003 | GET /api/templates?category=weather | Returns only weather category templates | P1 |
| TC-API-004 | GET /api/templates/{id} | Returns template with config_schema | P0 |
| TC-API-005 | GET /api/templates/{id} | Non-existent ID returns 404 | P1 |
| TC-API-006 | POST /api/templates/instances | Valid weather config creates Asset + TemplateInstance | P0 |
| TC-API-007 | POST /api/templates/instances | Missing required station_id returns 400 | P0 |
| TC-API-008 | POST /api/templates/instances | Invalid template_id returns 404 | P1 |
| TC-API-009 | PUT /api/templates/instances/{id} | Updates config_values on existing instance | P1 |
| TC-API-010 | DELETE /api/templates/instances/{id} | Soft-deletes instance; associated Asset marked inactive | P1 |
| TC-API-011 | GET /api/templates/instances | Lists all instances for current user | P1 |

#### 4.2.2 Canvas Project Endpoints

File: `backend/tests/test_canvas_projects.py`

| Test ID | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| CP-API-001 | GET /api/canvas-projects | Unauthenticated returns 401 | P0 |
| CP-API-002 | POST /api/canvas-projects | Creates project with name + canvas_json | P0 |
| CP-API-003 | POST /api/canvas-projects | Missing `name` returns 422 | P1 |
| CP-API-004 | GET /api/canvas-projects | Lists only active projects | P0 |
| CP-API-005 | GET /api/canvas-projects/{id} | Returns full canvas_json | P0 |
| CP-API-006 | PUT /api/canvas-projects/{id} | Saves updated canvas_json | P0 |
| CP-API-007 | PUT /api/canvas-projects/{id} | Autosave with thumbnail_data updates thumbnail_path | P0 |
| CP-API-008 | DELETE /api/canvas-projects/{id} | Soft delete; GET returns 404 | P1 |
| CP-API-009 | POST /api/canvas-projects/{id}/export | Creates canvas_composite Asset | P0 |
| CP-API-010 | POST /api/canvas-projects/{id}/export | Exported asset has correct width/height from project | P0 |
| CP-API-011 | POST /api/canvas-projects/{id}/duplicate | Returns new project ID, same canvas_json | P1 |
| CP-API-012 | POST /api/canvas-projects/{id}/export | canvas_json containing SVG data is sanitized | P0 |

#### 4.2.3 Font Endpoints

File: `backend/tests/test_fonts.py`

| Test ID | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| FN-API-001 | GET /api/fonts | Returns system + uploaded + cached fonts | P1 |
| FN-API-002 | POST /api/fonts/upload | .ttf upload creates Font record | P0 |
| FN-API-003 | POST /api/fonts/upload | .exe upload returns 400 | P0 |
| FN-API-004 | POST /api/fonts/upload | File > 10MB returns 413 | P1 |
| FN-API-005 | GET /api/fonts/google | Returns font catalog from Google (mocked) | P2 |
| FN-API-006 | POST /api/fonts/google/install | Downloads and caches font (mocked HTTP) | P1 |
| FN-API-007 | DELETE /api/fonts/{id} | Removes font record; file remains | P2 |

#### 4.2.4 Extended Asset Endpoints

File: `backend/tests/test_assets_extended.py`

| Test ID | Endpoint | Description | Priority |
|---------|----------|-------------|----------|
| AE-API-001 | GET /api/assets?type=canvas_composite | Filters by new asset type | P1 |
| AE-API-002 | GET /api/assets?search=weather | Full-text search returns matching assets | P1 |
| AE-API-003 | GET /api/assets/{id}/versions | Returns version history list | P1 |
| AE-API-004 | POST /api/assets/{id}/revert/{version} | Reverts asset to previous version | P1 |
| AE-API-005 | POST /api/assets/{id}/schedule | Creates time_window schedule | P1 |
| AE-API-006 | GET /api/assets/{id}/schedule | Returns current schedule | P1 |
| AE-API-007 | DELETE /api/assets/{id}/schedule | Removes schedule | P2 |
| AE-API-008 | POST /api/assets (data_bound type) | Creates data_bound asset with binding_config | P1 |
| AE-API-009 | POST /api/assets (data_bound type) | SSRF validation applied to source_url | P0 |

### 4.3 Database Migration Tests

Migrations are the highest-risk backend change. The following tests validate migration safety separately from the application test suite.

**File:** `backend/tests/test_migrations.py`

**Strategy:** Tests run Alembic operations against a temporary SQLite database containing a snapshot of pre-migration production data (anonymized or synthetic).

| Test ID | Description | Priority |
|---------|-------------|----------|
| MIG-001 | Forward migration from baseline creates all 8 new tables | P0 |
| MIG-002 | Forward migration does not modify existing Asset records (zero rows affected in assets table) | P0 |
| MIG-003 | Forward migration adds nullable columns to `assets` with NULL values for existing rows | P0 |
| MIG-004 | Forward migration adds `role` column to `users` with default "admin" for all existing users | P0 |
| MIG-005 | Rollback (downgrade) removes all new tables without error | P0 |
| MIG-006 | Rollback does not remove any existing asset rows | P0 |
| MIG-007 | Migration on a database with 1,000 existing assets completes in under 5 seconds | P1 |
| MIG-008 | Migration on a WAL-mode database succeeds without lock conflicts | P1 |
| MIG-009 | Foreign key constraints are satisfied -- orphaned TemplateInstance rows are impossible | P1 |
| MIG-010 | Migration is idempotent -- running forward twice does not error | P2 |

**Pre-migration snapshot procedure:**
Before merging the migration branch, dump the production database:
```bash
sqlite3 /data/vistterstream.db .dump > backend/tests/fixtures/pre-migration-snapshot.sql
```
The `test_migrations.py` suite loads this snapshot into a temp database and runs `alembic upgrade head` against it.

### 4.4 SSRF and Security Tests (Extended)

Extend the existing `test_ssrf_validation.py` coverage for new surfaces.

File: `backend/tests/test_ssrf_extended.py`

| Test ID | Description | Priority |
|---------|-------------|----------|
| SEC-001 | Template wizard `test_connection` endpoint rejects `host.docker.internal` URL | P0 |
| SEC-002 | Template wizard `test_connection` endpoint rejects `169.254.169.254` (metadata) | P0 |
| SEC-003 | Data binding `source_url` rejects 10.x.x.x private range | P0 |
| SEC-004 | Data binding `source_url` rejects `file://` scheme | P0 |
| SEC-005 | Data binding `source_url` allows 192.168.x.x (TempestWeather) | P0 |
| SEC-006 | Canvas project JSON containing `<script>` tags is stripped on load | P0 |
| SEC-007 | Canvas project JSON containing SVG with `onload` attribute is stripped | P0 |
| SEC-008 | Template import `.vst-template` with path traversal in filenames is rejected | P0 |
| SEC-009 | Template import with HMAC verification failure is rejected | P0 |
| SEC-010 | Font upload with double extension (`malware.ttf.exe`) is rejected | P0 |
| SEC-011 | Asset upload rate limit (100/min) is enforced | P1 |
| SEC-012 | Canvas autosave rate limit (60/min) is enforced | P1 |
| SEC-013 | 172.16.0.0/12 private range -- document current behavior (allowed per existing test pattern) | P2 |

---

## 5. Frontend Test Strategy

### 5.1 Framework Setup

The existing Create React App setup provides Jest + `@testing-library/react`. The strategy recommends migrating to **Vitest** for faster execution and better ESM support, but this is not required for Phase 1. Either Jest or Vitest works; the test code is identical.

**New dev dependencies to add:**

```json
{
  "@testing-library/user-event": "^14.x",
  "vitest": "^2.x",
  "@vitest/ui": "^2.x",
  "msw": "^2.x",
  "happy-dom": "^14.x"
}
```

**MSW (Mock Service Worker)** is used to intercept API calls in component tests without needing a running backend.

### 5.2 Component Tests -- Template Catalog

File: `frontend/src/components/__tests__/TemplateCatalog.test.tsx`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FE-TC-001 | Renders template cards from API response | P0 |
| FE-TC-002 | Category filter chip click filters visible cards | P0 |
| FE-TC-003 | Search input filters cards by name in real-time | P1 |
| FE-TC-004 | "Coming Soon" template cards are visible but have disabled click target | P1 |
| FE-TC-005 | Clicking a template card opens the configuration slide-over | P0 |
| FE-TC-006 | Empty state renders "No templates found" when search has no results | P2 |
| FE-TC-007 | API error returns an error state with retry button | P1 |

File: `frontend/src/components/__tests__/TemplateWizard.test.tsx`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FE-TW-001 | Required fields are marked; "Create Asset" button is disabled until filled | P0 |
| FE-TW-002 | Filling required Station ID enables "Test Connection" button | P0 |
| FE-TW-003 | "Test Connection" success shows green checkmark + live preview update | P0 |
| FE-TW-004 | "Test Connection" failure shows inline error message | P0 |
| FE-TW-005 | Invalid Station ID format shows validation message below field | P0 |
| FE-TW-006 | Submitting wizard calls `POST /api/templates/instances` with correct payload | P0 |
| FE-TW-007 | Successful submission closes slide-over and shows success toast | P1 |
| FE-TW-008 | API error on submission shows error toast with message | P1 |
| FE-TW-009 | Position picker (9-grid) maps to correct `position_x`/`position_y` values | P1 |

### 5.3 Component Tests -- Canvas Editor

The Canvas Editor is tested at two levels: the React wrapper components (testable with jsdom) and the Fabric.js integration (tested via manual protocol in section 9). Do not attempt to test `FabricCanvas.tsx` internals with jsdom -- Fabric.js requires a real browser canvas.

File: `frontend/src/components/__tests__/CanvasEditorPage.test.tsx`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FE-CE-001 | Page renders EditorToolbar, ToolPanel, and PropertiesPanel | P0 |
| FE-CE-002 | Toolbar displays project name and Save button | P0 |
| FE-CE-003 | Ctrl+S triggers save API call | P0 |
| FE-CE-004 | Ctrl+Z dispatches undo action to history manager | P0 |
| FE-CE-005 | Ctrl+Shift+Z dispatches redo action to history manager | P0 |
| FE-CE-006 | Unsaved changes prompt shown when navigating away (dirty state) | P1 |
| FE-CE-007 | "Export as Asset" button triggers export flow | P0 |
| FE-CE-008 | Export dialog shows filename pre-filled from project name | P1 |

File: `frontend/src/components/__tests__/LayerPanel.test.tsx`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FE-LP-001 | Layers list renders one item per canvas object | P0 |
| FE-LP-002 | Clicking visibility toggle fires `object.set('visible', false)` | P1 |
| FE-LP-003 | Clicking lock toggle fires `object.set('selectable', false)` | P1 |
| FE-LP-004 | Double-clicking layer name enables inline rename | P1 |
| FE-LP-005 | Drag-to-reorder fires correct z-order change event | P1 |

File: `frontend/src/components/__tests__/PropertiesPanel.test.tsx`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FE-PP-001 | No selection shows empty/placeholder state | P1 |
| FE-PP-002 | Text object selected -- TextProperties panel is visible | P0 |
| FE-PP-003 | Shape object selected -- ShapeProperties panel is visible | P0 |
| FE-PP-004 | Font size input change fires correct Fabric.js property update | P1 |
| FE-PP-005 | Opacity slider change fires opacity update | P1 |
| FE-PP-006 | Color picker selection fires fill color update | P1 |

### 5.4 Component Tests -- CanvasHistoryManager

The `CanvasHistoryManager` class contains pure logic and is fully testable without a browser:

File: `frontend/src/utils/__tests__/CanvasHistoryManager.test.ts`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FE-HM-001 | `push` adds state to history | P0 |
| FE-HM-002 | `undo` decrements pointer and returns previous state | P0 |
| FE-HM-003 | `undo` at pointer 0 returns null | P0 |
| FE-HM-004 | `redo` increments pointer and returns next state | P0 |
| FE-HM-005 | `redo` at end of history returns null | P0 |
| FE-HM-006 | `push` after undo truncates forward history | P0 |
| FE-HM-007 | History exceeding 50 entries drops the oldest | P1 |
| FE-HM-008 | `push` 51 states: oldest is dropped, `undo` limit is correct | P1 |

### 5.5 Component Tests -- Asset Library (Enhanced)

File: `frontend/src/components/__tests__/AssetLibrary.test.tsx`

| Test ID | Description | Priority |
|---------|-------------|----------|
| FE-AL-001 | Renders asset grid from API response | P0 |
| FE-AL-002 | Filter by type "canvas_composite" shows only canvas assets | P1 |
| FE-AL-003 | Search field filters in real-time | P1 |
| FE-AL-004 | Version history panel opens on "History" button click | P1 |
| FE-AL-005 | Schedule panel opens on "Schedule" button click | P1 |
| FE-AL-006 | "Revert" button in version history calls `POST /api/assets/{id}/revert/{version}` | P1 |
| FE-AL-007 | Empty state shows "Browse Templates" CTA | P1 |

---

## 6. Integration Test Strategy -- End-to-End Pipeline

### 6.1 E2E Framework: Playwright

Add Playwright for the critical user journeys that require a real browser. These tests run against the `docker-compose.test.yml` stack.

**Installation:**
```bash
cd frontend && npm install -D @playwright/test && npx playwright install chromium
```

**Test location:** `frontend/e2e/`

### 6.2 Critical E2E Test Suite

These are the journeys that must pass before any release. They cover the full stack: browser -> API -> database -> filesystem.

| Test ID | Journey | Priority |
|---------|---------|----------|
| E2E-001 | Login -> Asset Studio (empty state) -> Template Catalog -> Configure Tempest Weather -> Create Asset -> Asset appears in library | P0 |
| E2E-002 | Login -> Asset Studio -> New Canvas Project -> Name project -> Canvas editor loads -> Export as Asset -> Asset in library | P0 |
| E2E-003 | Login -> Asset Library -> Select existing asset -> Open Version History -> Revert to previous version -> Confirm revert | P1 |
| E2E-004 | Login -> Asset -> Configure Schedule (time_window Mon-Fri 9am-5pm) -> Save -> Schedule appears in schedule panel | P1 |
| E2E-005 | Template import: upload a valid `.vst-template` file -> New asset and template instance appear | P1 |
| E2E-006 | Template import: upload a malformed `.vst-template` file -> Error displayed, no partial import | P0 |
| E2E-007 | Canvas editor: Create project -> Add text layer -> Add image -> Change z-order -> Export -> PNG is downloadable | P0 |

### 6.3 Asset-to-FFmpeg Pipeline Integration Test

This is the most critical end-to-end verification: does a canvas-exported PNG actually composite correctly in FFmpeg?

**Test location:** `tests/test_canvas_to_stream.py`

**Strategy:** Does not spin up a live stream. Instead, tests the FFmpeg command-line invocation with mocked inputs.

```python
# Pseudocode for the pipeline integration test

def test_canvas_export_composites_in_ffmpeg():
    # 1. Create a canvas project via API
    project = api_client.post("/api/canvas-projects", {...})

    # 2. Export as PNG asset
    export = api_client.post(f"/api/canvas-projects/{project.id}/export", {...})
    asset = export.json()

    # 3. Verify the asset file exists on disk
    assert Path(asset["file_path"]).exists()

    # 4. Verify FFmpeg can process the file (validate the filter graph)
    result = subprocess.run([
        "ffmpeg", "-f", "lavfi", "-i", "color=black:1920x1080",
        "-i", asset["file_path"],
        "-filter_complex", f"[0:v][1:v]overlay=x={asset['position_x']*1920}:y={asset['position_y']*1080}",
        "-frames:v", "1",
        "-f", "null", "-"
    ], capture_output=True, timeout=10)

    assert result.returncode == 0, f"FFmpeg failed: {result.stderr.decode()}"
```

| Test ID | Description | Priority |
|---------|-------------|----------|
| PIPE-001 | Canvas export PNG passes FFmpeg overlay filter without error | P0 |
| PIPE-002 | Canvas export PNG has correct dimensions (1920x1080 default) | P0 |
| PIPE-003 | Canvas export PNG has alpha channel (transparency preserved) | P0 |
| PIPE-004 | Template-instantiated `api_image` asset URL resolves correctly in test environment | P1 |
| PIPE-005 | Asset with `position_x=0.0`, `position_y=0.0` generates correct FFmpeg overlay coordinates | P0 |
| PIPE-006 | Asset with `position_x=1.0`, `position_y=1.0` does not clip (correct boundary handling) | P1 |
| PIPE-007 | Multiple overlays stacked (5 assets) produce valid filter_complex graph | P1 |
| PIPE-008 | `data_bound` asset fallback text renders when data source is unreachable | P1 |

---

## 7. Performance Testing

### 7.1 Canvas Editor Performance

The PRD requires 60fps during drag/resize with up to 50 objects on a CPU-only environment. There is no GPU acceleration inside Docker.

**Test approach:** Browser-based performance profiling using Chrome DevTools. Not automatable in CI -- run manually before each Phase 1 milestone.

**Test script** (`docs/qa/canvas-performance-test.md`):

| Step | Action | Measurement |
|------|--------|-------------|
| 1 | Open canvas editor on the target server (192.168.86.38) | - |
| 2 | Add 50 text objects with random positions | - |
| 3 | Open Chrome DevTools > Performance tab | - |
| 4 | Start recording | - |
| 5 | Select all objects (Ctrl+A) and drag across canvas for 5 seconds | Frame rate in DevTools |
| 6 | Stop recording | - |
| 7 | Report minimum, average, and maximum fps during drag | Target: avg >= 60fps, min >= 45fps |
| 8 | Repeat with 50 image objects (PNG logos) | Same targets |
| 9 | Open a saved project with 100 layers | Load time target: < 2 seconds |

**Automated regression guard:** Add a lightweight browser benchmark test using Playwright:

File: `frontend/e2e/canvas-performance.spec.ts`

```typescript
test('canvas renders 50 objects without layout thrashing', async ({ page }) => {
  // Navigate to canvas editor, inject 50 fabric objects via page.evaluate()
  // Measure frame timing using PerformanceObserver
  // Assert average frame time < 16.7ms (60fps)
});
```

### 7.2 API Performance Targets

| Endpoint | Target p95 | Measurement Method |
|----------|------------|-------------------|
| GET /api/templates | < 200ms | pytest + time.time() in integration test |
| GET /api/canvas-projects (200 projects) | < 500ms | pytest load fixture |
| POST /api/templates/instances | < 500ms | pytest timing |
| PUT /api/canvas-projects/{id} (autosave, 200KB JSON) | < 1000ms | pytest timing |
| POST /api/canvas-projects/{id}/export (1MB PNG) | < 3000ms | pytest timing |
| GET /api/assets (1000 assets) | < 1000ms | pytest load fixture |

File: `backend/tests/test_api_performance.py`

Use `time.time()` around TestClient requests. Seed large datasets via fixtures. These are not load tests -- they verify single-request performance against targets.

### 7.3 FFmpeg Filter Complexity

Adding more concurrent overlay assets increases FFmpeg filter graph complexity and CPU usage.

| Test ID | Description | Target |
|---------|-------------|--------|
| PERF-FF-001 | FFmpeg command with 1 overlay processes test frame in < 100ms | P1 |
| PERF-FF-002 | FFmpeg command with 5 overlays processes test frame in < 300ms | P1 |
| PERF-FF-003 | FFmpeg command with 10 overlays (max) processes test frame in < 500ms | P1 |
| PERF-FF-004 | FFmpeg command with 11 overlays warns/rejects at API level (PRD limit) | P0 |

Use `subprocess.run` with a single-frame encode test (no real video source needed; use `lavfi` color input).

---

## 8. Security Testing

### 8.1 File Upload Security

| Test ID | Attack Vector | Expected Behavior | Test Type |
|---------|--------------|-------------------|-----------|
| SEC-FU-001 | Upload image/png with embedded PHP (polyglot) | Accepted as image; script never executed | Automated |
| SEC-FU-002 | Upload SVG containing `<script>alert(1)</script>` | SVG content is sanitized or rejected | Automated |
| SEC-FU-003 | Upload a 51MB file (over 50MB limit) | 413 response | Automated |
| SEC-FU-004 | Upload with `Content-Type: text/html`, actual content is PNG | MIME validation catches mismatch | Automated |
| SEC-FU-005 | Font upload with `.ttf` extension containing PE header (Windows exe) | Magic bytes validation rejects | Automated |
| SEC-FU-006 | Canvas thumbnail base64 containing malicious data | Pillow decode rejects invalid PNG | Automated |

### 8.2 Template Import Security

| Test ID | Attack Vector | Expected Behavior | Test Type |
|---------|--------------|-------------------|-----------|
| SEC-TI-001 | `.vst-template` with path traversal: `../../etc/passwd` as filename | Rejected at import; no file written outside upload dir | Automated |
| SEC-TI-002 | `.vst-template` with tampered HMAC signature | `400 Invalid package signature` | Automated |
| SEC-TI-003 | `.vst-template` ZIP bomb (deeply nested archives) | Rejected at size/depth check | Automated |
| SEC-TI-004 | `.vst-template` with `definition.json` containing XSS in name field | Field is stored as text; never rendered unescaped | Automated |
| SEC-TI-005 | `.vst-template` with manifest referencing 1,000 files (DoS) | File count limit enforced | Automated |

### 8.3 Canvas JSON XSS

| Test ID | Attack Vector | Expected Behavior | Test Type |
|---------|--------------|-------------------|-----------|
| SEC-CJ-001 | `canvas_json` containing `<script>` in text object `text` property | Sanitized before persistence | Automated |
| SEC-CJ-002 | `canvas_json` containing SVG `src` with `javascript:` URL | Sanitized on load | Automated |
| SEC-CJ-003 | `canvas_json` containing prototype pollution payload | JSON parse is safe; prototype is not modified | Automated |

### 8.4 RBAC Enforcement (Phase 3 -- verify boundary at Phase 1)

Even though full RBAC is Phase 3, the `role` column is added in Phase 1's migration. Verify that the current admin-only model is not broken.

| Test ID | Description | Priority |
|---------|-------------|----------|
| SEC-RBAC-001 | Non-admin user cannot register new users (existing test; regression check) | P0 |
| SEC-RBAC-002 | All new endpoints require authentication (`401` without token) | P0 |
| SEC-RBAC-003 | New user created via migration has `role = "admin"` (backward compat) | P0 |

### 8.5 Security Scanning

| Tool | Purpose | Frequency |
|------|---------|-----------|
| `bandit` (Python SAST) | Static analysis of backend Python code for common vulnerabilities | Every PR |
| `npm audit` | Frontend dependency vulnerability scan | Every PR |
| `pip-audit` | Python dependency vulnerability scan | Every PR |
| Manual penetration test | File upload, import/export, canvas XSS surfaces | Once per phase |

**Add to CI pipeline:**
```bash
# Backend security checks
pip install bandit pip-audit
bandit -r backend/ -ll   # level: LOW and above
pip-audit

# Frontend security checks
npm audit --audit-level=moderate
```

---

## 9. Manual Testing Checklist -- Visual and Canvas Features

These items cannot be reliably automated and must be verified manually before each phase release. They are primarily the Fabric.js visual behaviors.

### 9.1 Canvas Editor Visual Correctness Checklist

**Environment:** Run against the staging Docker instance at 192.168.86.38 using Chrome (latest).

**Section A: Basic Tool Behavior**

- [ ] Text tool: click on canvas creates text object; double-click enables inline text editing
- [ ] Text tool: inline editing supports backspace, cursor movement, and multi-line (Enter key)
- [ ] Rectangle tool: draw produces correct proportional shape with default fill
- [ ] Circle tool: draw produces circle; hold Shift to constrain to perfect circle
- [ ] Line tool: click-drag produces line; two points snap to grid when grid is enabled
- [ ] Image import: drag PNG from desktop adds image to canvas and to layer panel
- [ ] Image import: drag JPEG from desktop adds image to canvas
- [ ] Image import: attempt to drag non-image file shows rejection (no crash)
- [ ] Select tool: click selects object; click blank area deselects
- [ ] Select tool: Ctrl+click adds to selection; drag selects multiple objects via marquee

**Section B: Object Manipulation**

- [ ] Drag: selected object follows mouse smoothly (no jitter at 60fps target)
- [ ] Resize: corner handles resize object; aspect ratio maintained with Shift held
- [ ] Rotate: rotation handle rotates object; Shift constrains to 15-degree increments
- [ ] Nudge: Arrow keys move selected object 1px; Shift+Arrow moves 10px
- [ ] Z-order: layer panel reorder via drag updates visual z-order on canvas instantly
- [ ] Visibility toggle: hiding a layer via eye icon makes object transparent on canvas
- [ ] Lock: locking a layer prevents selection and drag

**Section C: Text Properties**

- [ ] Font family change applies to selected text object immediately
- [ ] Font size change via numeric input applies correctly
- [ ] Bold/italic toggles apply and display correctly in canvas
- [ ] Color picker changes text color; hex input accepts `#RRGGBB` format
- [ ] Text shadow appears correctly (offset, blur visible)
- [ ] Text stroke appears correctly (outline visible on canvas)
- [ ] Text background color renders as a semi-transparent rect behind text

**Section D: Shape Properties**

- [ ] Fill color picker applies fill to selected shape
- [ ] Border (stroke) color and width apply correctly
- [ ] Corner radius (rounded rectangle) renders visually correct
- [ ] Gradient fill (linear) renders correct gradient direction
- [ ] Opacity slider changes object transparency correctly

**Section E: Alignment and Guides**

- [ ] Grid snap: with grid enabled, objects snap to grid intersections while dragging
- [ ] Smart guides: moving an object near another shows alignment guide lines
- [ ] Alignment buttons: align left aligns selected objects' left edges
- [ ] Align center (horizontal) centers selected objects relative to canvas
- [ ] Alignment buttons: align top, align bottom work correctly
- [ ] Rulers along top and left edges show pixel values
- [ ] Safe zone overlay shows title-safe and action-safe margins when toggled

**Section F: Undo/Redo**

- [ ] After each object add/edit/delete, Ctrl+Z restores previous state
- [ ] Ctrl+Z at 50 operations no longer undoes further (history limit)
- [ ] Ctrl+Shift+Z after undo restores forward state
- [ ] Redo is cleared after a new action (branch behavior)

**Section G: Autosave and Recovery**

- [ ] Make edits, wait 10 seconds; close and reopen browser tab; localStorage recovery prompt appears
- [ ] Make edits, wait 65 seconds; check network tab shows PUT to `/api/canvas-projects/{id}`
- [ ] Make edits without saving; navigate away; browser shows "You have unsaved changes" dialog

**Section H: Export**

- [ ] "Export as Asset" generates a PNG download (or saves as asset)
- [ ] Exported PNG has transparent background (not white) when canvas background is transparent
- [ ] Exported PNG dimensions match the configured canvas size (1920x1080 default)
- [ ] Exported PNG correctly represents all visible layers in the correct z-order
- [ ] Exported PNG with text shadow shows the shadow (not just plain text)
- [ ] Export with hidden layers: hidden layers do not appear in the PNG

### 9.2 Template Catalog Visual Checklist

- [ ] Template card thumbnails load for all bundled templates
- [ ] Category filter chips scroll horizontally on narrow screens without overflow
- [ ] Template wizard slide-over shows preview thumbnail at top
- [ ] "Test Connection" button for Tempest template hits the live Tempest API (if available)
- [ ] 9-position grid picker highlights selected position correctly
- [ ] Units toggle (F/C) reflects in the preview

### 9.3 Asset Library Visual Checklist

- [ ] Asset cards display preview thumbnail, name, type badge
- [ ] Canvas composite assets show the exported PNG as their thumbnail
- [ ] Version history slide-over lists versions with timestamps in descending order
- [ ] "Preview" button on a version shows a thumbnail of that version's state
- [ ] Schedule panel shows weekly calendar view with active windows highlighted
- [ ] Analytics tab shows per-asset display time and impression count (Phase 3)

---

## 10. Regression Test Suite

### 10.1 Existing Tests That Must Continue to Pass

The following existing tests must pass without modification after the Asset Management Studio changes are merged. They serve as the baseline regression suite.

**Backend (run `pytest backend/tests/ tests/` from repo root):**

| File | Coverage Area | Criticality |
|------|--------------|-------------|
| `backend/tests/test_auth.py` | Login, registration, RBAC basics, password validation | P0 |
| `backend/tests/test_assets.py` | Asset CRUD (all 5 types), authorization | P0 |
| `backend/tests/test_timelines.py` | Timeline CRUD, tracks, cues, copy, broadcast metadata | P0 |
| `backend/tests/test_ssrf_validation.py` | URL validation for api_image assets | P0 |
| `backend/tests/test_streams.py` | Stream management | P1 |
| `backend/tests/test_cameras.py` | Camera management | P1 |
| `backend/tests/test_destinations.py` | Streaming destinations | P1 |
| `backend/tests/test_audit.py` | Audit log middleware | P1 |
| `tests/test_ffmpeg_manager.py` | FFmpeg process manager | P1 |
| `tests/test_camera_service_status.py` | Camera service | P2 |
| `tests/test_stream_status_endpoint.py` | Stream status | P2 |

**Frontend:**

| File | Coverage Area |
|------|--------------|
| `src/App.test.tsx` | Application renders without crashing |

### 10.2 Regression Scenarios for Existing Asset Functionality

The Asset Management Studio adds new columns and relationships to the `assets` table. Verify that none of these changes break existing behavior:

| Scenario | Verification |
|----------|-------------|
| Create `static_image` asset (existing type) | `template_instance_id` and `canvas_project_id` are NULL; no error |
| Create `api_image` asset (existing type) | `data_binding_config` is NULL; no error |
| Update `api_image` asset | Does not create unwanted version record (versioning may be opt-in; verify design) |
| Delete asset that is referenced by a template instance | Either cascades correctly or returns a meaningful error |
| Timeline overlay with existing asset after migration | Overlay renders correctly (normalized positions unchanged) |
| Asset test proxy endpoint (`/api/assets/{id}/test`) | Continues to work for `api_image` assets; SSRF rules unchanged |

### 10.3 Running the Full Regression Suite

```bash
# From /Users/nickd/Workspaces/VistterStream

# Backend unit + integration tests
cd backend && python -m pytest ../backend/tests/ ../tests/ -v --tb=short

# With coverage
python -m pytest ../backend/tests/ -v --cov=. --cov-report=html

# Frontend component tests (after Vitest setup)
cd frontend && npm test -- --run

# E2E tests (requires Docker stack running)
cd frontend && npx playwright test
```

---

## 11. Test Data Strategy

### 11.1 Backend Test Data

All backend tests use **synthetic, per-test data** seeded via the `db_session` fixture (in-memory SQLite, cleaned after every test). No shared global test state.

**New fixtures to add to `conftest.py`:**

```python
@pytest.fixture
def seeded_template(db_session):
    """An active OverlayTemplate with a weather config schema."""
    template = OverlayTemplate(
        name="Tempest Current Conditions",
        category="weather",
        description="Real-time weather from Tempest station",
        config_schema={
            "required": ["station_id"],
            "properties": {
                "station_id": {"type": "string", "pattern": "^[0-9]{5}$"},
                "units": {"type": "string", "enum": ["F", "C"], "default": "F"},
            }
        },
        default_config={"units": "F", "refresh_interval": 60},
        is_bundled=True,
        is_active=True,
    )
    db_session.add(template)
    db_session.commit()
    return template

@pytest.fixture
def seeded_canvas_project(db_session):
    """A saved canvas project with minimal Fabric.js JSON."""
    project = CanvasProject(
        name="Test Overlay",
        canvas_json='{"version":"6.0.0","objects":[]}',
        width=1920,
        height=1080,
        is_active=True,
    )
    db_session.add(project)
    db_session.commit()
    return project
```

**Large dataset fixtures (for performance tests):**

```python
@pytest.fixture
def large_asset_library(db_session, client):
    """Seeds 1000 assets for pagination/performance testing."""
    headers = _get_auth_header(client, db_session)
    for i in range(1000):
        client.post("/api/assets", json={
            "name": f"Test Asset {i}",
            "type": "api_image",
            "api_url": f"http://192.168.86.38:8036/api/overlay/{i}",
        }, headers=headers)
```

### 11.2 Frontend Test Data

MSW handlers provide mock API responses for component tests.

**File:** `frontend/src/mocks/handlers.ts`

```typescript
import { http, HttpResponse } from 'msw'

export const handlers = [
  // Template catalog
  http.get('/api/templates', () =>
    HttpResponse.json([
      { id: 1, name: 'Tempest Current Conditions', category: 'weather', ... },
      { id: 2, name: 'Lower Third', category: 'lower_third', ... },
    ])
  ),

  // Canvas projects
  http.get('/api/canvas-projects', () =>
    HttpResponse.json([
      { id: 1, name: 'My First Overlay', thumbnail_path: '/uploads/canvas/thumb1.png' },
    ])
  ),

  // Template instantiation
  http.post('/api/templates/instances', () =>
    HttpResponse.json({ asset_id: 42, id: 1 })
  ),
]
```

### 11.3 Pre-Migration Test Data

Store a snapshot of the production database (anonymized) for migration testing:

```
backend/tests/fixtures/
  pre-migration-snapshot.sql   # sqlite3 .dump before Phase 1 migration
  sample-vst-template.zip      # Valid .vst-template package for import tests
  malformed-vst-template.zip   # Invalid package (bad HMAC) for rejection tests
  canvas-export-1920x1080.png  # Reference PNG for FFmpeg pipeline tests
```

### 11.4 What Not to Use as Test Data

- Do not reference `backend/vistterstream.db` in tests -- it is the production database on the server
- Do not use real Tempest station IDs in automated tests -- mock the API instead
- Do not use real Google Fonts API calls in tests -- mock the HTTP client

---

## 12. Quality Gates per Delivery Phase

### 12.1 Phase 1 Exit Criteria

Phase 1 covers: Template Catalog, Configuration Wizards, Canvas Editor (core tools + export), Font Management, Alembic migration.

**Hard gates (must pass -- no exceptions):**

- [ ] All existing tests pass without modification (`pytest backend/tests/ tests/`)
- [ ] Frontend `App.test.tsx` passes
- [ ] All P0 backend tests for new endpoints pass (TC-API, CP-API, FN-API sections above)
- [ ] All P0 security tests pass (SEC section above)
- [ ] Pipeline integration test PIPE-001 through PIPE-006 pass
- [ ] Migration tests MIG-001 through MIG-006 pass
- [ ] Zero P0 defects open
- [ ] Canvas Editor manual checklist Sections A through H completed with no blocking issues

**Soft gates (should pass -- exceptions require written justification):**

- [ ] Backend API coverage >= 80% on new code
- [ ] Frontend component coverage >= 70% on new components
- [ ] API performance targets met (section 7.2)
- [ ] Canvas drag performance >= 45fps minimum with 50 objects (manual test)
- [ ] Zero open P1 defects, or <= 2 with documented workarounds

### 12.2 Phase 2 Exit Criteria

Phase 2 covers: Asset Versioning, Asset Scheduling, Data Bindings (`data_bound` type).

- [ ] All Phase 1 exit criteria remain satisfied (no regression)
- [ ] All AV-* and AS-* service tests pass
- [ ] All AE-API-* extended asset endpoint tests pass
- [ ] SSRF tests for `data_bound` source URLs pass (SEC-003, SEC-004, SEC-005)
- [ ] Schedule correctness: `is_asset_active_now` passes for all timezone scenarios
- [ ] Version revert creates a new version (not destructive edit) -- verified by test AV-005
- [ ] Manual checklist: Version History and Scheduling panels verified

### 12.3 Phase 3 Exit Criteria

Phase 3 covers: Asset Groups, Analytics, RBAC, Import/Export.

- [ ] All Phase 2 criteria remain satisfied
- [ ] Import/export path traversal and ZIP bomb tests pass
- [ ] HMAC signature verification test passes
- [ ] RBAC: Designer role cannot access stream management endpoints
- [ ] RBAC: Operator role cannot create or edit assets
- [ ] Analytics: display log aggregate query completes in < 1 second for 90-day log

### 12.4 Bug Severity Definitions

| Severity | Definition | Response |
|----------|------------|----------|
| P0 - Critical | Canvas export produces broken PNG; migration corrupts database; stream stops due to asset bug; SSRF validation bypass | Immediate; blocks release |
| P1 - High | Template wizard produces incorrect asset config; undo/redo loses data; SSRF blocks legitimate TempestWeather URL; autosave fails silently | Fix in current sprint or document workaround |
| P2 - Medium | Layer panel drag-to-reorder wrong direction; alignment guides imprecise; font not available in list | Fix before next phase |
| P3 - Low | Minor visual glitch; incorrect default value in wizard; typo in label | Backlog |

---

## 13. Continuous Integration

### 13.1 Recommended CI Pipeline (GitHub Actions / local runner)

```yaml
# .github/workflows/qa.yml (or run locally via act)

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt pytest pytest-cov bandit pip-audit
      - run: cd backend && python -m pytest ../backend/tests/ -v --cov=. --cov-report=xml
      - run: bandit -r backend/ -ll -q
      - run: pip-audit

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd frontend && npm ci && npm test -- --run
      - run: cd frontend && npm audit --audit-level=moderate

  migration-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest ../backend/tests/test_migrations.py -v
```

### 13.2 Pre-Merge Checklist

Before any PR merging changes to backend routers, services, or models:

- [ ] `pytest backend/tests/test_assets.py` passes (asset regression)
- [ ] `pytest backend/tests/test_timelines.py` passes (timeline regression)
- [ ] `pytest backend/tests/test_ssrf_validation.py` passes (security regression)
- [ ] New router changes have corresponding test file
- [ ] New Alembic migration has corresponding migration test

---

## 14. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Fabric.js v6 canvas API behavior differs from expected (jsdom incompatibility) | High | High | Accept this limitation; test canvas logic unit tests separately from visual tests; rely on manual protocol for visual correctness |
| SQLite WAL mode locking during concurrent autosave + API requests | Medium | Medium | Test autosave under concurrent load; document WAL configuration; test MIG-008 |
| FFmpeg filter_complex breaks when canvas PNG has unexpected color profile | High | Low | Validate PNG color profile in export service (Pillow: ensure sRGB, no ICC profile issues); add PIPE-001 to CI |
| Migration rollback fails on production database due to existing data | High | Low | Test MIG-006 against pre-migration snapshot; require DBA sign-off before production migration |
| Google Fonts API changes response format | Low | Medium | Mock in tests; add version pinning to font catalog endpoint |
| SSRF via canvas image import (user drags a URL-linked image) | High | Low | Canvas image import must not make server-side HTTP requests; images are base64-encoded client-side before upload |
| localStorage autosave collision (two browser tabs open same project) | Medium | Low | Document in UX; last-write-wins on server; add test CP-API-009 |
| Template import ZIP with path traversal writes outside upload dir | Critical | Low | SEC-TI-001 covers this; use `zipfile.ZipFile` safe extraction pattern |

---

## 15. Open Questions

These questions need answers before writing specific tests for the affected areas:

- [ ] **Autosave versioning:** Does every PUT to `/api/canvas-projects/{id}` create an asset version record, or only explicit "Save as Asset" exports? (affects AV-* test design)
- [ ] **Data_bound rendering:** In Phase 2, does the backend render `data_bound` assets to images (like `api_image`), or does the frontend render them? (affects pipeline test design)
- [ ] **MIME validation for canvas export:** Does the export endpoint validate that the submitted blob is actually a valid PNG, or does it trust the frontend? (affects SEC-FU-006)
- [ ] **Template test connection:** Does the `test_connection` call originate from the frontend (browser) or is it proxied through the backend? If through the backend, SSRF validation must apply.
- [ ] **Asset type enum:** Is `data_bound` and `canvas_composite` stored as a string column or a Python/Pydantic enum? (affects backward compatibility of existing enum validation)
- [ ] **Font availability in Docker:** Which system fonts are guaranteed available in `python:3.11-slim-bookworm`? This affects which fonts can be used safely in templates. (affects FS-009 and canvas export tests)
- [ ] **Version snapshot behavior:** Is versioning opt-in (user clicks "Save Version") or automatic on every edit? (affects AV-001 test setup)

---

## 16. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-15 | Nick DeMarco with AI Assistance | Initial draft |
