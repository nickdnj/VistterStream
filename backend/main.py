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
from routers import cameras, auth, streams, presets, status

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
app.include_router(presets.router, prefix="/api/presets", tags=["presets"])
app.include_router(status.router, prefix="/api/status", tags=["status"])

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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
