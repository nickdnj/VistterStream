"""
YouTube Watchdog Management API
Control and monitor YouTube stream watchdogs
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict

from models.database import get_db
from models.destination import StreamingDestination
from services.watchdog_manager import get_watchdog_manager

router = APIRouter(prefix="/api/watchdog", tags=["watchdog"])


@router.get("/status")
def get_all_watchdog_status():
    """Get status of all running watchdogs"""
    manager = get_watchdog_manager()
    statuses = manager.get_all_statuses()
    
    return {
        "watchdog_count": len(statuses),
        "watchdogs": statuses
    }


@router.get("/{destination_id}/status")
def get_watchdog_status(destination_id: int, db: Session = Depends(get_db)):
    """Get status of watchdog for a specific destination"""
    # Verify destination exists
    destination = db.query(StreamingDestination).filter(
        StreamingDestination.id == destination_id
    ).first()
    
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    manager = get_watchdog_manager()
    status = manager.get_watchdog_status(destination_id)
    
    return {
        "destination_id": destination_id,
        "destination_name": destination.name,
        "platform": destination.platform,
        "watchdog_enabled": destination.enable_watchdog,
        **status
    }


@router.post("/{destination_id}/start")
async def start_watchdog(destination_id: int, db: Session = Depends(get_db)):
    """Start watchdog for a destination"""
    destination = db.query(StreamingDestination).filter(
        StreamingDestination.id == destination_id
    ).first()
    
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    if not destination.enable_watchdog:
        raise HTTPException(status_code=400, detail="Watchdog is not enabled for this destination")
    
    manager = get_watchdog_manager()
    await manager.start_watchdog(destination)
    
    return {
        "message": f"Watchdog started for destination {destination_id} ({destination.name})",
        "destination_id": destination_id
    }


@router.post("/{destination_id}/stop")
async def stop_watchdog(destination_id: int, db: Session = Depends(get_db)):
    """Stop watchdog for a destination"""
    destination = db.query(StreamingDestination).filter(
        StreamingDestination.id == destination_id
    ).first()
    
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    manager = get_watchdog_manager()
    await manager.stop_watchdog(destination_id)
    
    return {
        "message": f"Watchdog stopped for destination {destination_id}",
        "destination_id": destination_id
    }


@router.post("/{destination_id}/restart")
async def restart_watchdog(destination_id: int, db: Session = Depends(get_db)):
    """Restart watchdog for a destination"""
    destination = db.query(StreamingDestination).filter(
        StreamingDestination.id == destination_id
    ).first()
    
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    if destination.platform != "youtube":
        raise HTTPException(status_code=400, detail="Watchdog only supported for YouTube destinations")
    
    manager = get_watchdog_manager()
    await manager.restart_watchdog(destination)
    
    return {
        "message": f"Watchdog restarted for destination {destination_id} ({destination.name})",
        "destination_id": destination_id
    }


@router.post("/reload")
async def reload_all_watchdogs(db: Session = Depends(get_db)):
    """Reload all watchdogs from database configuration"""
    manager = get_watchdog_manager()
    await manager.reload_from_db(db)
    
    statuses = manager.get_all_statuses()
    
    return {
        "message": "Watchdog configuration reloaded",
        "active_watchdogs": len(statuses),
        "watchdogs": statuses
    }


@router.post("/stop-all")
async def stop_all_watchdogs():
    """Stop all running watchdogs"""
    manager = get_watchdog_manager()
    await manager.stop_all()
    
    return {
        "message": "All watchdogs stopped"
    }

