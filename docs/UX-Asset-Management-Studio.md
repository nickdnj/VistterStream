# UX Design Specification: VistterStream Asset Management Studio

**Version:** 0.1
**Last Updated:** 2026-03-15
**Author:** Nick DeMarco with AI Assistance
**Status:** Draft
**PRD Reference:** `docs/PRD-Asset-Management-Studio.md`

---

## 1. Executive Summary

### 1.1 Design Vision

The Asset Management Studio transforms VistterStream from a streaming tool that happens to support overlays into a creative platform where any stream operator -- regardless of design experience -- can produce professional, dynamic stream graphics. The UX must feel like a control room operator's toolkit: purposeful, organized, and efficient. It should never feel like a consumer design app or an enterprise CMS.

### 1.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Studio entry point | New "Asset Studio" top-level nav item replacing current Assets link | The Studio is a significant enough feature set to warrant its own navigation home; surfaces the catalog immediately |
| Canvas editor surface | Dedicated full-page route, not a modal | Canvas editing requires focused workspace; modals are too constrained for a multi-panel tool |
| Template catalog | Tab within Asset Studio, not a separate page | Keeps templates and personal assets spatially adjacent; easy switching |
| Configuration wizard | Slide-over panel, not a full modal | Allows catalog to remain visible for reference; feels lighter than a full-screen takeover |
| Layer panel | Left side of canvas editor | Mirrors convention from Figma, Photoshop, and video editors familiar to target users |
| Properties panel | Right side of canvas editor | Standard right-side placement for properties; mirrors existing industry convention |
| "Coming Soon" templates | Visible but disabled with lock badge | Shows the roadmap; creates anticipation without confusion about what's available today |
| Scheduling UI | Inline panel on asset detail, not a separate page | Schedule is a property of an asset; keeping it contextual reduces navigation |
| Version history | Slide-over panel on asset detail | History is an infrequent operation; slide-over avoids a full navigation jump |

### 1.3 Design Principles

- **Progressive complexity:** The simplest path (pick a template, fill in two fields) should take under 2 minutes. Power features (canvas editor, data bindings) are discoverable but not in the way.
- **Confidence through preview:** Every configuration decision shows a live or static preview before the user commits. No surprises on the stream.
- **Operator-grade efficiency:** Keyboard shortcuts, batch operations, and drag-and-drop are first-class. These users run streams, not design exercises.
- **Dark-first:** All UI is designed for the existing dark theme (`bg-dark-800`, `bg-dark-900`). Stream operators work in dimly lit control rooms and dark UIs are preferred.
- **Error recovery over error prevention:** Undo, version history, and draft saves prevent catastrophic mistakes. Warn but do not block.

---

## 2. User Personas

### 2.1 Primary Persona: The Cam Operator (Sam)

**Demographics:**
- Age: 40-65
- Technical comfort: Low-to-medium (comfortable with web interfaces, not with code)
- Device preference: Desktop browser
- Session pattern: Weekly configuration, then set-and-forget

**Goals:**
- Add a weather overlay to a 24/7 unattended beach stream
- Have it update automatically without any ongoing intervention
- Look professional without hiring a designer

**Pain Points:**
- Current system requires knowing what "API URL" means to add dynamic content
- Position is expressed as 0.0-1.0 floats which is not intuitive
- No way to preview what an overlay will look like before it goes live

**Quote:**
> "I just want to see the temperature in the corner. I don't know what an API endpoint is."

### 2.2 Secondary Persona: The Community Producer (Jordan)

**Demographics:**
- Age: 30-50
- Technical comfort: Medium (comfortable with web tools, has used Canva or similar)
- Device preference: Desktop browser
- Session pattern: Active during event prep, then monitoring during broadcasts

**Goals:**
- Create sponsor logo overlays for local business advertisers
- Rotate sponsor logos every 30 seconds automatically
- Show a lower third when introducing speakers

**Pain Points:**
- No way to create graphics in VistterStream; must use external tools and then upload
- Scheduling overlays per-asset is not currently possible
- Managing 10+ assets is tedious with the current flat list

**Quote:**
> "I need to build the ad, upload it, and then tell the system when to show it. Right now that's three different things that don't talk to each other."

### 2.3 Tertiary Persona: The Small Broadcaster (Alex)

**Demographics:**
- Age: 25-40
- Technical comfort: High (developer or technically experienced)
- Device preference: Desktop browser
- Session pattern: Deep work sessions for setup, then routine monitoring

**Goals:**
- Build a complete branded overlay package for a multi-day event
- Group lower thirds, sponsor logos, and a weather widget into a reusable bundle
- Export the bundle to use on a different VistterStream instance next year

**Pain Points:**
- No grouping or composition tools
- Cannot version-control overlay designs
- Cannot export/import between instances

**Quote:**
> "I build the same overlay package from scratch every year for this tournament. I just want to save it and load it next time."

---

## 3. Information Architecture

### 3.1 Site Map (Updated)

```
VistterStream
├── Dashboard
├── Timelines
├── Asset Studio                   [NEW - replaces bare "Assets" link]
│   ├── My Assets                  [enhanced version of current Assets page]
│   │   ├── All Assets (grid)
│   │   ├── Asset Groups
│   │   └── Canvas Projects
│   ├── Template Catalog           [NEW]
│   │   ├── Category: Weather
│   │   ├── Category: Marine
│   │   ├── Category: Time / Date
│   │   ├── Category: Sponsor / Ad
│   │   ├── Category: Lower Thirds
│   │   ├── Category: Social Media  [Coming Soon]
│   │   └── Category: Custom
│   ├── Canvas Editor              [NEW - full-page route]
│   │   ├── (project open)
│   │   └── (new project)
│   └── Analytics                  [NEW]
├── ReelForge
└── Settings
```

### 3.2 Navigation Model

**Primary navigation:** Left sidebar (existing pattern, collapsible). "Asset Studio" replaces the current link that leads to the asset management page. The icon is a palette or layers icon (distinct from the current camera/film icons already in use).

**Secondary navigation within Asset Studio:** Horizontal tab bar at the top of the Asset Studio section. Tabs: My Assets | Template Catalog | Canvas Editor | Analytics. The tab bar is persistent within the Studio -- switching tabs does not lose state.

**Canvas Editor navigation:** Canvas Editor opens as a dedicated full-page route (`/asset-studio/canvas/:projectId` or `/asset-studio/canvas/new`). A breadcrumb at the top-left provides a back link to Asset Studio without losing unsaved work (triggers save prompt if dirty).

**Contextual panels:** Slide-over panels (right-side drawers) are used for: template configuration wizard, asset detail/edit, version history, scheduling configuration. These overlay the main content without full navigation.

### 3.3 Content Hierarchy

| Content Type | Priority | Location |
|--------------|----------|----------|
| Template Catalog | High (onboarding path) | Second tab in Asset Studio; also surfaced as a CTA in the empty state of My Assets |
| My Assets grid | High | First tab in Asset Studio (default view) |
| Canvas Projects | Medium | Sub-section within My Assets tab, below individual assets |
| Asset Groups | Medium | Sub-section within My Assets tab |
| Analytics | Low (power feature) | Fourth tab, not default |
| Import/Export | Low (utility) | Toolbar buttons in My Assets and Template Catalog tabs |

---

## 4. User Flows

### 4.1 Flow: Add Weather Overlay via Template (Primary Happy Path)

**Entry points:**
- Sidebar > Asset Studio (lands on My Assets tab, empty state shows "Browse Templates" CTA)
- Sidebar > Asset Studio > Template Catalog tab

