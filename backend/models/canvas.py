"""
Canvas Project model for the Asset Management Studio
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from datetime import datetime, timezone

from .database import Base


class CanvasProject(Base):
    __tablename__ = "canvas_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    canvas_json = Column(Text, nullable=False)  # Fabric.js serialized JSON
    thumbnail_path = Column(String)  # Path to thumbnail PNG
    width = Column(Integer, default=1920)
    height = Column(Integer, default=1080)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
