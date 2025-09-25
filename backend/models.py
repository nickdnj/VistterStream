from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

    cameras = relationship("Camera", back_populates="owner")

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)
    protocol = Column(String)
    address = Column(String)
    username = Column(String)
    password_enc = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="cameras")
    presets = relationship("Preset", back_populates="camera")
    streams = relationship("Stream", back_populates="camera")

class Preset(Base):
    __tablename__ = "presets"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    name = Column(String)
    pan = Column(Float)
    tilt = Column(Float)
    zoom = Column(Float)

    camera = relationship("Camera", back_populates="presets")

class Stream(Base):
    __tablename__ = "streams"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    destination = Column(String)
    status = Column(String)
    started_at = Column(String)

    camera = relationship("Camera", back_populates="streams")
