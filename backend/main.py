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
from routers import cameras, auth, streams, status, timelines, timeline_execution, emergency, destinations
from routers import presets as presets_router

# Import health monitor
from services.camera_health_monitor import start_health_monitor, stop_health_monitor

# Create FastAPI app
app = FastAPI(
    title="VistterStream API",
    description="Local streaming appliance for camera management and live streaming",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(streams.router, prefix="/api/streams", tags=["streams"])
app.include_router(presets_router.router)  # PTZ Presets
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(destinations.router)  # Streaming destinations (YouTube, Facebook, etc.)
app.include_router(timelines.router)  # Timeline CRUD
app.include_router(timeline_execution.router)  # Timeline execution (start/stop/status)
app.include_router(emergency.router)  # Emergency controls (kill all streams)

# Serve static files (React build)
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the React frontend"""
    frontend_file = Path(__file__).parent.parent / "frontend" / "dist" / "index.html"
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
    print("✅ All services started")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background services on shutdown"""
    print("🛑 Shutting down VistterStream Backend...")
    print("📷 Stopping camera health monitor...")
    await stop_health_monitor()
    print("✅ All services stopped")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
