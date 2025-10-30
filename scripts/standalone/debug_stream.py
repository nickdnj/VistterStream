#!/usr/bin/env python3
import sys
sys.path.insert(0, 'backend')

from models.database import SessionLocal, Stream
from models.schemas import StreamCreate, StreamDestination
from services.stream_service import StreamService

# Create database session
db = SessionLocal()

try:
    # Create stream service
    service = StreamService(db)
    
    # Create stream data
    stream_data = StreamCreate(
        name="Test YouTube Stream",
        camera_id=6,
        destination=StreamDestination.YOUTUBE,
        stream_key="3fxp-wjv9-xxxa-94hd-0q3p",
        rtmp_url="rtmp://a.rtmp.youtube.com/live2",
        resolution="1920x1080",
        bitrate="4500k",
        framerate=30
    )
    
    print("Creating stream...")
    import asyncio
    stream = asyncio.run(service.create_stream(stream_data))
    print(f"✅ Stream created: {stream}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()

