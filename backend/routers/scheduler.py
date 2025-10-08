"""
Scheduler API: create schedules, list, update, and control run state
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from models.database import get_db
from models.schedule import Schedule, ScheduleTimeline
from models.timeline import Timeline
from models.destination import StreamingDestination
from services.timeline_executor import get_timeline_executor

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class ScheduleTimelineItem(BaseModel):
    timeline_id: int
    order_index: int


class ScheduleCreate(BaseModel):
    name: str
    is_enabled: bool = True
    timezone: str = "UTC"
    days_of_week: List[int] = [0,1,2,3,4,5,6]
    window_start: str = "00:00"
    window_end: str = "23:59"
    destination_ids: List[int] = []
    timelines: List[ScheduleTimelineItem] = []


@router.get("/")
def list_schedules(db: Session = Depends(get_db)):
    items = db.query(Schedule).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "is_enabled": s.is_enabled,
            "timezone": s.timezone,
            "days_of_week": s.days_of_week,
            "window_start": s.window_start,
            "window_end": s.window_end,
            "destination_ids": s.destination_ids,
            "timelines": [
                {"timeline_id": st.timeline_id, "order_index": st.order_index}
                for st in sorted(s.timelines, key=lambda x: x.order_index)
            ],
        }
        for s in items
    ]


@router.post("/")
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db)):
    # Validate timelines
    tl_ids = [t.timeline_id for t in payload.timelines]
    if tl_ids:
        count = db.query(Timeline).filter(Timeline.id.in_(tl_ids)).count()
        if count != len(tl_ids):
            raise HTTPException(status_code=400, detail="One or more timelines not found")

    # Validate destinations
    if payload.destination_ids:
        count_d = db.query(StreamingDestination).filter(StreamingDestination.id.in_(payload.destination_ids)).count()
        if count_d != len(payload.destination_ids):
            raise HTTPException(status_code=400, detail="One or more destinations not found")

    s = Schedule(
        name=payload.name,
        is_enabled=payload.is_enabled,
        timezone=payload.timezone,
        days_of_week=payload.days_of_week,
        window_start=payload.window_start,
        window_end=payload.window_end,
        destination_ids=payload.destination_ids,
    )
    db.add(s)
    db.commit()
    db.refresh(s)

    for item in payload.timelines:
        st = ScheduleTimeline(schedule_id=s.id, timeline_id=item.timeline_id, order_index=item.order_index)
        db.add(st)
    db.commit()

    return {"id": s.id}


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    s = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(s)
    db.commit()
    return {"deleted": True}