**Happy path:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Asset Studio │────▶│  Template    │────▶│  Weather     │────▶│  Configure   │────▶│  Asset       │
│  (My Assets   │     │  Catalog tab │     │  template    │     │  wizard      │     │  created +   │
│   empty state)│     │              │     │  card        │     │  (slide-over)│     │  in My Assets│
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

**Step-by-step:**
1. User clicks "Asset Studio" in sidebar, lands on My Assets tab (empty state)
2. Empty state shows "Browse Templates" primary button
3. User clicks button, switches to Template Catalog tab
4. User sees category filter set to "All"; clicks "Weather" category chip
5. Catalog shows 2-3 weather templates ("Current Conditions", "5-Day Forecast", "Marine Weather")
6. User clicks the "Current Conditions" card
7. Configuration slide-over opens on the right side
8. Slide-over shows: preview thumbnail at top, then form fields below
9. Required field: Station ID (text input with helper link "Find your station ID")
10. Optional fields: Position (9-position grid picker), Units (F/C toggle), Theme (Light/Dark toggle), Refresh interval (slider: 30s default)
11. "Test Connection" button appears below Station ID field; user clicks it
12. Success indicator: green checkmark + live preview updates with real data from the station
13. User clicks "Create Asset" button
14. Slide-over closes, success toast appears: "Weather overlay created"
15. User is returned to My Assets tab, new asset card is visible at the top of the grid
16. User can now add the asset to a timeline from the asset card's action menu

**Alternative paths:**
- User searches "weather" from the search bar in the catalog header
- User enters an invalid station ID; inline error appears below the field; "Create Asset" button remains disabled

**Error scenarios:**
| Error | User Sees | Recovery Action |
|-------|-----------|-----------------|
| Invalid station ID format | "Station IDs are 5 digits (e.g., 12345)" below field | Correct the input |
| Station ID not found / API unreachable | "Could not connect to weather station. Check the ID and try again." | Test button shows error state; user can still save with a warning |
| Template configuration incomplete | "Complete required fields to create this asset" inline at bottom of form | Fill remaining required fields |

### 4.2 Flow: Create Ad Overlay in Canvas Editor

**Entry points:**
- My Assets tab > "New Canvas Project" button
- Template Catalog > "Sponsor / Ad" template > "Open in Canvas Editor" option within wizard

**Happy path:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  My Assets   │────▶│  Canvas      │────▶│  Design ad   │────▶│  Export to   │────▶│  Asset saved │
│  "New Canvas │     │  Editor      │     │  (layers,    │     │  PNG         │     │  to My Assets│
│   Project"   │     │  (new blank) │     │   text, logo)│     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

**Step-by-step:**
1. User clicks "New Canvas Project" button
2. New project dialog appears (name input, optional description, resolution selector defaulting to 1920x1080)
3. User names project "ABC Hardware - March 2026" and clicks "Create"
4. Canvas Editor page loads; blank transparent canvas fills the center area
5. User drags and drops a logo image from their computer onto the canvas
6. Logo appears on canvas; Layer panel on left shows "Image 1"
7. User double-clicks "Image 1" in layer panel and renames it "ABC Hardware Logo"
8. User selects the Rectangle tool from the toolbar, draws a wide rectangle at the bottom for a lower-third background
9. Properties panel on right shows fill color, opacity, corner radius; user sets fill to dark blue, opacity to 85%
10. User clicks Text tool, clicks on the canvas above the rectangle, types "ABC Hardware"
11. Properties panel shows font controls; user sets font to "Roboto Bold", size 48, color white
12. User clicks Align Center button in the toolbar to center text on canvas
13. User adds a subtitle text "123 Main Street | 555-0100" in smaller size below
14. Auto-save indicator shows "Saved" at 60-second intervals
15. User clicks "Export" button in toolbar
16. Export dialog appears: filename (pre-filled from project name), format (PNG), resolution confirmed
17. User clicks "Export and Save as Asset"
18. Progress indicator: "Generating... Uploading..."
19. Success: "Asset created: ABC Hardware - March 2026. View in My Assets."
20. Canvas project remains open for further editing; the exported asset is now available in My Assets

**Alternative paths:**
- User uses "Export Only" (no automatic asset creation; just downloads PNG)
- User saves project without exporting (project remains as canvas project, no static image asset yet)
- User opens an existing canvas project from the My Assets > Canvas Projects sub-section

### 4.3 Flow: Configure Asset Scheduling (Ad Rotation)

**Entry points:**
- My Assets asset card > "Schedule" action
- Asset detail panel > Schedule tab

**Happy path:**
1. User has 3 sponsor logo assets (ABC Hardware, Bay View Marina, Sunrise Coffee)
2. User opens the asset detail for "ABC Hardware" (clicks card, or uses the action menu)
3. Asset detail slide-over opens; user clicks "Schedule" tab
4. Schedule panel shows: Schedule Type (dropdown: Always On / Time Window / Rotation Group)
5. User selects "Rotation Group"
6. New section appears: "Rotation Group" -- input for group name ("Spring Sponsors") + "Add to group" to include other assets
7. User clicks "Add to group", selects "Bay View Marina" and "Sunrise Coffee" from a multi-select asset picker
8. Rotation interval slider appears: 30 seconds (default); user sets it to 45 seconds
9. Optional: Time Window toggle -- user enables it, sets display hours Mon-Fri 8am-8pm
10. Weekly calendar preview appears at the bottom of the schedule panel showing shaded active hours
11. User clicks "Save Schedule"
12. Success toast: "Rotation group 'Spring Sponsors' saved"
13. Asset cards for all three sponsors now show a "Scheduled" badge

### 4.4 Flow: Browse and Revert Version History

**Entry points:**
- Asset card action menu > "Version History"
- Asset detail slide-over > "History" tab

**Happy path:**
1. User opens version history for an asset that has been edited multiple times
2. History slide-over shows a timeline of versions (most recent first)
3. Each version entry: version number, timestamp, who changed it, thumbnail, change description
4. User clicks "Preview" on version 3 (two versions ago)
5. Preview panel opens within the slide-over showing the version 3 thumbnail at full size
6. User confirms this is the version they want
7. User clicks "Revert to this version"
8. Confirmation prompt: "This will create a new version (v6) with the content from v3. Your current version is not deleted."
9. User confirms; new version record created; asset updated to v3 content
10. Success toast: "Reverted to version 3. A new version (v6) was created."

---

## 5. Wireframe Specifications

### 5.1 Screen: Asset Studio - My Assets Tab (Default View)

**Purpose:** Home base for all asset management. The user arrives here from the sidebar link. Shows all personal assets in a scannable grid with access to all asset management actions.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SIDEBAR  │  Asset Studio                                                        │
│           │  ┌──────────────────────────────────────────────────────────────┐   │
│ Dashboard │  │  My Assets  │  Template Catalog  │  Canvas Editor  │ Analytics│   │
│           │  └──────────────────────────────────────────────────────────────┘   │
│ Timelines │                                                                      │
│           │  ┌─────────────────────────────────────────────────────────────┐    │
│ Asset     │  │ Search: [___________________]  [Filter ▾] [Import] [Export] │    │
│ Studio  ◀ │  │                              [+ New Asset] [New Canvas Proj] │    │
│           │  └─────────────────────────────────────────────────────────────┘    │
│ ReelForge │                                                                      │
│           │  Sub-nav: [All] [Images] [Videos] [Templates] [Groups] [Canvas]      │
│ Settings  │                                                                      │
│           │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│           │  │ [preview]│ │ [preview]│ │ [preview]│ │ [preview]│               │
│           │  │          │ │          │ │          │ │  +       │               │
│           │  │ Asset 1  │ │ Asset 2  │ │ Asset 3  │ │ New Asset│               │
│           │  │ weather  │ │ ABC logo │ │ tide ch..│ │          │               │
│           │  │[•] Sched │ │ Static   │ │ API Image│ │          │               │
│           │  │[Edit][..] │ │[Edit][..]│ │[Edit][..]│ │          │               │
│           │  └──────────┘ └──────────┘ └──────────┘ └──────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Component breakdown:**

