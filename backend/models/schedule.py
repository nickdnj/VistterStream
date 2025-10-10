"""
Scheduling models to run timelines automatically within time windows
"""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=True)
    timezone = Column(String, default="UTC")
    # Days of week active, 0=Mon ... 6=Sun
    days_of_week = Column(JSON, default=[0,1,2,3,4,5,6])
    # Daily window in local time zone (24h "HH:MM" strings)
    window_start = Column(String, default="00:00")
    window_end = Column(String, default="23:59")
    # Destination IDs to stream to when schedule runs
    destination_ids = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    timelines = relationship("ScheduleTimeline", back_populates="schedule", cascade="all, delete-orphan")


class ScheduleTimeline(Base):
    __tablename__ = "schedule_timelines"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"), nullable=False)
    timeline_id = Column(Integer, ForeignKey("timelines.id"), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)

    schedule = relationship("Schedule", back_populates="timelines")


