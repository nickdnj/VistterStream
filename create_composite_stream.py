#!/usr/bin/env python3
"""
Create a composite stream with camera switching
Camera 1 for 1 minute → Camera 2 for 1 minute → Repeat
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import SessionLocal, Camera, create_tables
from models.timeline import Timeline, TimelineTrack, TimelineCue
from datetime import datetime


def create_composite_stream():
    """Create a timeline with alternating cameras"""
    
    # Initialize database
    create_tables()
    db = SessionLocal()
    
    try:
        # Get available cameras
        cameras = db.query(Camera).all()
        if len(cameras) < 2:
            print(f"❌ Need at least 2 cameras, found {len(cameras)}")
            print("Please add cameras first!")
            return
            
        camera1 = cameras[0]
        camera2 = cameras[1]
        
        print(f"📷 Creating composite stream:")
        print(f"  Camera 1: {camera1.name} (ID: {camera1.id})")
        print(f"  Camera 2: {camera2.name} (ID: {camera2.id})")
        print()
        
        # Create timeline
        timeline = Timeline(
            name="Alternating Camera Stream",
            description="Switches between Camera 1 and Camera 2 every 1 minute",
            duration=120.0,  # 2 minutes total (will loop)
            fps=30,
            resolution="1920x1080",
            loop=True  # Loop forever
        )
        db.add(timeline)
        db.flush()  # Get the timeline ID
        
        print(f"✅ Created timeline: {timeline.name} (ID: {timeline.id})")
        
        # Create video track
        video_track = TimelineTrack(
            timeline_id=timeline.id,
            track_type="video",
            layer=0,
            is_enabled=True
        )
        db.add(video_track)
        db.flush()  # Get the track ID
        
        print(f"✅ Created video track (ID: {video_track.id})")
        
        # Create cue 1: Camera 1 for 60 seconds
        cue1 = TimelineCue(
            track_id=video_track.id,
            cue_order=1,
            start_time=0.0,
            duration=60.0,  # 1 minute
            action_type="show_camera",
            action_params={
                "camera_id": camera1.id,
                "transition": "cut"
            },
            transition_type="cut",
            transition_duration=0.0
        )
        db.add(cue1)
        
        print(f"✅ Created cue 1: Show {camera1.name} for 60 seconds")
        
        # Create cue 2: Camera 2 for 60 seconds
        cue2 = TimelineCue(
            track_id=video_track.id,
            cue_order=2,
            start_time=60.0,
            duration=60.0,  # 1 minute
            action_type="show_camera",
            action_params={
                "camera_id": camera2.id,
                "transition": "cut"
            },
            transition_type="cut",
            transition_duration=0.0
        )
        db.add(cue2)
        
        print(f"✅ Created cue 2: Show {camera2.name} for 60 seconds")
        
        # Commit all changes
        db.commit()
        
        print()
        print("🎉 Composite stream created successfully!")
        print()
        print("Timeline details:")
        print(f"  ID: {timeline.id}")
        print(f"  Name: {timeline.name}")
        print(f"  Duration: {timeline.duration} seconds per loop")
        print(f"  Loop: {timeline.loop}")
        print()
        print("Cues:")
        print(f"  1. {camera1.name} (0:00 - 1:00)")
        print(f"  2. {camera2.name} (1:00 - 2:00)")
        print(f"  [Loop back to cue 1]")
        print()
        print("🚀 To start streaming this timeline, use the API or UI")
        print(f"   Timeline ID: {timeline.id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_composite_stream()