Tab bar: Horizontal, full-width, below the page heading area. Active tab has a bottom border in `primary-600`. Tabs: My Assets (default), Template Catalog, Canvas Editor (links to current project or new project dialog), Analytics.

Toolbar (below tab bar): Two rows on mobile, single row on desktop.
- Row 1 left: Search input (full-text search across asset names and descriptions)
- Row 1 right: Filter dropdown (type, status, scheduled/unscheduled), Import button, Export button
- Row 2 right: "New Asset" primary button (opens the existing asset creation flow), "New Canvas Project" secondary button

Sub-filter chips: Below the toolbar. Horizontal scrolling chip group: All | Images | Videos | API Images | Templates | Groups | Canvas Projects. Selected chip is filled `primary-600`. These filter the grid below without reloading.

Asset grid: 3 columns on desktop (lg), 2 on tablet (md), 1 on mobile. Grid items are cards with aspect-ratio preview area (16:9), then metadata and actions below. Matches the existing card pattern.

**Enhanced asset card (vs. current):**

```
┌─────────────────────────────────────┐
│  [16:9 preview area]                │
│                          [TYPE BADGE]│
│                          [SCHED DOT] │
├─────────────────────────────────────┤
│  Asset Name (truncate 1 line)       │
│  Description (truncate 2 lines)     │
│                                     │
│  Position: Top Right                │
│  Opacity: 90%                       │
│  Refresh: 60s         (if api)      │
│  v3 · Last edited 2h ago            │
├─────────────────────────────────────┤
│ [Edit]  [Schedule] [History] [...]  │
└─────────────────────────────────────┘
```

New elements vs. current card:
- "Scheduled" green dot badge on the preview image (top-left corner) when an active schedule exists
- Version number + last-edited timestamp in the metadata section
- "Schedule" action button in the footer (currently absent)
- "History" action button in the footer (currently absent)
- "..." overflow menu contains: Duplicate, Test Connection (if API), Export, Delete

**States:**

Empty state (no assets):
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│                  [Layers icon, large]                │
│                                                      │
│         No overlays yet                              │
│         Get started with a pre-built template        │
│         or create one from scratch.                  │
│                                                      │
│  [ Browse Template Catalog ]  [ New Canvas Project ] │
│                                                      │
└──────────────────────────────────────────────────────┘
```

Loading state: Skeleton cards (dark shimmer rectangles) in the grid position during initial load.

### 5.2 Screen: Asset Studio - Template Catalog Tab

**Purpose:** Browsable library of pre-built overlay templates. Primary onboarding path for new users.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  SIDEBAR  │  Asset Studio                                                        │
│           │  [ My Assets ] [ Template Catalog ] [ Canvas Editor ] [ Analytics ] │
│           │                      ↑ active tab                                    │
│           │  ┌─────────────────────────────────────────────────────────────┐    │
│           │  │ Search templates: [_____________________]         [Import ▾] │    │
│           │  └─────────────────────────────────────────────────────────────┘    │
│           │                                                                      │
│           │  Category filter chips:                                              │
│           │  [All] [Weather] [Marine] [Time/Date] [Sponsor/Ad] [Lower Thirds]   │
│           │  [Social Media 🔒] [Custom]                                          │
│           │                                                                      │
│           │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│           │  │ [thumbnail]  │ │ [thumbnail]  │ │ [thumbnail]  │               │
│           │  │              │ │              │ │  COMING SOON │               │
│           │  │Current       │ │5-Day Forecast│ │ Social Feed  │               │
│           │  │Conditions    │ │              │ │ 🔒           │               │
│           │  │Tempest data  │ │Tempest data  │ │              │               │
│           │  │ ★★★★☆ (12)  │ │ ★★★★★ (8)  │ │              │               │
│           │  │[Use Template]│ │[Use Template]│ │[Notify me]   │               │
│           │  └──────────────┘ └──────────────┘ └──────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Component breakdown:**

Search bar: Single input field at the top. Searches template name and description. Instant filter (no submit required). Clears with X button.

Category chips: Horizontal scrolling chip row. Chips: All, Weather, Marine, Time/Date, Sponsor/Ad, Lower Thirds, Social Media (with lock icon), Custom. Multiple categories can be selected simultaneously. "Social Media" chip shows lock icon badge and is selectable but the templates within it show "Coming Soon" state.

Template cards: 3-column grid (same breakpoints as asset grid).

```
┌─────────────────────────────────────┐
│  [Thumbnail - 16:9 aspect ratio]   │
│                        [CATEGORY]   │
├─────────────────────────────────────┤
│  Template Name                      │
│  Brief description (2 lines max)    │
│                                     │
│  Requires: Station ID               │
│  ★★★★☆  12 uses                    │
├─────────────────────────────────────┤
│     [ Use Template ]                │
└─────────────────────────────────────┘
```

"Coming Soon" card variant: Same layout but with a semi-transparent overlay on the thumbnail containing a lock icon and "Coming Soon" text. The "Use Template" button becomes "Notify Me" (to register interest). The card is visually de-emphasized with reduced opacity on the body text.

Template thumbnails: Static PNG screenshots showing the overlay rendered on a sample stream background. Shipped with the Docker image.

**Template detail slide-over (opens when "Use Template" is clicked):**

A right-side slide-over panel, 480px wide on desktop. Structure:
```
┌──────────────────────────────────────────────────────┐
│  [X]  Current Conditions                     Weather  │
│  ─────────────────────────────────────────────────── │
│  [Full-width preview: overlay on sample background]  │
│  [Preview updates live as fields change]             │
│  ─────────────────────────────────────────────────── │
│  Configure this template                             │
│                                                      │
│  Station ID *                                        │
│  [____________]  [Test Connection]                   │
│  ✓ Connected - Station: Smith Beach (12345)          │
│                                                      │
│  Position                                            │
│  ┌───┬───┬───┐                                       │
│  │ ○ │ ○ │ ● │  Top Right (selected)                │
│  ├───┼───┼───┤                                       │
│  │ ○ │ ○ │ ○ │                                       │
│  ├───┼───┼───┤                                       │
│  │ ○ │ ○ │ ○ │                                       │
│  └───┴───┴───┘                                       │
│                                                      │
│  Units         ○ Fahrenheit  ● Celsius               │
│  Theme         ○ Light       ● Dark                  │
│  Refresh       [─────●──────] 60 seconds             │
│                                                      │
│  ─────────────────────────────────────────────────── │
│  [ Cancel ]              [ Create Asset ]            │
└──────────────────────────────────────────────────────┘
```

Position picker: A 3x3 grid of radio-button circles representing 9 screen positions (top-left through bottom-right). Currently selected position is highlighted with `primary-600` fill. This replaces the current raw 0.0-1.0 numeric inputs for the template flow (raw inputs remain available in the full asset edit form for power users).

"Test Connection" button behavior: Inline beside the Station ID field. Triggers API validation. States:
- Default: Gray outline button, "Test Connection"
- Loading: Spinner, "Testing..."
- Success: Green background, checkmark, "Connected" + station name shown below
- Error: Red background, X, "Could not connect" + specific error detail below

Live preview: The thumbnail at the top of the slide-over updates within 1-2 seconds when Station ID is tested successfully, showing real data. For templates where live preview is not possible (e.g., no API connection), the preview shows sample/mock data with a "Sample data shown" label.

Scroll behavior: The slide-over content is scrollable; the Cancel/Create Asset footer is sticky at the bottom.

### 5.3 Screen: Canvas Editor

**Purpose:** Full-page browser-based canvas editor for creating custom overlay graphics. Replaces external tools (Canva, Photoshop) for overlay design tasks.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ← Asset Studio  /  ABC Hardware - March 2026                     [Saved ✓]  [Export]  [Save]   │
├──────────────┬──────────────────────────────────────────────────────┬────────────────────────── │
│ LAYER PANEL  │  TOOLBAR                                             │  PROPERTIES PANEL          │
│  240px wide  │  ──────────────────────────────────────────────      │  280px wide                │
│              │  [▾] [◻] [T] [⬭] [/] [⬡] [img] | [⊞] [⊟]        │                            │
│ ┌──────────┐ │  Sel  Rect Text Ell Line Shape Img  Zoom+  Zoom-   │  (nothing selected)        │
│ │ Layers  +│ │  ─────────────────────────────────────────────────  │  Select an object to see  │
│ ├──────────┤ │                                                      │  its properties            │
│ │👁🔒ABC   │ │         CANVAS AREA                                 │                            │
│ │   Logo   │ │   ┌──────────────────────────────────────────┐     │                            │
│ │          │ │   │                                          │     │  (when layer selected)     │
│ │👁🔒BG    │ │   │  [checkerboard = transparent background] │     │                            │
│ │   Rect   │ │   │                                          │     │  Position                  │
│ │          │ │   │        ABC Hardware                      │     │  X [______]  Y [______]    │
│ │👁🔒Title │ │   │  ═══════════════════════════════════     │     │                            │
│ │   Text   │ │   │  123 Main St | 555-0100                  │     │  Size                      │
│ │          │ │   │                                          │     │  W [______]  H [______]    │
│ │👁🔒Sub   │ │   └──────────────────────────────────────────┘     │  [Lock aspect ratio ⛓]    │
│ │   Text   │ │         1920 x 1080 px                             │                            │
│ │          │ │                                                      │  Rotation                  │
│ │ + Add    │ │  Status: 4 layers | 100% zoom                       │  [_____°]  [↺]  [↻]       │
│ └──────────┘ │                                                      │                            │
│              │                                                      │  Opacity                   │
│              │                                                      │  [──────●──────]  90%      │
│              │                                                      │                            │
│              │                                                      │  Fill Color                │
│              │                                                      │  [████] #1A2B8C  [A: 100] │
│              │                                                      │                            │
│              │                                                      │  Border                    │
│              │                                                      │  [None ▾]                  │
└──────────────┴──────────────────────────────────────────────────────┴────────────────────────── ┘
```

