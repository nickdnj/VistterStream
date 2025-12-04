"""
VistterStream Backend API
Main FastAPI application for camera management and streaming control
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
from pathlib import Path

# Import routers
from routers import cameras, auth, streams, status, timelines, timeline_execution, emergency, destinations, assets, scheduler, watchdog, settings
from routers import presets as presets_router

# Import health monitor
from services.camera_health_monitor import start_health_monitor, stop_health_monitor
# Scheduler is optional in some builds; avoid crashing if missing
try:
    from services.scheduler_service import get_scheduler_service  # type: ignore
except Exception:  # noqa: E722
    get_scheduler_service = None  # type: ignore

# Import RTMP relay service (THE SECRET SAUCE!)
from services.rtmp_relay_service import get_rtmp_relay_service

# Import watchdog manager
from services.watchdog_manager import get_watchdog_manager
from models.database import get_db

# Create FastAPI app
app = FastAPI(
    title="VistterStream API",
    description="Local streaming appliance for camera management and live streaming",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend communication
# CORS configuration (configurable via env)
cors_origins_env = os.getenv("CORS_ALLOW_ORIGINS")
# Get Cloudflare Tunnel domain from env (if configured)
cloudflare_domain = os.getenv("CLOUDFLARE_TUNNEL_DOMAIN", "stream.vistter.com")
default_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
    "http://vistter.local:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://0.0.0.0:5173",
    f"https://{cloudflare_domain}",  # Cloudflare Tunnel domain
]
cors_origins = [o.strip() for o in (cors_origins_env or "").split(",") if o.strip()]
if not cors_origins:
    cors_origins = default_cors_origins

cors_origin_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX")
if not cors_origin_regex:
    # Allow any HTTP origin on the local network (IPv4) and mDNS hostnames by default so the
    # frontend served from the Pi (e.g. http://192.168.x.x:3000 or http://vistter.local:3000) can reach the
    # API without additional configuration. Also allow HTTPS origins from Cloudflare Tunnel domains.
    # This still keeps the regex scoped to HTTP/HTTPS origins and matches the common dev ports used by the project.
    cors_origin_regex = r"https?://(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|\\d{1,3}(?:\\.\\d{1,3}){3}|[a-zA-Z0-9-]+\\.local|.*\\.vistter\\.com)(?::\\d+)?"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads directory for serving uploaded assets
# Allow overriding via environment variable to support Docker volume mounts
uploads_dir_env = os.getenv("UPLOADS_DIR")
uploads_path = Path(uploads_dir_env) if uploads_dir_env else (Path(__file__).parent / "uploads")
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(streams.router, prefix="/api/streams", tags=["streams"])
app.include_router(presets_router.router)  # PTZ Presets
app.include_router(assets.router)  # Assets (overlays, graphics, API images)
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(destinations.router)  # Streaming destinations (YouTube, Facebook, etc.)
app.include_router(watchdog.router)  # YouTube stream watchdog management
app.include_router(timelines.router)  # Timeline CRUD
app.include_router(timeline_execution.router)  # Timeline execution (start/stop/status)
app.include_router(settings.router)  # System settings
# Scheduling API
app.include_router(scheduler.router)
# Preview disabled per refactor away from local HLS preview
app.include_router(emergency.router)  # Emergency controls (kill all streams)

# Serve static files (React build)
# Support both Vite (dist) and CRA (build)
frontend_candidates = [
    Path(__file__).parent.parent / "frontend" / "dist",
    Path(__file__).parent.parent / "frontend" / "build",
]
frontend_path = next((p for p in frontend_candidates if p.exists()), None)
if frontend_path:
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the React frontend"""
    # Resolve the frontend index.html if available
    if frontend_path:
        frontend_file = frontend_path / "index.html"
        if frontend_file.exists():
            return HTMLResponse(content=frontend_file.read_text())
    return HTMLResponse(content="<h1>VistterStream Backend Running</h1><p>Frontend not built yet</p>")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "VistterStream API",
        "version": "1.0.0"
    }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize background services on startup"""
    print("🚀 Starting VistterStream Backend...")
    print("📷 Starting camera health monitor...")
    await start_health_monitor()
    print("📡 Starting RTMP relay service (THE SECRET SAUCE!)...")
    relay_service = get_rtmp_relay_service()
    await relay_service.start_all_cameras()
    # Start scheduler loop
    if get_scheduler_service:
        try:
            await get_scheduler_service().start()
            print("🗓️ Scheduler started")
        except Exception as e:
            print(f"⚠️ Failed to start scheduler: {e}")
    # Start YouTube watchdog manager
    try:
        print("🐕 Starting YouTube watchdog manager...")
        watchdog_manager = get_watchdog_manager()
        db = next(get_db())
        await watchdog_manager.start(db)
        print("✅ Watchdog manager started")
    except Exception as e:
        print(f"⚠️ Failed to start watchdog manager: {e}")
    print("✅ All services started")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background services on shutdown"""
    print("🛑 Shutting down VistterStream Backend...")
    print("📷 Stopping camera health monitor...")
    await stop_health_monitor()
    print("📡 Stopping RTMP relay service...")
    relay_service = get_rtmp_relay_service()
    await relay_service.stop_all_relays()
    # Stop scheduler loop
    if get_scheduler_service:
        try:
            await get_scheduler_service().stop()
        except Exception:
            pass
    # Stop watchdog manager
    try:
        print("🐕 Stopping watchdog manager...")
        watchdog_manager = get_watchdog_manager()
        await watchdog_manager.stop_all()
        print("✅ Watchdog manager stopped")
    except Exception:
        pass
    print("✅ All services stopped")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
