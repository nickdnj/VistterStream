"""
Scheduler API endpoints for managing and triggering schedules.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from models.database import get_db
from models.schedule import Schedule, ScheduleTimeline
from models.timeline import Timeline
from models.destination import StreamingDestination
from services.scheduler_service import get_scheduler_service

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


class ScheduleTimelineItem(BaseModel):
    timeline_id: int
    order_index: int


class ScheduleCreate(BaseModel):
    name: str
    is_enabled: bool = True
    timezone: str = "UTC"
    days_of_week: List[int] = [0, 1, 2, 3, 4, 5, 6]
    window_start: str = "00:00"
    window_end: str = "23:59"
    destination_ids: List[int] = []
    timelines: List[ScheduleTimelineItem] = []


class TriggerScheduleRequest(BaseModel):
    force: bool = False


@router.get("")
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


@router.post("")
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db)):
    # Validate timelines
    tl_ids = [t.timeline_id for t in payload.timelines]
    if tl_ids:
        count = db.query(Timeline).filter(Timeline.id.in_(tl_ids)).count()
        if count != len(tl_ids):
            raise HTTPException(status_code=400, detail="One or more timelines not found")

    # Validate destinations
    if payload.destination_ids:
        count_d = (
            db.query(StreamingDestination)
            .filter(StreamingDestination.id.in_(payload.destination_ids))
            .count()
        )
        if count_d != len(payload.destination_ids):
            raise HTTPException(status_code=400, detail="One or more destinations not found")

    schedule = Schedule(
        name=payload.name,
        is_enabled=payload.is_enabled,
        timezone=payload.timezone,
        days_of_week=payload.days_of_week,
        window_start=payload.window_start,
        window_end=payload.window_end,
        destination_ids=payload.destination_ids,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    for item in payload.timelines:
        entry = ScheduleTimeline(
            schedule_id=schedule.id,
            timeline_id=item.timeline_id,
            order_index=item.order_index,
        )
        db.add(entry)
    db.commit()

    return {"id": schedule.id}


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(schedule)
    db.commit()
    return {"deleted": True}


@router.post("/{schedule_id}/run")
async def run_schedule(schedule_id: int, request: TriggerScheduleRequest):
    service = get_scheduler_service()
    success = await service.trigger_schedule(schedule_id, force=request.force)
    if not success:
        raise HTTPException(status_code=400, detail="Unable to start schedule (inactive window or missing data)")
    return {"started": True, "schedule_id": schedule_id, "forced": request.force}


@router.post("/{schedule_id}/stop")
async def stop_schedule(schedule_id: int):
    service = get_scheduler_service()
    success = await service.stop_schedule(schedule_id)
    if not success:
        raise HTTPException(status_code=400, detail="Schedule is not currently running")
    return {"stopped": True, "schedule_id": schedule_id}


@router.get("/running")
async def list_running_schedules():
    service = get_scheduler_service()
    running = service.list_running()
    return [
        {
            "schedule_id": item.schedule_id,
            "timeline_id": item.timeline_id,
            "started_at": item.started_at.isoformat(),
            "window_started_at": item.window_started_at.isoformat(),
            "timeline_index": item.timeline_index,
        }
        for item in running
    ]