**Layer panel (left, 240px):**

Header: "Layers" label + "+" button to add a new layer. Layers listed in z-order (topmost layer at the top of the list = rendered on top of the canvas). Each row:

```
[👁] [🔒]  [layer name (truncated)]  [type icon]  [⋮]
```

- Eye icon: toggle visibility. Clicked = hidden, dimmed eye. Visible = active eye icon.
- Lock icon: toggle lock. Locked = fill lock icon; object cannot be selected or moved on canvas. Used to protect background elements.
- Layer name: Click to select the layer. Double-click to rename (inline edit).
- Type icon: small icon indicating layer type (image, text, shape).
- Overflow menu (⋮): Duplicate, Delete, Group, Move to Top, Move to Bottom.

Reordering: Drag a layer row up or down to change z-order. Drop target indicator (horizontal line) shows where the layer will be placed.

Selection: Clicking a layer row selects it; the corresponding object on the canvas is selected (blue handles appear). Multiple selection: Cmd/Ctrl+click to select multiple layers.

**Canvas area (center):**

Background: Dark gray (`bg-dark-900`) surrounding a white checkerboard pattern indicating transparent areas.

Canvas: The actual working area rendered by Fabric.js. Fills the available center space with scroll/pan if zoomed in. The canvas document is the specified resolution (1920x1080 default) scaled to fit the available space.

Rulers: Thin rulers along the top and left edges showing pixel coordinates relative to the canvas origin. Toggle visibility via View menu or keyboard shortcut (Cmd/Ctrl+R).

Safe zones: Optional overlay (toggle in View menu) showing title-safe (90% of canvas) and action-safe (80% of canvas) boundaries as dashed lines. Relevant for broadcast operators who need to keep content away from screen edges.

Canvas status bar: Below the canvas area, shows: number of layers, current zoom percentage, canvas dimensions.

**Toolbar (horizontal bar below the breadcrumb header):**

Tool buttons in groups:
- Group 1 (Selection tools): Select (arrow), Multi-select
- Group 2 (Draw tools): Rectangle, Text, Ellipse, Line, Custom shape
- Group 3 (Import): Image import (opens file picker or asset library picker)
- Group 4 (View controls): Zoom In, Zoom Out, Fit to Screen
- Group 5 (Alignment, visible when 2+ objects selected): Align Left, Center, Right, Top, Middle, Bottom | Distribute Horizontal, Distribute Vertical
- Group 6 (Edit): Undo, Redo, Snap-to-grid toggle, Guides toggle

**Properties panel (right, 280px):**

Context-sensitive based on selected layer type. Scrollable panel with grouped sections:

When nothing is selected:
- Canvas properties (dimensions, background color/transparency)

When a shape is selected:
- Position (X, Y numeric inputs, pixel values)
- Size (W, H with aspect lock toggle)
- Rotation (degree input, clockwise/counter-clockwise buttons)
- Opacity (slider + numeric)
- Fill (color swatch + hex input + alpha; solid/gradient selector)
- Border (toggle, color, width, dash pattern)
- Corner radius (for rectangles)

When a text layer is selected:
- All shape properties above, plus:
- Font family (searchable dropdown)
- Font size (numeric input with +/- stepper)
- Font style (Bold, Italic, Underline toggles)
- Text alignment (Left, Center, Right, Justify)
- Text color (color swatch)
- Line height (numeric)
- Letter spacing (numeric)
- Text shadow (toggle + offset X, offset Y, blur, color)
- Text stroke/outline (toggle + width + color)
- Text background (toggle + color + opacity)

When an image layer is selected:
- Position, Size, Rotation, Opacity (same as shape)
- Flip Horizontal, Flip Vertical buttons
- Crop (opens inline cropping handles on canvas)
- Blend mode dropdown (Normal, Multiply, Screen, Overlay)

**Export dialog:**

```
┌──────────────────────────────────────────────────────┐
│  Export Canvas                                       │
│  ──────────────────────────────────────────────────  │
│  Filename                                            │
│  [ABC Hardware - March 2026________________]         │
│                                                      │
│  Format         ● PNG  ○ JPEG                       │
│  Resolution     [1920] x [1080] px                  │
│  Scale          100% ▾   (results in 1920×1080)     │
│                                                      │
│  ──────────────────────────────────────────────────  │
│  After export:                                       │
│  ● Save as new asset in My Assets                    │
│  ○ Download only (no asset created)                  │
│                                                      │
│  Asset name (if saving):                             │
│  [ABC Hardware - March 2026________________]         │
│  ──────────────────────────────────────────────────  │
│  [ Cancel ]          [ Export ]                      │
└──────────────────────────────────────────────────────┘
```

**Project save and auto-save:**

Breadcrumb header shows save state:
- "Saved ✓" in gray when clean
- "Saving..." with spinner during save
- "Unsaved changes" with dot indicator when dirty
- "Auto-saved 2m ago" after auto-save

The "Save" button at top-right triggers a manual save. Auto-save runs every 60 seconds when there are unsaved changes.

