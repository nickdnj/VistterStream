#!/usr/bin/env python3
"""Test camera RTSP URLs"""

import sys
import os
import base64

os.environ['DATABASE_URL'] = 'sqlite:///backend/vistterstream.db'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import SessionLocal, Camera

db = SessionLocal()

try:
    cameras = db.query(Camera).filter(Camera.id.in_([1, 3])).all()
    
    for camera in cameras:
        print(f"\n{'='*60}")
        print(f"Camera: {camera.name} (ID: {camera.id})")
        print(f"{'='*60}")
        print(f"Type: {camera.type}")
        print(f"Address: {camera.address}")
        print(f"Port: {camera.port}")
        print(f"Path: {camera.stream_path}")
        print(f"Username: {camera.username}")
        
        # Decode password
        password = None
        if camera.password_enc:
            try:
                password = base64.b64decode(camera.password_enc).decode()
                print(f"Password: {password}")
            except Exception as e:
                print(f"Password decode error: {e}")
        
        # Build RTSP URL
        if camera.username and password:
            rtsp_url = f"rtsp://{camera.username}:{password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            rtsp_url = f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"
            
        print(f"\nRTSP URL: {rtsp_url}")
        
finally:
    db.close()

