# PTZ on Raspberry Pi Docker

This guide captures the steps used to diagnose and stabilize Sunba PTZ presets when the backend runs inside Docker on Raspberry Pi.

## Quick Summary
- Set `ONVIF_DEVICE_URL` (and optional `ONVIF_PTZ_URL`) so the backend talks to the camera directly without WS-Discovery.
- Enable `PTZ_DEBUG=1` to log device/ptz endpoints, profile tokens, and preset tokens during preset moves.
- Use the new `pi-host` Docker Compose profile when multicast/UDP is required or discovery must be re-enabled.
- Capture artifacts under `diagnostics/` to compare Mac vs Pi behaviour and retain reproducibility.
- Preset capture now stores raw pan/tilt/zoom, exposes live status, and reuses them for AbsoluteMove before every GotoPreset/SetPreset.

## Prerequisites
1. Copy `.env.example` to `.env` and adjust values:
   ```env
   PTZ_DEBUG=1
   ONVIF_DEVICE_URL=http://192.168.12.59:8899/onvif/device_service
   ONVIF_PTZ_URL=http://192.168.12.59:8899/onvif/ptz   # optional, leave blank if not needed
   ```
2. Regenerate the backend image if dependencies changed:
   ```bash
   docker compose -f docker/docker-compose.rpi.yml build backend
   ```
3. Collect environment snapshots before and after changes:
   ```bash
   python3 scripts/collect_env.py --output diagnostics/env-pi.json
   # repeat on Mac workstation -> diagnostics/env-mac.json
   ```

## Option A – Bridge Network with Explicit URL (recommended)
1. Ensure the camera IP is routable from the Pi host (ping from host OS).
2. Configure the backend container:
   ```bash
   PTZ_DEBUG=1 ONVIF_DEVICE_URL=http://192.168.12.59:8899/onvif/device_service \
     docker compose -f docker/docker-compose.rpi.yml up -d backend
   ```
3. Exec into the container to validate connectivity:
   ```bash
   docker compose -f docker/docker-compose.rpi.yml exec backend \
     ping -c1 192.168.12.59
   docker compose -f docker/docker-compose.rpi.yml exec backend \
     curl -sw '\nHTTP %{http_code}\n' http://192.168.12.59:8899/onvif/device_service -o /dev/null
   ```
4. Trigger preset calls via API or Timeline executor. Logs (with `PTZ_DEBUG=1`) will show:
   - Resolved ONVIF host/port
   - Service XAddrs (device/media/ptz)
   - Media profile tokens and preset tokens
5. Save the run log:
   ```bash
   docker compose -f docker/docker-compose.rpi.yml logs backend --since=15m \
     > diagnostics/pi-ptz-run.log
   ```
6. Repeat on Mac (native run) and diff:
   ```bash
   uvicorn backend.main:app --port 8000 2>&1 | tee diagnostics/mac-ptz-run.log
   diff -u diagnostics/mac-ptz-run.log diagnostics/pi-ptz-run.log | less
   ```

## Updated Preset Workflow
1. **Capture:** Use the Preset Management UI (or `POST /api/presets/capture`) to save a position. The capture modal now streams live `GetStatus` telemetry; once the camera reports coordinates the UI immediately opens an edit dialog pre-filled with those values so you can fine-tune before leaving. Backend logs appear as `📸`/`📍` lines in `diagnostics/pi-ptz-run.log`.
2. **Edit:** Adjust pan/tilt/zoom numerically in the UI or send `PATCH /api/presets/{id}` with `{"pan": ..., "tilt": ..., "zoom": ...}`. The backend issues an `AbsoluteMove` followed by `SetPreset`, updating both the database and camera token.
3. **Recall:** Calling `POST /api/presets/{id}/move` triggers `AbsoluteMove` before `GotoPreset`, so the stored coordinates drive the motion even after a backend restart.
4. **Check status:** Query `GET /api/presets/cameras/{camera_id}/status` to poll live PTZ position (the UI poll interval is 2s). Logs mark these reads with `📊` entries.

## Option B – Host Network Profile (for discovery / multicast)
If the camera requires WS-Discovery or multicast traffic, use the optional profile introduced in `docker/docker-compose.rpi.yml`:
```bash
PTZ_DEBUG=1 docker compose -f docker/docker-compose.rpi.yml --profile pi-host \
  up -d backend-host rtmp-relay preview-server frontend
```
Key notes:
- `backend-host` binds directly to the Pi network stack. RTMP relay is still accessible via `127.0.0.1`.
- Exposed ports (`8000`) now belong to the host; remove conflicting services before enabling this profile.
- Stop the default `backend` service to avoid double allocation: `docker compose -f docker/docker-compose.rpi.yml stop backend`.

## Diagnostics Checklist
1. **Environment** – `diagnostics/env-*.json`
2. **Docker config** – generated via:
   ```bash
   docker compose -f docker/docker-compose.rpi.yml config \
     > diagnostics/docker/compose-rpi-config.yml
   docker compose -f docker/docker-compose.rpi.yml --profile pi-host config \
     > diagnostics/docker/compose-rpi-pi-host-config.yml
   ```
3. **Container Inspect** – after services are up:
   ```bash
   docker inspect vistterstream-backend > diagnostics/docker/inspect-backend.txt
   docker inspect vistterstream-backend-host > diagnostics/docker/inspect-backend-host.txt
   ```
4. **SOAP sanity checks** – templates live under `diagnostics/soap/`. Example (Digest auth shown, adjust as needed):
   ```bash
curl --anyauth -u admin:SECRET \
   -H 'Content-Type: application/soap+xml; charset=utf-8' \
   --data @diagnostics/soap/GetCapabilities.xml \
   http://192.168.12.59:8899/onvif/device_service
```
> Tip: `curl --digest` on the Pi was observed to replay the POST without a body (Content-Length: 0) before authentication, leading to `Empty reply from server`. Using `--anyauth` forces curl to complete the Digest handshake and send the SOAP body correctly.
5. **Diff Mac vs Pi logs** – check for mismatched base URLs, profile counts, HTTP errors, or timeout differences.

## Troubleshooting Notes
- `host.docker.internal` and `localhost` do **not** work inside Linux containers. Use the camera's LAN IP or set `ONVIF_DEVICE_URL`.
- If `PTZ_DEBUG` shows retries on ports 80/8000/8899, ensure the camera actually listens on those ports; override with the exact port if different.
- Clock skew can break Digest auth. Sync Pi time via `sudo timedatectl set-ntp true`.
- When discovery is required, confirm UDP 3702 reachability (`sudo tcpdump -ni any udp port 3702`). Host networking bypasses Docker's multicast limitations.
- After camera preset changes, recycle the container or call `/api/presets/{id}/move` once to refresh cached xaddrs.
- The backend seeds `camera_preset_token` with the preset ID when capturing a new preset. This supports cameras (like Sunba) that do not return a token from `SetPreset`.

## Related Assets
- `diagnostics/ptz-callgraph.md` – end-to-end PTZ request flow.
- `tests/test_ptz_service_overrides.py` – regression test covering explicit URL overrides.
- `diagnostics/soap/*.xml` – ready-made SOAP bodies for direct PTZ calls.