New project dialog (shown before canvas editor opens):
```
┌──────────────────────────────────────────────────────┐
│  New Canvas Project                                  │
│  ──────────────────────────────────────────────────  │
│  Project Name *                                      │
│  [________________________________________]          │
│                                                      │
│  Description (optional)                              │
│  [________________________________________]          │
│                                                      │
│  Canvas Size                                         │
│  ● 1920 × 1080 (Full HD, recommended)               │
│  ○ 1280 × 720 (HD)                                  │
│  ○ 3840 × 2160 (4K)                                 │
│  ○ Custom: [_____] × [_____]                         │
│  ──────────────────────────────────────────────────  │
│  [ Cancel ]              [ Create Project ]          │
└──────────────────────────────────────────────────────┘
```

### 5.4 Screen: Asset Detail Slide-over

**Purpose:** View and edit a single asset's full configuration without leaving the My Assets grid. Replaces the current full-screen modal.

**Trigger:** Click an asset card (not an action button). Or click "Edit" in the asset card footer.

**Layout:** Right-side slide-over panel, 520px wide. Main content area is scrollable. Tab navigation within the slide-over.

```
┌──────────────────────────────────────────────────────┐
│  [X]  ABC Hardware Logo             Static Image      │
│  ──────────────────────────────────────────────────── │
│  [ Settings ] [ Schedule ] [ History ]               │
│  ──────────────────────────────────────────────────── │
│                                                      │
│  (Settings tab - default)                            │
│                                                      │
│  [Preview thumbnail - 16:9]                          │
│                                                      │
│  Asset Name                                          │
│  [ABC Hardware Logo_______________________]          │
│                                                      │
│  Description                                         │
│  [_________________________________________]         │
│                                                      │
│  Position                                            │
│  ┌───┬───┬───┐   Or: X [0.85] Y [0.05]              │
│  │ ○ │ ○ │ ● │                                      │
│  ├───┼───┼───┤                                       │
│  │ ○ │ ○ │ ○ │                                       │
│  ├───┼───┼───┤                                       │
│  │ ○ │ ○ │ ○ │                                       │
│  └───┴───┴───┘                                       │
│                                                      │
│  Size        W [auto___]  H [auto___]                │
│  Opacity     [──────●──────────] 100%                │
│                                                      │
│  ──────────────────────────────────────────────────── │
│  [ Delete ]         [ Cancel ] [ Save Changes ]      │
└──────────────────────────────────────────────────────┘
```

Schedule tab:
```
│  (Schedule tab)                                      │
│                                                      │
│  Schedule Type                                       │
│  ○ Always On                                         │
│  ○ Time Window                                       │
│  ● Rotation Group                                    │
│                                                      │
│  Rotation Group: [Spring Sponsors_____________]      │
│  Interval: [──●────────] 45 seconds                 │
│                                                      │
│  Assets in this group:                               │
│  ┌───────────────────────────────────────────┐       │
│  │ ■ ABC Hardware Logo              [Remove] │       │
│  │ ■ Bay View Marina               [Remove]  │       │
│  │ ■ Sunrise Coffee                [Remove]  │       │
│  │ [+ Add asset to group]                    │       │
│  └───────────────────────────────────────────┘       │
│                                                      │
│  Active Hours (optional)                             │
│  ○ All day                                           │
│  ● Custom: 08:00 AM to 08:00 PM                     │
│                                                      │
│  Days of week:                                       │
│  [M] [T] [W] [T] [F] [S] [S]  (Mon-Fri filled)     │
│                                                      │
│  Schedule Preview:                                   │
│  [Weekly calendar grid showing shaded hours]         │
```

History tab:
```
│  (History tab)                                       │
│                                                      │
│  Version 5 (current)                                 │
│  2026-03-15 at 2:34 PM - nick                        │
│  "Updated logo file"                                 │
│  [thumbnail]                          [Current]      │
│  ─────────────────────────────────────               │
│  Version 4                                           │
│  2026-03-10 at 10:15 AM - nick                       │
│  "Adjusted position"                                 │
│  [thumbnail]          [Preview] [Revert to v4]      │
│  ─────────────────────────────────────               │
│  Version 3                                           │
│  ...                                                 │
```

### 5.5 Screen: Asset Studio - Analytics Tab

**Purpose:** Display time and impression tracking for assets, primarily for stream operators selling ad spots.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  Asset Studio                                                                    │
│  [ My Assets ] [ Template Catalog ] [ Canvas Editor ] [ Analytics ]  ← active  │
│                                                                                  │
│  Date Range: [Last 7 days ▾]  [Mar 8 - Mar 15, 2026]          [Export CSV]     │
│                                                                                  │
│  Summary Cards:                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Total        │  │ Total        │  │ Most Shown   │  │ Least Shown  │        │
│  │ Display Time │  │ Impressions  │  │ Asset        │  │ Asset        │        │
│  │  14h 32m    │  │    847       │  │ ABC Hardware │  │ Tide Chart   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                                  │
│  Per-Asset Table:                                                                │
│  ┌──────────────────────────────────────────────────────────────────────┐       │
│  │ Asset Name          │ Type     │ Display Time │ Impressions │ Last On │       │
│  │─────────────────────┼──────────┼──────────────┼─────────────┼────────│       │
│  │ ABC Hardware Logo   │ Static   │ 4h 12m       │ 280         │ Today  │       │
│  │ Bay View Marina     │ Static   │ 3h 58m       │ 265         │ Today  │       │
│  │ Current Conditions  │ Template │ 14h 32m      │ 1 (always)  │ Now    │       │
│  │ Tide Chart          │ API      │ 2h 05m       │ 140         │ Mar 12 │       │
│  └──────────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

Summary cards: Four small stat cards in a row at the top. Same style as existing dashboard stat cards (`bg-dark-800`, `border border-dark-700`, white stat value, gray label).

Per-asset table: Sortable columns (click header to sort). Each row links to that asset's detail slide-over. "Last On" column shows relative time ("Now", "Today", "Mar 12") for quick scanning.

Date range selector: Dropdown with presets (Today, Last 7 days, Last 30 days, Custom range). Custom range opens a date picker.

Export CSV: Downloads a CSV file with the full analytics table for the selected date range.

---

## 6. Component Library Additions

### 6.1 Position Picker (9-Grid)

Used in: Template configuration wizard, Asset detail (Settings tab), any form where overlay screen position is set.

Replaces: Raw X/Y numeric inputs (0.0-1.0) for non-technical users.

```
┌───┬───┬───┐
│ ○ │ ○ │ ● │   Positions map to semantic labels:
├───┼───┼───┤   TL | TC | TR
│ ○ │ ○ │ ○ │   ML | MC | MR
├───┼───┼───┤   BL | BC | BR
│ ○ │ ○ │ ○ │
└───┴───┴───┘   Selected cell fills with primary-600.
```

Advanced mode: A toggle below the grid ("Advanced: set exact position") reveals the raw X/Y float inputs for power users who need sub-position accuracy. Both modes stay in sync (selecting a grid cell updates the floats; typing a float updates the grid to the nearest cell).

### 6.2 "Coming Soon" Badge / Template Card State

Used in: Template Catalog cards for unreleased templates (Social Media feeds).

- Template card maintains its normal structure
- A dark semi-transparent overlay (`bg-black/50`) covers the thumbnail
- Centered lock icon (HeroIcons `LockClosedIcon`) + "Coming Soon" text on the overlay
- Category chip on the catalog filter bar shows the same lock icon
- The card body text is rendered at reduced opacity (60%)
- "Use Template" button is replaced by "Notify Me" (outline style, gray)
- "Notify Me" opens a simple modal: "We'll let you know when [Social Media Feed] templates are available." + Confirm button

### 6.3 Connection Test Button

Used in: Template configuration wizard (API-backed templates like weather, tide), Data Binding editor.

