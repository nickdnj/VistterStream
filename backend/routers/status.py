"""
System status API endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import psutil
import time
from datetime import datetime

from models.database import get_db, Camera, Stream
from models.schemas import SystemStatus, CameraStatus

router = APIRouter()

# Store start time for uptime calculation
start_time = time.time()

@router.get("/system", response_model=SystemStatus)
async def get_system_status(db: Session = Depends(get_db)):
    """Get system status and metrics"""
    # Get system metrics
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get database counts
    active_cameras = db.query(Camera).filter(Camera.is_active == True).count()
    active_streams = db.query(Stream).filter(Stream.status == "running").count()
    
    # Calculate uptime
    uptime = time.time() - start_time
    
    return SystemStatus(
        status="healthy",
        uptime=uptime,
        cpu_usage=cpu_usage,
        memory_usage=memory.percent,
        disk_usage=disk.percent,
        active_cameras=active_cameras,
        active_streams=active_streams
    )

@router.get("/cameras", response_model=list[CameraStatus])
async def get_cameras_status(db: Session = Depends(get_db)):
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
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VistterStream API"
    }
