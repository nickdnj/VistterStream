#!/usr/bin/env python3
"""Debug timeline execution to see errors"""

import sys
import os
import asyncio
import logging

# Set the database path
os.environ['DATABASE_URL'] = 'sqlite:///backend/vistterstream.db'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set up logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from models.database import SessionLocal
from models.timeline import Timeline
from services.timeline_executor import get_timeline_executor


async def debug_timeline():
    """Test timeline with full output"""
    
    timeline_id = 1
    stream_key = "3fxp-wjv9-xxxa-94hd-0q3p"
    
    print("=" * 60)
    print("DEBUG: Starting timeline execution")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get timeline
        timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
        if not timeline:
            print(f"ERROR: Timeline {timeline_id} not found")
            return
            
        print(f"Timeline: {timeline.name}")
        print(f"Duration: {timeline.duration}s")
        print(f"Loop: {timeline.loop}")
        print()
        
        # Build output URL
        rtmp_url = "rtmp://a.rtmp.youtube.com/live2"
        output_url = f"{rtmp_url}/{stream_key}"
        
        print(f"Output URL: {output_url}")
        print()
        
        # Get timeline executor
        executor = get_timeline_executor()
        
        # Start timeline
        print("Starting timeline...")
        success = await executor.start_timeline(
            timeline_id=timeline_id,
            output_urls=[output_url],
            encoding_profile=None
        )
        
        if not success:
            print("ERROR: Failed to start timeline")
            return
            
        print("Timeline started successfully!")
        print()
        print("Waiting for execution (press Ctrl+C to stop)...")
        print()
        
        # Wait for user interrupt
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print()
            print("Stopping timeline...")
            await executor.stop_timeline(timeline_id)
            print("Timeline stopped")
            
    finally:
        db.close()


if __name__ == "__main__":
    try:
        asyncio.run(debug_timeline())
    except KeyboardInterrupt:
        print("\nExiting...")

