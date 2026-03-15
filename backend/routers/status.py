"""
System status API endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import asyncio
import platform
import subprocess
import psutil
import time
import logging
from datetime import datetime, timezone
from typing import Optional

from models.database import get_db, Camera, Stream, User
from models.timeline import Timeline
from models.destination import StreamingDestination
from models.schemas import SystemStatus, SystemInfo, CameraStatus
from services.timeline_executor import get_timeline_executor
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Store start time for uptime calculation
start_time = time.time()

# Store initial network stats for delta calculation
initial_net_io = psutil.net_io_counters()
last_net_check = time.time()

@router.get("/system", response_model=SystemStatus)
async def get_system_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get system status and metrics"""
    global last_net_check
    
    # Get system metrics
    cpu_usage = await asyncio.to_thread(psutil.cpu_percent, 1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Calculate network usage as percentage of typical bandwidth (100 Mbps = 12.5 MB/s)
    # This measures current throughput as % of a 100 Mbps connection
    current_time = time.time()
    net_io = psutil.net_io_counters()
    time_delta = current_time - last_net_check
    
    if time_delta > 0:
        bytes_sent = net_io.bytes_sent - initial_net_io.bytes_sent
        bytes_recv = net_io.bytes_recv - initial_net_io.bytes_recv
        total_bytes_per_sec = (bytes_sent + bytes_recv) / time_delta
        # Calculate as percentage of 100 Mbps (12.5 MB/s)
        network_usage = min((total_bytes_per_sec / (12.5 * 1024 * 1024)) * 100, 100.0)
    else:
        network_usage = 0.0
    
    last_net_check = current_time
    
    # Get database counts
    active_cameras = db.query(Camera).filter(Camera.is_active == True).count()
    active_streams = db.query(Stream).filter(Stream.status == "running").count()
    
    # Calculate uptime
    uptime = time.time() - start_time
    
    # Check for active timeline streaming
    timeline_streaming = False
    timeline_name = None
    timeline_destinations = None
    
    try:
        executor = get_timeline_executor()
        if executor.active_timelines:
            # Get the first active timeline (typically only one runs at a time)
            timeline_id = list(executor.active_timelines.keys())[0]
            timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
            
            if timeline:
                timeline_streaming = True
                timeline_name = timeline.name
                
                # Get destination names from timeline metadata if available
                # Note: We store this when starting the timeline
                if hasattr(executor, 'timeline_destinations') and timeline_id in executor.timeline_destinations:
                    timeline_destinations = executor.timeline_destinations[timeline_id]
    except Exception as e:
        logger.warning(f"Failed to get timeline status: {e}")
    
    return SystemStatus(
        status="healthy",
        uptime=uptime,
        cpu_usage=cpu_usage,
        memory_usage=memory.percent,
        disk_usage=disk.percent,
        network_usage=network_usage,
        active_cameras=active_cameras,
        active_streams=active_streams,
        timeline_streaming=timeline_streaming,
        timeline_name=timeline_name,
        timeline_destinations=timeline_destinations
    )

def _detect_ffmpeg_version() -> str:
    """Detect FFmpeg version by running ffmpeg -version"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # First line looks like: "ffmpeg version 7.1.1 Copyright ..."
        first_line = result.stdout.strip().split("\n")[0]
        # Extract version string after "ffmpeg version "
        if "ffmpeg version" in first_line:
            return first_line.split("ffmpeg version")[1].strip().split()[0]
        return first_line
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        logger.warning(f"Failed to detect FFmpeg version: {e}")
        return "unknown"


# Cache system info since it doesn't change at runtime
_cached_system_info: Optional[SystemInfo] = None


@router.get("/system/info", response_model=SystemInfo)
async def get_system_info():
    """Get static system information (no auth required)"""
    global _cached_system_info

    if _cached_system_info is None:
        from main import app as fastapi_app

        ffmpeg_version = await asyncio.to_thread(_detect_ffmpeg_version)

        _cached_system_info = SystemInfo(
            version=fastapi_app.version,
            platform=f"{platform.system()} {platform.machine()}",
            database="SQLite",
            ffmpeg_version=ffmpeg_version,
            python_version=platform.python_version(),
        )

    return _cached_system_info


@router.get("/cameras", response_model=list[CameraStatus])
async def get_cameras_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get status of all cameras"""
    cameras = db.query(Camera).filter(Camera.is_active == True).all()
    camera_statuses = []
    
    for camera in cameras:
        # Simple status check - in production, this would be more sophisticated
        status = "online" if camera.last_seen else "offline"
        
        camera_statuses.append(CameraStatus(
            camera_id=camera.id,
            name=camera.name,
            status=status,
            last_seen=camera.last_seen,
            error_message=None
        ))
    
    return camera_statuses

@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "VistterStream API"
    }