States and appearance:
```
Default:   [ Test Connection ]   Gray outline button
Loading:   [ ◌ Testing...   ]   Spinner + gray outline
Success:   [ ✓ Connected    ]   Green fill, white text
           Station: Smith Beach (ID: 12345) - below button, small gray text
Error:     [ ✗ Failed       ]   Red fill, white text
           "Could not reach weather API. Check your station ID." - below, red text
```

### 6.4 Scheduling Weekly Calendar Preview

Used in: Asset detail > Schedule tab (when Time Window or Rotation Group schedule type is selected).

A 7-column (days of week), 24-row (hours) mini grid. Active hours filled with `primary-600/40` color. Inactive hours are `dark-700`. Labels: Mon/Tue/Wed/Thu/Fri/Sat/Sun across the top, hour labels (12am, 6am, 12pm, 6pm) on the left side.

```
     M    T    W    T    F    S    S
12a  ░    ░    ░    ░    ░    ░    ░
3a   ░    ░    ░    ░    ░    ░    ░
6a   ░    ░    ░    ░    ░    ░    ░
8a   ████ ████ ████ ████ ████ ░    ░   (active Mon-Fri 8a-8p)
12p  ████ ████ ████ ████ ████ ░    ░
6p   ████ ████ ████ ████ ████ ░    ░
8p   ░    ░    ░    ░    ░    ░    ░
```

Clicking a cell toggles that hour on/off (not required for MVP; treat as read-only preview in Phase 1). Hovering a filled cell shows a tooltip: "Mon 8:00 AM - 8:00 PM".

### 6.5 Version History Timeline (within slide-over)

Each version entry:
- Thumbnail (small, 80x45px, aspect 16:9, rounded corners)
- Version badge (v5, v4...) in small monospace chip
- Timestamp + user (gray subtext)
- Change description (italic, gray)
- "Current" badge (if this is the active version, no revert button)
- "Preview" link (opens full-size thumbnail in a lightbox)
- "Revert to vN" button (red outline, confirms before acting)

Divider between entries. The list is scrollable within the slide-over. Shows most recent at top.

### 6.6 Auto-Save Indicator

Used in: Canvas Editor header area.

```
[Saving... ◌]     (during save)
[Saved ✓       ]  (after successful save, gray text)
[● Unsaved     ]  (dirty state, orange dot)
[Auto-saved 2m ago]  (after auto-save, gray text)
```

The indicator is positioned in the canvas editor header between the project name and the Export/Save buttons. It is informational only; clicking it has no effect. If auto-save fails, it shows "Auto-save failed - click Save" in orange with a Save button link.

---

## 7. Interaction Design

### 7.1 Template Configuration Wizard Interactions

**Slide-over open:** Right-side panel slides in from off-screen over 250ms (`ease-out`). The main catalog content remains visible and slightly dimmed behind the slide-over. A backdrop overlay (`bg-black/30`) covers the main content.

**Slide-over close:** Reverse animation over 200ms. If the user has filled in any fields, a brief confirmation prevents accidental dismissal: "Discard configuration changes?" with Discard / Keep Editing options.

**Live preview update:** When any configuration field changes, the preview thumbnail at the top of the slide-over updates with a 300ms debounce. While updating, a subtle shimmer effect replaces the thumbnail. For API-backed templates, the preview only updates after a successful "Test Connection".

**Field validation:** Real-time inline validation on blur. Error messages appear as small red text below the field with a red border on the input. The "Create Asset" button is disabled (opacity 50%, not-allowed cursor) until all required fields are valid.

### 7.2 Canvas Editor Interactions

**Object selection:** Click to select (blue handles appear). Click-drag on empty canvas to box-select multiple. Cmd/Ctrl+A to select all.

**Resize handles:** 8-point handles (corners + midpoints) around selected objects. Dragging a corner scales proportionally by default; hold Shift to scale non-proportionally. Midpoint handles scale in one axis only.

**Text editing:** Double-click a text layer on canvas or in the layer panel to enter inline edit mode. Cursor appears within the text. Escape or click outside to exit edit mode.

**Drag from layer panel to canvas:** Not applicable (layers represent objects already on canvas, not a palette).

**Image import:** Drag image file from OS onto canvas area. Drop target indicator (blue border around canvas) shows the canvas will receive the image. File validation occurs immediately on drop (type, size). Invalid files show an error toast.

**From existing asset library:** "Import from Assets" button in the toolbar opens a modal grid of the user's existing assets. User can search and click to import. The image is added to the canvas as a new layer.

**Undo/redo:** Cmd/Ctrl+Z / Cmd/Ctrl+Shift+Z. Up to 50 history states. Undo button in toolbar shows a tooltip with the operation that will be undone ("Undo: Move ABC Logo").

**Keyboard shortcuts (canvas editor):**

| Key | Action |
|-----|--------|
| V | Select tool |
| R | Rectangle tool |
| T | Text tool |
| E | Ellipse tool |
| L | Line tool |
| I | Image import |
| Cmd/Ctrl+Z | Undo |
| Cmd/Ctrl+Shift+Z | Redo |
| Cmd/Ctrl+S | Save project |
| Cmd/Ctrl+E | Export |
| Delete / Backspace | Delete selected layer |
| Arrow keys | Nudge selected object 1px |
| Shift+Arrow keys | Nudge selected object 10px |
| Cmd/Ctrl+G | Group selected objects |
| Cmd/Ctrl+Shift+G | Ungroup |
| Cmd/Ctrl+D | Duplicate selected |
| Cmd/Ctrl+A | Select all |
| Cmd/Ctrl+R | Toggle rulers |
| [ | Bring selection backward one layer |
| ] | Send selection forward one layer |
| Cmd/Ctrl+[ | Send selection to back |
| Cmd/Ctrl+] | Bring selection to front |
| Escape | Deselect / Exit text edit mode |

**Alignment guides (smart guides):** Appear as thin `primary-400` lines when a dragged object's edges or center align with another object's edges or center, or with the canvas center/edges. Guides appear on drag and disappear on release.

**Snap to grid:** When enabled, objects snap to the nearest grid intersection. Grid lines are drawn on the canvas in a low-contrast color (visible but not distracting). Grid size defaults to 16px; configurable in View settings.

### 7.3 Asset Grid Interactions

**Card hover:** Card border brightens from `border-dark-700` to `border-dark-600`. Action buttons in the card footer become visible (they are subtly hidden at lower opacity when not hovered, to keep the grid clean).

**Card click (not on action button):** Opens the asset detail slide-over.

**"..." overflow menu:** Opens a small floating menu above/below the button. Options: Duplicate, Test Connection (API types only), Export, Delete.

**Delete confirmation:** Not a browser `confirm()`. Instead, a small inline confirmation appears within the overflow menu: "Delete this asset? [Cancel] [Delete]". Red text for the delete option.

**Search:** Typing in the search input filters the grid in real time with a 200ms debounce. No submit required. A clear (X) button appears when the search has content.

**Category chip filter:** Click to select/deselect. Multiple chips can be active simultaneously (OR logic: show assets matching any selected category). All chip deselects everything and shows everything.

---

## 8. Responsive Design

### 8.1 Breakpoints

The existing VistterStream frontend uses Tailwind defaults:

| Name | Width | Asset Studio Behavior |
|------|-------|----------------------|
| Mobile | < 640px | Tab bar becomes scrollable; asset grid is 1 column; canvas editor shows a "Desktop recommended" prompt but remains functional at reduced size |
| Tablet (md) | 640-1024px | 2-column asset grid; template catalog 2 columns; slide-overs full-width |
| Desktop (lg) | 1024-1280px | 3-column grids; slide-overs 480-520px; canvas editor panels collapse to icons only |
| Wide (xl) | > 1280px | 4-column grids; canvas editor panels at full width |

