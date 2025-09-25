# VistterStream User Interface Design Document

## Layout Structure

* **Login Screen:** Simple form for username/password.
* **Main Dashboard:** Camera overview with previews, health indicators, and quick actions.
* **Navigation Sidebar:** Links for Dashboard, Cameras, Presets, Streams, Overlays, Settings.
* **Top Bar:** System status (CPU, memory, active streams), user menu (logout, change password).

## Core Components

1. **Login Page**

   * Input fields: username, password
   * Submit button → redirects to Dashboard
   * Minimal branding with VistterStream logo

2. **Dashboard**

   * **Camera Grid:** Tiles with live preview, camera name, status indicator (green/red).
   * **Quick Actions:** Start/stop stream, go to settings, view logs.
   * **System Metrics:** CPU, memory, network usage in top bar widget.

3. **Camera Management**

   * **Camera List View:** Table or cards with camera name, type (stationary/PTZ), protocol, health.
   * **Add Camera Form:** Fields for name, type, address, port, credentials.
   * **Connection Test Button:** Validate camera before saving.
   * **Edit/Delete Buttons** per camera.
   * **Preview Pane:** Inline stream preview.

4. **PTZ Preset Manager**

   * **Preset List:** Table with shot names (e.g., shot1, shot2).
   * **Add Preset Form:** Pan, tilt, zoom sliders/inputs.
   * **Live Preview Window:** Adjust PTZ and save as preset.
   * **Trigger Buttons:** Move camera to saved preset.

5. **Streams**

   * **Active Streams List:** Destination (YouTube, Facebook, Twitch), status, start time.
   * **Add Stream Destination Form:** Select platform, enter RTMP URL/stream key.
   * **Controls:** Start, stop, restart stream.

6. **Overlays**

   * **Overlay List:** Cached assets synced from VistterStudio.
   * **Preview Panel:** Small thumbnails for overlays.
   * **Sync Button:** Manual trigger to fetch latest overlays.

7. **Settings**

   * **User Management:** Change password.
   * **System Settings:** Cache size, auto-reconnect toggles.
   * **Authentication:** Local-only, reset password option.
   * **Logs:** Download/view system logs.

## Interaction Patterns

* **Dashboard-first workflow:** Always land on camera overview.
* **CRUD actions:** For cameras, presets, streams, overlays.
* **Modal Dialogs:** For add/edit forms (camera, stream, preset).
* **Live Previews:** Inline HLS/RTSP player in dashboard and camera detail.
* **Status Indicators:** Color-coded dots for health (green = online, red = offline).
* **Confirmation Dialogs:** For deletions or major changes.

## Visual Design Elements & Color Scheme

* **Color Palette:**

  * Dark background (#1E1E1E)
  * Accent blue (#007BFF) for primary actions
  * Green (#28A745) for healthy/online
  * Red (#DC3545) for error/offline
  * Neutral grays for secondary text/buttons
* **Branding:** VistterStream logo in sidebar and login screen.
* **Card Style:** Rounded corners, soft shadows.

## Mobile, Web App, Desktop Considerations

* **Responsive Web UI** (scales from desktop to tablet).
* **Mobile-Friendly:** Dashboard collapses to list view; navigation sidebar collapses to bottom nav.
* **Desktop Use:** Optimized for wide-screen monitoring, multiple camera previews side-by-side.

## Typography

* **Primary Font:** Inter (sans-serif, clean, modern).
* **Headings:** Bold, uppercase.
* **Body Text:** Medium weight, high contrast.
* **Status Indicators:** Paired with text labels for accessibility.

## Accessibility

* **Contrast Ratios:** All text/buttons meet WCAG AA.
* **Keyboard Navigation:** All forms and modals accessible with Tab/Enter.
* **ARIA Labels:** For camera previews, status indicators, and buttons.
* **Colorblind-Friendly:** Status icons paired with text labels (Online, Offline).

