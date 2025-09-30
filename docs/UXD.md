# VistterStream User Experience & Interaction Design

## 1. Design Principles
* **Operational Clarity:** Every view surfaces system status, active streams, and recent alerts without hunting.
* **Guided Configuration:** Wizards and contextual tips help non-technical operators onboard cameras and presets confidently.
* **Resilient Feedback:** Real-time validations, optimistic UI states with rollback, and persistent toasts keep users informed during timeline execution.
* **Responsive Reliability:** Layout adapts gracefully to tablets and smaller laptops used in control rooms or on-site kiosks.

## 2. Information Architecture
* **Authentication Layer:** Login, password reset, first-time setup wizard.
* **Primary Navigation:** Dashboard, Cameras, Presets, Timelines, Segments, Streams, Overlays, System (Settings, Logs, Updates).
* **Secondary Navigation:** Within each section provide tabs (Details, Activity, Diagnostics) to reduce clutter.
* **Global Elements:** Persistent top bar with health summary, alerts bell, and quick actions (Start Stream, Generate Diagnostics).

## 3. Key User Journeys
### 3.1 First-Time Setup
1. User lands on welcome screen, reads hardware setup checklist.
2. Guided wizard collects locale/timezone, admin credentials, network preferences.
3. Final screen summarizes configuration and links to camera onboarding.

### 3.2 Camera Onboarding & Validation
1. Operator opens Cameras → "Add Camera" modal.
2. Form collects camera name, type (stationary/PTZ), protocol, network details, credentials.
3. Inline validation verifies credentials; preview pane streams sample footage.
4. Success state stores camera and suggests adding PTZ presets if applicable.

### 3.3 Timeline Monitoring
1. Remote producer or operator opens Timelines view.
2. See table of scheduled/active timelines with status chips (Scheduled, Running, Warning, Failed).
3. Selecting a timeline opens detail drawer showing shot sequence, current step, and upcoming overlays.
4. Operator can pause/resume timeline or trigger manual override (switch to fallback shot).

### 3.4 Overlay Orchestration Monitoring
1. Producer opens Timelines → selects active show with overlays.
2. Overlay panel shows current scene, next cue countdown, and layer stack preview.
3. Producer can trigger manual overrides (pause overlays, force fallback slate) with confirmation dialog.
4. Cue history lists executed overlays with timestamps for advertiser verification.

### 3.5 Incident Response
1. Alert badge indicates new issue; clicking opens Alerts center.
2. Alert detail page shows severity, affected resource, recommended action, quick links (restart stream, view logs).
3. Resolution actions change alert state to Resolved with audit trail entry.

### 3.6 Manual Segment Playback
1. Operator opens Segments view to browse synced and offline packages.
2. Selecting a segment opens detail drawer with timeline steps, required cameras, overlays, and duration.
3. Operator previews segment playback (picture-in-picture) and queues it to "Next" or triggers immediate play.
4. Confirmation modal summarizes outputs affected and requests optional note for audit trail.
5. Upon completion, success banner offers quick link to review execution logs or replay.

## 4. Screen Specifications
| Screen | Layout Details | Key Components |
| --- | --- | --- |
| **Login & Setup** | Centered card, dual-column on desktop (login + help panel). Setup wizard uses progress indicator. | Form fields, password strength meter, hardware checklist accordion. |
| **Dashboard** | Responsive grid: top bar metrics, camera preview tiles, alerts list sidebar. | Metric cards, camera cards (thumbnail, status, actions), alert feed, quick action buttons. |
| **Cameras** | Table view with filters + inline preview; drawer for camera detail editing. | Data table, filter chips, RTSP test button, connection history timeline. |
| **Presets** | Split view: left list of presets, right live preview with PTZ controls. | PTZ joystick controls, slider inputs, save/cancel actions, preset tagging. |
| **Timelines** | Calendar/list toggle, detail drawer showing step sequence. | Timeline progress indicator, overlay thumbnails, override controls, overlay cue timeline scrubber. |
| **Segments** | Library list with sync status and source (cloud/export). Detail drawer highlights dependencies and offers preview controls. | Segment cards with status badges (Ready, Needs Validation), import/upload button, queue/Play Now actions, execution log panel. |
| **Streams** | Card layout per destination with status, bitrate graphs, history log. | Start/stop toggle, bitrate sparkline, error log accordion, key management modal. |
| **Overlays** | Dual-pane view: asset gallery with manifest metadata alongside OCL script preview. | Thumbnail grid, sync status badges, version comparison modal, cue inspector (start time, duration, transition, opacity curve). |
| **System Settings** | Tabbed interface (General, Network, Updates, Diagnostics). | Form sections, backup/export buttons, OTA update progress widget. |