### 8.2 Canvas Editor Responsive Behavior

The canvas editor is explicitly a desktop-focused tool. On viewports narrower than 1024px:
- A persistent banner appears at the top of the canvas editor: "The canvas editor works best on a larger screen. Some panels may be hidden."
- The layer panel collapses to a toggle-able drawer (icon button to show/hide)
- The properties panel collapses to a toggle-able drawer
- The canvas area fills the available space
- All functionality remains accessible via drawers and toolbar

On mobile (< 640px):
- The canvas editor is accessible but shows a stronger recommendation: "For the best experience, open the canvas editor on a desktop or laptop."
- A "Continue anyway" link allows proceeding

### 8.3 Template Catalog Responsive Behavior

- Mobile: 1 column grid; category chips are horizontally scrollable
- Tablet: 2 column grid
- Desktop: 3 column grid
- Template detail slide-over becomes full-width on mobile (covers the catalog completely, close button prominent at top)

---

## 9. Accessibility Specifications

### 9.1 WCAG Compliance Target

**Level: AA** (consistent with existing VistterStream UI commitment)

### 9.2 Color and Contrast

The dark theme requires careful contrast checking:
- White text (`#FFFFFF`) on `dark-800` (`approx #1F2937`): Ratio ~12:1 (exceeds AA)
- `gray-400` (`approx #9CA3AF`) on `dark-800`: Ratio ~4.7:1 (passes AA for normal text)
- `primary-600` (`approx #2563EB`) as button background with white text: ~4.5:1 (passes AA)
- Error states use `red-400` (`#F87171`) on `dark-800`: ~5.4:1 (passes AA)
- "Coming Soon" overlaid cards: The overlay must not cause the lock icon or "Coming Soon" text to fail contrast against the dark overlay background

### 9.3 Keyboard Navigation

**Template Catalog:**
- Category chips: Arrow keys to navigate between chips; Space/Enter to toggle
- Template cards: Tab to navigate between cards; Enter to open the configuration slide-over
- Slide-over: Focus is trapped within the slide-over when open; Tab navigates form fields; Escape closes the slide-over and returns focus to the triggering card

**Canvas Editor:**
- All toolbar tools are reachable via Tab; Enter/Space activates the tool
- Layer panel rows are focusable; Enter selects the layer; Delete key removes it
- The canvas itself receives focus (via Tab); once focused, arrow keys nudge selected objects; all keyboard shortcuts documented in Section 7.2 are active
- Properties panel inputs are reachable via Tab

**Asset Grid:**
- Cards are focusable (Tab); Enter opens detail slide-over; Escape closes it
- Action buttons within cards have proper focus indicators
- Search input is the first focusable element on the page

### 9.4 Screen Reader Support

- Template cards have `aria-label` including template name, category, and whether it is available or coming soon
- "Coming Soon" state is conveyed via `aria-disabled` and a visually-hidden explanation, not just the visual lock icon
- Slide-overs use `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` pointing to the slide-over title
- The 9-grid position picker uses `role="radiogroup"` with `role="radio"` for each cell; labels include the semantic position name ("Top Right")
- Canvas editor layer panel uses `role="list"` and `role="listitem"` for layers; drag-and-drop reordering announces changes to screen readers ("ABC Logo moved to position 2")
- Connection test button announces result: "Test Connection: Connected to station Smith Beach" or "Test Connection: Failed - could not reach API"
- Auto-save indicator uses `aria-live="polite"` to announce state changes without interrupting user flow
- Version history revert confirmation uses `aria-live="assertive"` to announce the confirmation prompt

### 9.5 Focus Management

- Opening a slide-over moves focus to the close button (X) or the first interactive element within the slide-over
- Closing a slide-over returns focus to the element that triggered it
- Deleting an asset returns focus to the next card in the grid (or the "New Asset" button if the last card was deleted)
- Canvas editor: switching tools (toolbar clicks or keyboard shortcuts) announces the active tool to screen readers via an `aria-live` region ("Text tool selected")

---

## 10. Content Guidelines

### 10.1 Voice and Tone

VistterStream operators are running real broadcast infrastructure. The tone is:
- **Direct:** Tell users exactly what an action does. "Create Asset" not "Continue".
- **Technical but not jargon-heavy:** "API" is acceptable; "JSON endpoint" is not unless in an advanced section. "Station ID" is better than "Tempest Device ID parameter".
- **Confident:** The software knows what it's doing. Avoid hedging language ("This might update..."). Say "The overlay will update every 60 seconds."
- **Error messages are actionable:** Not "Error 500" but "Could not connect to the weather station. Check that your station ID is correct and the Tempest service is running."

### 10.2 Microcopy Standards

**Template category labels:**
- "Weather" not "Meteorological Overlays"
- "Sponsor / Ad" not "Advertising Templates"
- "Lower Thirds" (industry standard term; target users know it)

**Button labels:**
- "Use Template" (on catalog card) -- action-oriented
- "Create Asset" (at bottom of wizard) -- clear outcome
- "Open in Canvas Editor" (alternate wizard path) -- specific
- "Export and Save as Asset" (canvas export dialog) -- explains both outcomes
- "Test Connection" (API templates) -- describes what it does

**Empty states:**
| Location | Heading | Body | CTA |
|----------|---------|------|-----|
| My Assets (empty) | "No overlays yet" | "Add professional overlays to your stream in minutes." | "Browse Template Catalog" |
| Canvas Projects (empty) | "No canvas projects" | "Create custom graphics without leaving VistterStream." | "New Canvas Project" |
| Version History (single version) | "No version history yet" | "Versions are saved automatically each time you edit this asset." | (none) |
| Analytics (no data) | "No display data yet" | "Analytics appear after assets have been displayed on a live stream." | (none) |
| Template Catalog search (no results) | "No templates found" | "Try a different search term or browse by category." | "Clear search" |

**Confirmation prompts (slide-over inline, not browser dialogs):**
| Action | Prompt |
|--------|--------|
| Delete asset | "Delete [Asset Name]? This cannot be undone." [Cancel] [Delete Asset] |
| Revert to version | "Revert to version [N]? A new version [N+1] will be created with this content." [Cancel] [Revert] |
| Close wizard with data | "Discard your configuration? Your changes will be lost." [Keep Editing] [Discard] |

---

## 11. Navigation Integration Detail

### 11.1 Sidebar Change

Current sidebar navigation:
```
Dashboard
Timelines
ReelForge
Settings
```

Updated sidebar navigation:
```
Dashboard
Timelines
Asset Studio    [NEW - replaces nothing; this is where "Assets" currently lives as a tab under Timelines]
ReelForge
Settings
```

The existing Assets page is currently reached from within Timelines (as a section) and is not in the primary sidebar. The Asset Studio gets a dedicated sidebar entry, elevating asset management to a first-class section. Icon: Use `PhotoIcon` or `SquaresPlusIcon` from HeroIcons (distinct from `FilmIcon` for Timelines and `SparklesIcon` for ReelForge).

### 11.2 Routes

| Path | Component | Notes |
|------|-----------|-------|
| `/asset-studio` | AssetStudio (My Assets tab) | Default tab |
| `/asset-studio/catalog` | AssetStudio (Template Catalog tab) | Direct link to catalog |
| `/asset-studio/canvas` | CanvasEditor (new project dialog) | New project |
| `/asset-studio/canvas/:projectId` | CanvasEditor (project open) | Resume project |
| `/asset-studio/analytics` | AssetStudio (Analytics tab) | Direct link to analytics |

Tab navigation within Asset Studio uses URL-based tabs (not component state) so that browser back/forward work as expected and users can bookmark a specific tab.

