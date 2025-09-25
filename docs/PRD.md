# Product Requirements Document (PRD): VistterStream Appliance

## 1. Elevator Pitch

VistterStream is the local streaming appliance that connects on-premises cameras to VistterStudio cloud timelines. Running on hardware like the Raspberry Pi in a Docker container, VistterStream discovers, manages, and processes local cameras, including PTZ (pan-tilt-zoom) presets. It ingests RTSP/RTMP feeds, applies overlays and instructions received from VistterStudio, and streams the final output to destinations such as YouTube Live, Facebook Live, or Twitch. With live previews, health monitoring, and FFmpeg-based processing, VistterStream turns commodity IP cameras into a reliable broadcast node.

## 2. Who is this app for

* **Small businesses & venues**: Shops, restaurants, marinas, and tourist attractions that want to broadcast local camera feeds with professional overlays.
* **Community organizations**: Visitor bureaus or chambers of commerce showcasing scenic views or events.
* **Property managers & real estate**: Broadcasting properties or scenic angles with dynamic overlays.
* **Event operators**: Local operators who need reliable camera-to-stream appliances without managing cloud infrastructure.

## 3. Functional Requirements

### Camera & PTZ Management

* **Camera Types:** Support for RTSP/RTMP cameras starting with Reolink (stationary) and Amcrest/Samba (PTZ).
* **Generic Camera Add:** Ability to add any RTSP/RTMP source via IP/port, credentials, and stream parameters.
* **PTZ Presets:** Users can define presets ("shots") for PTZ cameras (e.g., `camera1, shot1`, `camera1, shot2`).
* **Preset Execution:** VistterStream can move PTZ cameras to the correct preset when executing VistterStudio timelines.
* **Health Monitoring:** Real-time camera connection status, stream errors, and online/offline detection.

### Web Interface (Local Only)

* **Authentication:** Simple username/password login with ability to change credentials.
* **Add/Remove Cameras:** Web forms to configure IP address, port, credentials, stream path.
* **PTZ Configuration:** Interface to save and test PTZ preset positions.
* **Live Previews:** Embedded video preview for each camera feed.
* **Status Dashboard:** Camera health, system resource usage, and stream status.

### Streaming & Processing (FFmpeg)

* **Ingest:** Pull RTSP/RTMP feeds from configured cameras.
* **Overlay Pipeline:** Apply overlays and assets (ads, weather, promos) received from VistterStudio.
* **Transcoding:** Adjust resolution, codecs, and bitrates for compatibility with destinations.
* **Multi-Output:** Support streaming to multiple services simultaneously (YouTube Live, Facebook Live, Twitch).
* **Failover:** Replace failed feeds with placeholder or alternate camera.
* **Logging:** Maintain logs for stream errors, restarts, and system health.

### Storage & Config

* **Lightweight Database:** SQLite (or equivalent) to store camera configurations, PTZ presets, and credentials securely.
* **Cache:** Local caching of overlay assets, media, and fallback images.
* **Persistence:** Automatic restoration of configuration after reboot.

### Cloud Integration (VistterStudio)

* **Timeline Execution:** Receive instructions from VistterStudio to switch cameras and PTZ shots according to timelines.
* **Overlay Sync:** Download overlay assets and data (ads, weather, promos) from VistterStudio.
* **Execution Feedback:** Report status, errors, and health back to VistterStudio for monitoring.

## 4. User Stories

* **As a business owner,** I want to add my Reolink camera into VistterStream so that I can preview and broadcast it.
* **As a property manager,** I want to define PTZ presets so that I can show different angles of the same camera during a broadcast.
* **As a timeline editor in VistterStudio,** I want to reference `camera1, shot2` so that the correct PTZ position is shown in the livestream.
* **As a broadcast operator,** I want to monitor camera health so that I know if a feed goes down.
* **As a system admin,** I want simple local authentication so that only authorized people can configure cameras.
* **As a streamer,** I want the appliance to automatically push streams to YouTube Live so that I don’t have to manage FFmpeg manually.
* **As a location operator,** I want cached overlays to still display even if cloud connectivity is lost.

## 5. User Interface

* **Login Page:** Username/password authentication.
* **Dashboard:** Camera list with thumbnails, connection status, and live previews.
* **Add Camera Form:** Fields for camera name, type (stationary/PTZ), IP, port, credentials, stream path.
* **PTZ Preset Manager:** Interface to save and test presets, with labels like "shot1," "shot2."
* **Status Dashboard:** System health (CPU, memory), camera connectivity, active outputs.
* **Settings:** Manage authentication, storage usage, and streaming destinations.

## 6. Technical Notes

* **Deployment:** Docker container on Raspberry Pi or local Linux device.
* **Processing Engine:** FFmpeg for ingest, overlay composition, transcoding, and output.
* **Security:** Configurations stored securely, passwords encrypted, local-only access.
* **Extensibility:** Camera integration layer designed for additional vendors in future.
* **Resilience:** Auto-reconnect logic for unstable camera feeds.
* **Integration:** Tight coupling with VistterStudio timelines and overlays for synchronized storytelling.

