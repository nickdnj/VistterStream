## Raspberry Pi (ARM64) Docker Setup

This runs the full stack on a Pi: backend API, RTMP relay (nginx-rtmp), and MediaMTX for preview.

### 1) Create a .env file (at repo root)

Copy the following into a new `.env` file:

```bash
DATABASE_URL=sqlite:////data/vistterstream.db
UPLOADS_DIR=/data/uploads
RTMP_RELAY_HOST=rtmp-relay
RTMP_RELAY_PORT=1935
```

Optional:
- If you want to change backend port: expose different host port in compose.

### 2) Start services on the Pi

```bash
cd docker
docker compose -f docker-compose.rpi.yml up --build -d
```

Services:
- Backend API: `http://<pi>:8000`
- RTMP Relay (cameras): `rtmp://<pi>:1935/live/<key>`
- MediaMTX (preview): `rtmp://<pi>:1936/` and HLS `http://<pi>:8888/`

Data persists in the `vistter_data` volume under `/data` inside the backend container (database + uploads).

### 3) Cross-build from a non-ARM machine (optional)

If building on x86 for ARM, enable buildx and QEMU:

```bash
docker run --privileged --rm tonistiigi/binfmt --install all
docker buildx create --use --name vistter-builder || true
docker buildx use vistter-builder

# Build and push to a registry (example)
docker buildx build \
  --platform linux/arm64 \
  -t <registry>/vistterstream-backend:arm64 \
  -f backend/Dockerfile backend \
  --push
```

Then update `docker-compose.rpi.yml` to use the pushed image instead of building locally.

### 4) Verify

```bash
docker compose -f docker-compose.rpi.yml ps
curl http://<pi>:8000/api/health
curl http://<pi>:9997/v1/config/get
```

### Notes

- The backend auto-detects hardware and selects encoders accordingly. On Pi 5, `h264_v4l2m2m` is used when available.
- `RTMP_RELAY_HOST` is set to the service name `rtmp-relay` for in-network routing between containers.
- If `/dev/video11` is present on the Pi, it is passed through to the backend container in compose for V4L2.



