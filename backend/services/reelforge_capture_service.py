"""
ReelForge Capture Service
Manages the capture queue and integrates with timeline executor for clip capture.
"""

import asyncio
import logging
import os
import base64
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from pathlib import Path

from sqlalchemy.orm import Session

from models.database import SessionLocal, Camera, Preset
from models.reelforge import ReelCaptureQueue, ReelPost, ReelTemplate

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ReelForgeCaptureService:
    """
    Manages ReelForge capture queue and executes captures when timeline hits matching camera/preset.
    """
    
    def __init__(self):
        self._capture_queue: Dict[Tuple[int, Optional[int]], ReelCaptureQueue] = {}  # (camera_id, preset_id) -> queue_item
        self._active_captures: Dict[int, asyncio.subprocess.Process] = {}  # post_id -> ffmpeg process
        self._lock = asyncio.Lock()
        
        # Ensure uploads directory exists
        self._uploads_dir = Path(__file__).parent.parent / "uploads" / "reelforge"
        self._clips_dir = self._uploads_dir / "clips"
        self._portraits_dir = self._uploads_dir / "portraits"
        self._outputs_dir = self._uploads_dir / "outputs"
        self._thumbnails_dir = self._uploads_dir / "thumbnails"
        
        for dir_path in [self._clips_dir, self._portraits_dir, self._outputs_dir, self._thumbnails_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def load_pending_captures(self, db: Session):
        """Load pending captures from database on startup"""
        queue_items = db.query(ReelCaptureQueue).filter(
            ReelCaptureQueue.status == "waiting"
        ).all()
        
        async with self._lock:
            for item in queue_items:
                key = (item.camera_id, item.preset_id)
                self._capture_queue[key] = item
        
        logger.info(f"📹 ReelForge: Loaded {len(queue_items)} pending capture(s)")
    
    async def add_to_queue(self, queue_item: ReelCaptureQueue):
        """Add a capture request to the queue"""
        async with self._lock:
            key = (queue_item.camera_id, queue_item.preset_id)
            self._capture_queue[key] = queue_item
        
        logger.info(f"📹 ReelForge: Queued capture for camera={queue_item.camera_id}, preset={queue_item.preset_id}")
    
    async def remove_from_queue(self, camera_id: int, preset_id: Optional[int]):
        """Remove a capture request from the queue"""
        async with self._lock:
            key = (camera_id, preset_id)
            if key in self._capture_queue:
                del self._capture_queue[key]
    
    def has_pending_capture(self, camera_id: int, preset_id: Optional[int]) -> bool:
        """Check if there's a pending capture for this camera/preset"""
        key = (camera_id, preset_id)
        return key in self._capture_queue
    
    def get_pending_capture(self, camera_id: int, preset_id: Optional[int]) -> Optional[ReelCaptureQueue]:
        """Get the pending capture for this camera/preset"""
        key = (camera_id, preset_id)
        return self._capture_queue.get(key)
    
    async def trigger_capture(
        self,
        camera_id: int,
        preset_id: Optional[int],
        db: Session
    ) -> bool:
        """
        Trigger a capture for the specified camera/preset.
        Called by timeline executor when it switches to a camera/preset that has a pending capture.
        """
        key = (camera_id, preset_id)
        
        async with self._lock:
            if key not in self._capture_queue:
                return False
            
            queue_item = self._capture_queue[key]
            
            # Check if already capturing
            if queue_item.post_id in self._active_captures:
                logger.warning(f"📹 ReelForge: Capture already in progress for post {queue_item.post_id}")
                return False
        
        # Get camera info
        camera = db.query(Camera).filter(Camera.id == camera_id).first()
        if not camera:
            logger.error(f"📹 ReelForge: Camera {camera_id} not found")
            return False
        
        # Get post info
        post = db.query(ReelPost).filter(ReelPost.id == queue_item.post_id).first()
        if not post:
            logger.error(f"📹 ReelForge: Post {queue_item.post_id} not found")
            return False
        
        # Get template for clip duration
        clip_duration = 30  # default
        if post.template_id:
            template = db.query(ReelTemplate).filter(ReelTemplate.id == post.template_id).first()
            if template:
                clip_duration = template.clip_duration
        
        # Update statuses
        queue_item.status = "capturing"
        queue_item.started_at = datetime.utcnow()
        post.status = "capturing"
        post.capture_started_at = datetime.utcnow()
        db.commit()
        
        # Start capture in background
        asyncio.create_task(
            self._execute_capture(
                post_id=post.id,
                queue_id=queue_item.id,
                camera=camera,
                clip_duration=clip_duration,
                key=key
            )
        )
        
        logger.info(f"📹 ReelForge: Started {clip_duration}s capture for post {post.id} from {camera.name}")
        return True
    
    async def _execute_capture(
        self,
        post_id: int,
        queue_id: int,
        camera: Camera,
        clip_duration: int,
        key: Tuple[int, Optional[int]]
    ):
        """Execute the actual capture via FFmpeg"""
        db = SessionLocal()
        
        try:
            # Build RTSP URL
            rtsp_url = self._build_rtsp_url(camera)
            
            # Output file path
            output_path = self._clips_dir / f"{post_id}.mp4"
            
            # Build FFmpeg command for capture
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-t', str(clip_duration),  # Duration
                '-c:v', 'copy',  # Copy video codec (fast, no re-encoding)
                '-c:a', 'aac',  # Audio codec
                '-movflags', '+faststart',  # Enable fast start for web playback
                str(output_path)
            ]
            
            logger.debug(f"📹 ReelForge: FFmpeg command: {' '.join(ffmpeg_cmd[:8])}...")
            
            # Start FFmpeg process
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self._active_captures[post_id] = process
            
            # Wait for completion
            stdout, stderr = await process.communicate()
            
            # Check result
            if process.returncode == 0 and output_path.exists():
                logger.info(f"📹 ReelForge: Capture complete for post {post_id}")
                
                # Update database
                post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
                queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
                
                if post:
                    post.source_clip_path = str(output_path)
                    post.capture_completed_at = datetime.utcnow()
                    post.status = "processing"  # Ready for processing pipeline
                
                if queue_item:
                    queue_item.status = "completed"
                    queue_item.completed_at = datetime.utcnow()
                
                db.commit()
                
                # Remove from in-memory queue
                async with self._lock:
                    if key in self._capture_queue:
                        del self._capture_queue[key]
                
                # Trigger processing pipeline
                await self._trigger_processing(post_id, db)
                
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"📹 ReelForge: Capture failed for post {post_id}: {error_msg}")
                
                # Update database with error
                post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
                queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
                
                if post:
                    post.status = "failed"
                    post.error_message = f"Capture failed: {error_msg[:500]}"
                
                if queue_item:
                    queue_item.status = "failed"
                
                db.commit()
                
                # Remove from in-memory queue
                async with self._lock:
                    if key in self._capture_queue:
                        del self._capture_queue[key]
        
        except Exception as e:
            logger.error(f"📹 ReelForge: Capture exception for post {post_id}: {e}")
            
            # Update database with error
            try:
                post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
                if post:
                    post.status = "failed"
                    post.error_message = str(e)[:500]
                    db.commit()
            except:
                pass
        
        finally:
            # Clean up
            if post_id in self._active_captures:
                del self._active_captures[post_id]
            db.close()
    
    async def _trigger_processing(self, post_id: int, db: Session):
        """Trigger the processing pipeline for a captured clip"""
        # Import here to avoid circular imports
        try:
            from services.reelforge_processor import get_reelforge_processor
            processor = get_reelforge_processor()
            asyncio.create_task(processor.process_post(post_id))
            logger.info(f"📹 ReelForge: Triggered processing for post {post_id}")
        except ImportError:
            logger.warning(f"📹 ReelForge: Processor not available, post {post_id} ready for manual processing")
        except Exception as e:
            logger.error(f"📹 ReelForge: Failed to trigger processing for post {post_id}: {e}")
    
    def _build_rtsp_url(self, camera: Camera) -> str:
        """Build RTSP URL for camera"""
        password = None
        if camera.password_enc:
            try:
                password = base64.b64decode(camera.password_enc).decode()
            except:
                pass
        
        if camera.username and password:
            return f"rtsp://{camera.username}:{password}@{camera.address}:{camera.port}{camera.stream_path}"
        else:
            return f"rtsp://{camera.address}:{camera.port}{camera.stream_path}"
    
    def get_status(self) -> dict:
        """Get capture service status"""
        return {
            "pending_captures": len(self._capture_queue),
            "active_captures": len(self._active_captures),
            "queue": [
                {
                    "camera_id": key[0],
                    "preset_id": key[1],
                    "post_id": item.post_id
                }
                for key, item in self._capture_queue.items()
            ]
        }


# Global instance
_capture_service: Optional[ReelForgeCaptureService] = None


def get_reelforge_capture_service() -> ReelForgeCaptureService:
    """Get the global ReelForge capture service"""
    global _capture_service
    if _capture_service is None:
        _capture_service = ReelForgeCaptureService()
    return _capture_service


async def init_reelforge_capture_service(db: Session):
    """Initialize the capture service and load pending captures"""
    service = get_reelforge_capture_service()
    await service.load_pending_captures(db)
    return service
