"""Audit log model for tracking state-changing operations."""

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, timezone

from models.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user_id = Column(Integer, index=True)
    username = Column(String)
    action = Column(String, nullable=False, index=True)  # e.g. "login", "stream.start", "destination.create"
    method = Column(String)  # HTTP method
    path = Column(String)  # Request path
    status_code = Column(Integer)
    ip_address = Column(String)
    detail = Column(Text)  # Additional context (e.g. destination_id, timeline_id)
