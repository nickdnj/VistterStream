"""
Timeline management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from models.database import get_db
from models.timeline import Timeline, TimelineTrack, TimelineCue
from pydantic import BaseModel

router = APIRouter(prefix="/api/timelines", tags=["timelines"])


# Pydantic schemas
class CueCreate(BaseModel):
    cue_order: int
    start_time: float
    duration: float
    action_type: str
    action_params: dict
    transition_type: str = "cut"
    transition_duration: float = 0.0


class CueResponse(CueCreate):
    id: int
    track_id: int
    
    class Config:
        from_attributes = True


class TrackCreate(BaseModel):
    track_type: str  # "video" or "overlay"
    layer: int = 0
    is_enabled: bool = True
    cues: List[CueCreate] = []


class TrackResponse(BaseModel):
    id: int
    timeline_id: int
    track_type: str
    layer: int
    is_enabled: bool
    cues: List[CueResponse] = []
    
    class Config:
        from_attributes = True


class TimelineCreate(BaseModel):
    name: str
    description: str = ""
    duration: float
    fps: int = 30
    resolution: str = "1920x1080"
    loop: bool = True
    tracks: List[TrackCreate] = []


class TimelineUpdate(BaseModel):
    name: str = None
    description: str = None
    duration: float = None
    fps: int = None
    resolution: str = None
    loop: bool = None
    is_active: bool = None
    tracks: List[TrackCreate] = None


class TimelineResponse(BaseModel):
    id: int
    name: str
    description: str
    duration: float
    fps: int
    resolution: str
    loop: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    tracks: List[TrackResponse] = []
    
    class Config:
        from_attributes = True


# API Endpoints
@router.get("/", response_model=List[TimelineResponse])
def get_timelines(db: Session = Depends(get_db)):
    """Get all timelines"""
    timelines = db.query(Timeline).all()
    return timelines


@router.get("/{timeline_id}", response_model=TimelineResponse)
def get_timeline(timeline_id: int, db: Session = Depends(get_db)):
    """Get a specific timeline"""
    timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    return timeline


@router.post("/", response_model=TimelineResponse)
def create_timeline(timeline_data: TimelineCreate, db: Session = Depends(get_db)):
    """Create a new timeline"""
    try:
        # Create timeline
        timeline = Timeline(
            name=timeline_data.name,
            description=timeline_data.description,
            duration=timeline_data.duration,
            fps=timeline_data.fps,
            resolution=timeline_data.resolution,
            loop=timeline_data.loop
        )
        db.add(timeline)
        db.flush()  # Get timeline ID
        
        # Create tracks
        for track_data in timeline_data.tracks:
            track = TimelineTrack(
                timeline_id=timeline.id,
                track_type=track_data.track_type,
                layer=track_data.layer,
                is_enabled=track_data.is_enabled
            )
            db.add(track)
            db.flush()  # Get track ID
            
            # Create cues
            for cue_data in track_data.cues:
                cue = TimelineCue(
                    track_id=track.id,
                    cue_order=cue_data.cue_order,
                    start_time=cue_data.start_time,
                    duration=cue_data.duration,
                    action_type=cue_data.action_type,
                    action_params=cue_data.action_params,
                    transition_type=cue_data.transition_type,
                    transition_duration=cue_data.transition_duration
                )
                db.add(cue)
        
        db.commit()
        db.refresh(timeline)
        return timeline
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create timeline: {str(e)}")


@router.put("/{timeline_id}", response_model=TimelineResponse)
def update_timeline(timeline_id: int, timeline_data: TimelineUpdate, db: Session = Depends(get_db)):
    """Update a timeline"""
    timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    try:
        # Update fields
        if timeline_data.name is not None:
            timeline.name = timeline_data.name
        if timeline_data.description is not None:
            timeline.description = timeline_data.description
        if timeline_data.duration is not None:
            timeline.duration = timeline_data.duration
        if timeline_data.fps is not None:
            timeline.fps = timeline_data.fps
        if timeline_data.resolution is not None:
            timeline.resolution = timeline_data.resolution
        if timeline_data.loop is not None:
            timeline.loop = timeline_data.loop
        if timeline_data.is_active is not None:
            timeline.is_active = timeline_data.is_active
        
        # Update tracks and cues if provided
        if timeline_data.tracks is not None:
            # Delete existing tracks and cues (cascade delete)
            db.query(TimelineTrack).filter(TimelineTrack.timeline_id == timeline_id).delete()
            
            # Create new tracks and cues
            for track_data in timeline_data.tracks:
                track = TimelineTrack(
                    timeline_id=timeline.id,
                    track_type=track_data.track_type,
                    layer=track_data.layer,
                    is_enabled=track_data.is_enabled
                )
                db.add(track)
                db.flush()  # Get track ID
                
                # Create cues
                for cue_data in track_data.cues:
                    cue = TimelineCue(
                        track_id=track.id,
                        cue_order=cue_data.cue_order,
                        start_time=cue_data.start_time,
                        duration=cue_data.duration,
                        action_type=cue_data.action_type,
                        action_params=cue_data.action_params,
                        transition_type=cue_data.transition_type,
                        transition_duration=cue_data.transition_duration
                    )
                    db.add(cue)
        
        timeline.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(timeline)
        return timeline
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update timeline: {str(e)}")


@router.delete("/{timeline_id}")
def delete_timeline(timeline_id: int, db: Session = Depends(get_db)):
    """Delete a timeline"""
    timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not timeline:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    db.delete(timeline)
    db.commit()
    return {"message": "Timeline deleted successfully"}


@router.post("/{timeline_id}/duplicate", response_model=TimelineResponse)
def duplicate_timeline(timeline_id: int, db: Session = Depends(get_db)):
    """Duplicate an existing timeline"""
    original = db.query(Timeline).filter(Timeline.id == timeline_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Timeline not found")
    
    # Create duplicate
    duplicate = Timeline(
        name=f"{original.name} (Copy)",
        description=original.description,
        duration=original.duration,
        fps=original.fps,
        resolution=original.resolution,
        loop=original.loop
    )
    db.add(duplicate)
    db.flush()
    
    # Duplicate tracks
    for track in original.tracks:
        new_track = TimelineTrack(
            timeline_id=duplicate.id,
            track_type=track.track_type,
            layer=track.layer,
            is_enabled=track.is_enabled
        )
        db.add(new_track)
        db.flush()
        
        # Duplicate cues
        for cue in track.cues:
            new_cue = TimelineCue(
                track_id=new_track.id,
                cue_order=cue.cue_order,
                start_time=cue.start_time,
                duration=cue.duration,
                action_type=cue.action_type,
                action_params=cue.action_params,
                transition_type=cue.transition_type,
                transition_duration=cue.transition_duration
            )
            db.add(new_cue)
    
    db.commit()
    db.refresh(duplicate)
    return duplicate