### 11.3 Asset Studio Tab Bar

```
┌──────────────────────────────────────────────────────────────────────┐
│  My Assets   │  Template Catalog  │  Canvas Editor  │   Analytics   │
└──────────────────────────────────────────────────────────────────────┘
```

Active tab has a bottom border (`border-b-2 border-primary-600`) and white text. Inactive tabs are `text-gray-400` with `hover:text-white`. The tab bar is sticky below the top nav bar when the user scrolls down through a long asset grid.

"Canvas Editor" tab behavior: Since the canvas editor is a separate full-page route, clicking the tab navigates to `/asset-studio/canvas` (new project dialog if no project is active, or the most recently opened project if one exists in session). The tab shows an "open" indicator if a canvas project is currently open.

### 11.4 Existing Timeline Integration

The existing Timeline Editor already has an asset picker (when adding an overlay cue, users pick from the asset list). This picker is not changed in Phase 1. However, the picker can be enhanced in Phase 2 to show asset thumbnails and the new asset types (templates, groups) alongside the existing flat list.

Asset groups in a timeline: When a user adds an asset group to a timeline overlay track, the timeline creates one cue per member asset. This is handled server-side; the UX in the timeline editor shows the group name with an expand toggle to see individual member assets.

---

## 12. Template Catalog - Template Specifications

This section defines the visual layout and configuration fields for each template available at launch.

### 12.1 Template: Current Conditions (Weather)

**Preview:** Overlay in a rounded rectangle, dark background, showing a weather icon (sun/cloud), temperature in large font, wind speed and direction, and humidity. Positioned in a corner.

**Configuration fields:**
| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| Station ID | Text input | Yes | — | Numeric, validated against Tempest API |
| Position | 9-grid picker | No | Top Right | |
| Units | Toggle (F/C) | No | F | |
| Theme | Toggle (Light/Dark) | No | Dark | |
| Refresh interval | Slider (30s-300s) | No | 60s | |

**Live preview:** Updates after Test Connection succeeds. Shows real current data from the station.

**Data source:** Existing TempestWeather API at `http://host.docker.internal:8036`. The generated asset is an `api_image` type with the TempestWeather overlay endpoint URL and the configured refresh interval.

### 12.2 Template: 5-Day Forecast (Weather)

**Preview:** Wider overlay showing 5 days in a row (day name, icon, high/low temps, precipitation chance). Typically wider and positioned along the bottom of the frame.

**Configuration fields:** Same as Current Conditions with addition of:
| Field | Type | Required | Default |
|-------|------|----------|---------|
| Display mode | Radio (Compact / Expanded) | No | Compact |

### 12.3 Template: Time and Date Display

**Preview:** Clean text overlay showing time (large) and date (smaller below).

**Configuration fields:**
| Field | Type | Required | Default |
|-------|------|----------|---------|
| Timezone | Dropdown (IANA timezone list, searchable) | Yes | System timezone |
| Time format | Toggle (12h / 24h) | No | 12h |
| Show seconds | Checkbox | No | Off |
| Show date | Checkbox | No | On |
| Date format | Dropdown (MM/DD/YYYY, DD/MM/YYYY, Full date) | No | Full date (e.g., Saturday, March 15) |
| Font color | Color picker | No | White (#FFFFFF) |
| Background | Toggle + Color picker | No | Semi-transparent black |
| Position | 9-grid picker | No | Top Left |

**Data source:** Server system clock. Asset type is a new lightweight `data_bound` type or a simple server-rendered image.

### 12.4 Template: Sponsor / Ad Slot

**Preview:** A lower-third style overlay with a logo on the left, business name in large font, and tagline or contact info below.

**Configuration fields:**
| Field | Type | Required | Default |
|-------|------|----------|---------|
| Business name | Text input | Yes | — |
| Logo image | File upload | No | — |
| Tagline / contact | Text input | No | — |
| Background color | Color picker | No | Dark blue (#1A2B4C) |
| Background opacity | Slider | No | 85% |
| Position | 9-grid (bottom positions emphasized) | No | Bottom Left |

**Output:** When configured, this opens the Canvas Editor with a pre-populated lower-third template. The user can then customize further and export to create a `static_image` asset. This is the bridge between the template wizard and the canvas editor -- not all templates produce an `api_image` asset; some produce canvas project starting points.

### 12.5 Template: Lower Third

**Preview:** Classic broadcast lower third: colored bar across the bottom with name text and title text.

**Configuration fields:**
| Field | Type | Required | Default |
|-------|------|----------|---------|
| Primary text (name/title) | Text input | Yes | — |
| Secondary text (role/info) | Text input | No | — |
| Accent color | Color picker | No | primary-600 blue |
| Text color | Color picker | No | White |
| Style | Radio (Solid / Gradient / Transparent) | No | Solid |

**Output:** Opens Canvas Editor with pre-populated lower third template. User can customize and export.

### 12.6 Template: Social Media Feed (Coming Soon)

**Status:** Visible in catalog with "Coming Soon" state. Configuration wizard is not available.

**Planned platforms:** Twitter/X, Instagram, YouTube live chat.

**Coming Soon copy:** "Social media feed templates are coming in a future update. We'll display real-time posts and comments from your channel directly on your stream."

---

## 13. Open Questions and Future Considerations

### Open Questions

- [ ] Should the Canvas Editor "New Project" dialog offer a library of pre-built canvas templates (e.g., a lower-third template, an ad slot template) as starting points, in addition to starting from blank? This would accelerate Jordan's workflow significantly.
- [ ] For the template configuration wizard, should "Position" default to the PRD's normalized 0.0-1.0 coordinates for the 9-grid intermediate positions, or should we use only the 9 cardinal positions and add a separate "Fine-tune position" section?
- [ ] The PRD specifies that the Sponsor/Ad template and Lower Third template open the Canvas Editor rather than generating an asset directly. Should this be communicated to users before they click "Use Template" to set expectations? (e.g., "This template opens the canvas editor to customize your design")
- [ ] Version history auto-purges at 50 versions per asset. Should the UI warn users when they are approaching this limit (e.g., at 45 versions), or silently purge?
- [ ] The analytics tab is primarily useful for operators selling ad spots. For operators who are not selling ads, this tab adds navigation noise. Should it be hidden by default and enabled via Settings?

### Future Considerations (Phase 2 UX)

- **Animation configurator:** When animations are added post-MVP, the asset detail slide-over gets an "Animations" tab alongside Settings, Schedule, and History. Entrance/exit animations use a visual timeline UI similar to what is used in ReelForge.
- **Data Binding UI:** A "Live Data" tab in the asset detail slide-over for `data_bound` assets, with a JSON path builder that lets users test bindings against live API responses without writing JSONPath syntax manually.
- **Canvas template library:** Pre-built canvas project templates as starting points ("Lower Third Standard", "Ad Slot Full Width", "Score Bug", etc.) selectable in the new project dialog.
- **Batch operations:** Checkbox multi-select on the asset grid to apply Schedule, Export, or Delete to multiple assets at once.
- **Asset search / tagging:** Full-text search is in scope for Phase 1, but tagging (user-defined tags on assets) is deferred. Tags would appear as badges on cards and as filter chips.
- **Live preview in timeline:** When an asset is added to a timeline overlay cue, a small preview of the asset is shown in the overlay preview panel (existing `OverlayPreviewPanel` component). Phase 2 enhances this to update in real time when the asset schedule is modified.
- **Multi-user indicators:** When role-based permissions are added, asset cards that are locked by another user show a "Locked by Jordan" badge with an avatar/initial chip.

---

## 14. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-03-15 | Nick DeMarco (with AI Assistance) | Initial draft |
