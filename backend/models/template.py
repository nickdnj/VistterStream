"""
Overlay Template models for the Asset Management Studio
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .database import Base


class OverlayTemplate(Base):
    __tablename__ = "overlay_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # weather, marine, time_date, sponsor_ad, lower_third, social_media
    description = Column(String)
    config_schema = Column(Text, nullable=False)  # JSON Schema defining configurable fields
    default_config = Column(Text, nullable=False)  # Default values as JSON
    preview_path = Column(String)  # Path to preview PNG
    version = Column(Integer, default=1)
    is_bundled = Column(Boolean, default=True)  # Ships with Docker image
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    instances = relationship("TemplateInstance", back_populates="template", cascade="all, delete-orphan")


class TemplateInstance(Base):
    __tablename__ = "template_instances"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("overlay_templates.id"), nullable=False)
    config_values = Column(Text, nullable=False)  # User-provided config as JSON
    asset_id = Column(Integer, ForeignKey("assets.id", use_alter=True), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    template = relationship("OverlayTemplate", back_populates="instances")
