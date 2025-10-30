#!/usr/bin/env python3
"""
Test the composite stream timeline executor
Starts a timeline with camera switching to YouTube
"""

import sys
import os
import asyncio

# Set the database path to the backend directory
os.environ['DATABASE_URL'] = 'sqlite:///backend/vistterstream.db'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from models.database import SessionLocal
from models.timeline import Timeline
from services.timeline_executor import get_timeline_executor


async def test_composite_stream(timeline_id: int, stream_key: str):
    """Test timeline execution"""
    
    db = SessionLocal()
    
    try:
        # Get timeline
        timeline = db.query(Timeline).filter(Timeline.id == timeline_id).first()
        if not timeline:
            print(f"❌ Timeline {timeline_id} not found")
            return
            
        print(f"🎬 Starting composite stream:")
        print(f"  Timeline: {timeline.name}")
        print(f"  Duration: {timeline.duration}s per loop")
        print(f"  Loop: {timeline.loop}")
        print()
        
        # Build output URL
        rtmp_url = "rtmp://a.rtmp.youtube.com/live2"
        output_url = f"{rtmp_url}/{stream_key}"
        
        print(f"📡 Streaming to YouTube:")
        print(f"  RTMP URL: {rtmp_url}")
        print(f"  Stream Key: {stream_key[:10]}...")
        print()
        
        # Get timeline executor
        executor = get_timeline_executor()
        
        # Start timeline
        print("▶️  Starting timeline execution...")
        success = await executor.start_timeline(
            timeline_id=timeline_id,
            output_urls=[output_url],
            encoding_profile=None  # Use default reliability profile
        )
        
        if not success:
            print("❌ Failed to start timeline")
            return
            
        print("✅ Timeline started!")
        print()
        print("🔄 Composite stream is now running:")
        print("   - Camera switches will happen every 60 seconds")
        print("   - Check YouTube to see the stream")
        print()
        print("Press Ctrl+C to stop...")
        
        # Wait for user interrupt
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print()
            print("🛑 Stopping timeline...")
            await executor.stop_timeline(timeline_id)
            print("✅ Timeline stopped")
            
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/standalone/test_composite_stream.py <timeline_id> <youtube_stream_key>")
        print()
        print("Example:")
        print("  python scripts/standalone/test_composite_stream.py 1 xxxx-xxxx-xxxx-xxxx")
        sys.exit(1)
        
    timeline_id = int(sys.argv[1])
    stream_key = sys.argv[2]
    
    asyncio.run(test_composite_stream(timeline_id, stream_key))