## 5. Interaction Patterns & States
* **Modals** for add/edit actions with autosave drafts when closed unexpectedly.
* **Drawers** for quick inspection without navigating away (camera details, timeline steps, overlay cue inspector).
* **Segment Queue Controls** allow drag-and-drop ordering of upcoming manual segments with clear execution targets (Program, Preview).
* **Toast Notifications** with severity color-coding; persistent banner for critical incidents until acknowledged.
* **Empty States** providing call-to-action (e.g., "No cameras yet—add your first camera").
* **Loading Skeletons** for previews while streams initialize and overlays render in preview canvas.
* **Error Handling** includes inline hints, retry buttons, OCL validation error summaries with line references, and ability to download diagnostics from failure dialogs.

## 6. Visual Language
* **Color Palette:**
  * Midnight Gray (#1C1F2B) background, Deep Navy (#121521) panels.
  * Primary Accent Azure (#1E90FF) for main actions.
  * Success Green (#24D17B), Warning Amber (#FFC857), Error Crimson (#FF4D6D).
  * Neutral grays for text (#F4F6FB for headings, #B5BED6 for body).
* **Typography:** Inter as primary font with weights 400/500/600; monospaced font (JetBrains Mono) for logs.
* **Iconography:** Feather or Heroicons for consistency; ensure tooltips and labels for accessibility.
* **Card Design:** Rounded 8px corners, subtle elevation, status badge in top-right corner.

## 7. Responsive Behavior
* **Desktop (>1200px):** Three-column dashboard (metrics, cameras grid, alerts).
* **Tablet (768–1199px):** Navigation collapses to icon rail; camera previews switch to two-column.
* **Mobile (<768px):** Top nav converts to hamburger menu; key actions move to sticky footer for reachability; streaming previews optional due to bandwidth.

## 8. Accessibility & Compliance
* Meet WCAG 2.1 AA contrast ratios for text and interactive components.
* Support full keyboard navigation and focus outlines, including PTZ controls via arrow keys.
* Provide descriptive alt text for camera previews (camera name + status) and overlays.
* Offer text-to-speech friendly alerts and ARIA live regions for real-time status updates.

## 9. Content Strategy
* Use plain language labels ("Start Stream" instead of "Initiate Transmission").
* Include inline help icons linking to docs or tooltips for technical terms (RTSP, bitrate).
* Provide contextual success/error messaging with next-best actions ("Stream key invalid—update credentials") and segment-specific guidance ("Segment assets missing—revalidate or load from USB").
* Logs and diagnostics formatted with timestamps, severity labels, and action tags.

## 10. Future UX Enhancements
* Multi-appliance switcher within UI for fleet management.
* Embedded tutorial mode overlay guiding new operators.
* Dark/light theme toggle for varying control room environments.
* Mobile push notifications via PWA integration for alerting on the go.

## 11. Experience Planning & Traceability
### 11.1 Alignment with PRD & SAD
| UX Area | Supporting PRD Requirements | Supporting Architecture Elements | Notes |
| --- | --- | --- | --- |
| Setup Wizard & Auth | 6.1, 6.5 | Web/API Gateway, Persistence Layer | Validate copy and flow with first pilot customers behind firewalls. |
| Camera & PTZ Controls | 6.2 | Camera Manager APIs, PTZ latency metrics | Ensure joystick interactions remain keyboard accessible. |
| Timeline & Overlay Monitoring | 6.3, 6.7 | Control Service telemetry, Overlay Service cue reporting | Map overlay cue logs to advertiser reporting export. |
| Segments Library & Playback | 6.3, 6.6 | Segment metadata store, orchestration state machine | Define manual override permissions by role. |
| Alerts & Diagnostics | 6.6 | Metrics & Messaging, diagnostics bundle generator | Prototype alert resolution workflows with support team. |

### 11.2 UX Research & Content Backlog
1. Conduct contextual inquiry with two pilot venues to validate dashboard alert density and prioritization.
2. Usability-test PTZ preset creation flow on touch devices to ensure controls remain usable without hardware keyboards.
3. Draft microcopy guidelines for OCL validation errors so messaging is consistent across local UI and VistterStudio surfaces.
4. Define visual treatment for offline/online states throughout navigation, including timeline cards and segment rows.
5. Collaborate with engineering on telemetry dashboards that surface overlay cue drift in near real time.

### 11.3 Design Documentation To-Do
* Produce responsive layout specs for 768px breakpoint for Cameras, Timelines, and Segments views.
* Create component library starter in Figma with tokens for palette, typography, spacing, and elevation.
* Document animation principles (durations, easing) for overlay previews and timeline transitions.
* Establish accessibility acceptance checklist integrated into design review template.
