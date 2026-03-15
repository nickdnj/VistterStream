"""
Font model for the Asset Management Studio
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone

from .database import Base


class Font(Base):
    __tablename__ = "fonts"

    id = Column(Integer, primary_key=True, index=True)
    family = Column(String, nullable=False)  # CSS font-family value
    weight = Column(String, default="400")  # CSS font weight
    style = Column(String, default="normal")  # normal, italic
    source = Column(String, nullable=False)  # system, uploaded, google
    file_path = Column(String)  # Path to .ttf/.otf (null for system fonts without explicit path)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
