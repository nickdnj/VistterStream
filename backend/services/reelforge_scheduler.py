"""
ReelForge Scheduler Service

Handles scheduled captures and auto-publishing of ReelForge posts.
Runs as a background task checking for due items.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from models.database import SessionLocal, Settings, ReelForgeSettings
from models.reelforge import ReelPost, ReelCaptureQueue

logger = logging.getLogger(__name__)


class ReelForgeScheduler:
    """
    Background scheduler for ReelForge
    
    Responsibilities:
    1. Check for posts with scheduled_capture_at in the past
    2. Trigger capture for due scheduled items
    3. Auto-publish ready posts that have auto_publish enabled
    4. Handle recurring schedules
    """
    
    def __init__(self, check_interval: int = 60):
        """
        Initialize the scheduler
        
        Args:
            check_interval: Seconds between scheduler checks
        """
        self.check_interval = check_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    def _get_timezone(self) -> ZoneInfo:
        """Get configured timezone from settings"""
        try:
            db = SessionLocal()
            try:
                settings = db.query(Settings).first()
                if settings and settings.timezone:
                    return ZoneInfo(settings.timezone)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not get timezone: {e}")
        return ZoneInfo("America/New_York")
    
    async def start(self):
        """Start the scheduler"""
        logger.info("🗓️ ReelForge Scheduler starting...")
        self.running = True
        
        while self.running:
            try:
                await self._check_scheduled_captures()
                await self._check_auto_publish()
                await self._check_recurring_schedules()
            except Exception as e:
                logger.error(f"🗓️ Scheduler error: {e}", exc_info=True)
            
            await asyncio.sleep(self.check_interval)
        
        logger.info("🗓️ ReelForge Scheduler stopped")
    
    async def _check_scheduled_captures(self):
        """Check for posts with scheduled_capture_at that are due"""
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            
            # Find posts that are scheduled and due
            due_posts = db.query(ReelPost).filter(
                ReelPost.scheduled_capture_at <= now,
                ReelPost.status == "queued",
                ReelPost.scheduled_capture_at.isnot(None)
            ).all()
            
            for post in due_posts:
                logger.info(f"🗓️ Triggering scheduled capture for post {post.id}")
                
                # Check if already queued
                existing_queue = db.query(ReelCaptureQueue).filter(
                    ReelCaptureQueue.post_id == post.id,
                    ReelCaptureQueue.status.in_(["waiting", "capturing"])
                ).first()
                
                if existing_queue:
                    logger.debug(f"🗓️ Post {post.id} already in queue")
                    continue
                
                # Create queue item with high priority
                queue_item = ReelCaptureQueue(
                    post_id=post.id,
                    camera_id=post.camera_id,
                    preset_id=post.preset_id,
                    trigger_mode="scheduled",
                    scheduled_at=post.scheduled_capture_at,
                    status="waiting",
                    priority=100  # High priority for scheduled
                )
                db.add(queue_item)
                
                # Clear the scheduled time so it doesn't trigger again
                post.scheduled_capture_at = None
                
                db.commit()
                logger.info(f"🗓️ Created queue item for scheduled post {post.id}")
                
        except Exception as e:
            logger.error(f"🗓️ Error checking scheduled captures: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _check_auto_publish(self):
        """Check for ready posts that should be auto-published"""
        db = SessionLocal()
        try:
            # Find posts that are ready and have auto_publish enabled
            posts_to_publish = db.query(ReelPost).filter(
                ReelPost.status == "ready",
                ReelPost.auto_publish == True,
                ReelPost.published_at.is_(None)
            ).all()
            
            for post in posts_to_publish:
                logger.info(f"🗓️ Auto-publishing post {post.id} to {post.publish_platform}")
                
                try:
                    await self._publish_post(post, db)
                except Exception as e:
                    logger.error(f"🗓️ Failed to auto-publish post {post.id}: {e}")
                
        except Exception as e:
            logger.error(f"🗓️ Error checking auto-publish: {e}")
        finally:
            db.close()
    
    async def _publish_post(self, post: ReelPost, db: Session):
        """Publish a post to its configured platform"""
        if post.publish_platform == "youtube_shorts":
            settings = db.query(ReelForgeSettings).first()
            if not settings or not settings.youtube_connected:
                logger.warning(f"🗓️ YouTube not connected, skipping post {post.id}")
                return
            
            from services.youtube_shorts_service import get_youtube_service
            import base64
            
            service = get_youtube_service()
            
            # Decrypt credentials
            client_secret = base64.b64decode(settings.youtube_client_secret_enc.encode()).decode()
            refresh_token = base64.b64decode(settings.youtube_refresh_token_enc.encode()).decode()
            
            # Parse tags
            tags = []
            if post.publish_tags:
                tags = [t.strip().lstrip('#') for t in post.publish_tags.split(',')]
            
            # Get title
            title = post.publish_title
            if not title and post.generated_headlines:
                title = post.generated_headlines[0].get('text', 'Video')
            title = title or 'Video'
            
            result = await service.upload_short(
                video_path=post.output_path,
                title=title,
                description=post.publish_description or '',
                tags=tags,
                client_id=settings.youtube_client_id,
                client_secret=client_secret,
                refresh_token=refresh_token
            )
            
            if result.get("success"):
                post.published_at = datetime.utcnow()
                post.published_url = result.get("url")
                post.status = "published"
                db.commit()
                logger.info(f"🗓️ Published post {post.id} to YouTube: {result.get('url')}")
            else:
                logger.error(f"🗓️ Failed to publish: {result.get('error')}")
        else:
            logger.warning(f"🗓️ Platform {post.publish_platform} not supported for auto-publish")
    
    async def _check_recurring_schedules(self):
        """Check for posts with recurring schedules that are due"""
        db = SessionLocal()
        try:
            tz = self._get_timezone()
            now = datetime.now(tz)
            current_day = now.weekday()  # 0=Monday, 6=Sunday
            # Convert to our format where 0=Sunday
            current_day = (current_day + 1) % 7
            current_time = now.strftime("%H:%M")
            
            # Find posts with recurring schedules
            posts_with_recurring = db.query(ReelPost).filter(
                ReelPost.recurring_schedule.isnot(None),
                ReelPost.status.in_(["queued", "ready", "published"])  # Can recur
            ).all()
            
            for post in posts_with_recurring:
                schedule = post.recurring_schedule
                if not schedule or not schedule.get("enabled"):
                    continue
                
                days = schedule.get("days", [])
                times = schedule.get("times", [])
                
                if current_day not in days:
                    continue
                
                # Check if current time matches any scheduled time (within 1 minute)
                for scheduled_time in times:
                    if self._time_matches(current_time, scheduled_time):
                        logger.info(f"🗓️ Recurring schedule triggered for post {post.id}")
                        
                        # Check if already queued in last 5 minutes
                        five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
                        recent_queue = db.query(ReelCaptureQueue).filter(
                            ReelCaptureQueue.post_id == post.id,
                            ReelCaptureQueue.created_at >= five_mins_ago
                        ).first()
                        
                        if recent_queue:
                            logger.debug(f"🗓️ Post {post.id} already queued recently")
                            continue
                        
                        # Create new queue item
                        queue_item = ReelCaptureQueue(
                            post_id=post.id,
                            camera_id=post.camera_id,
                            preset_id=post.preset_id,
                            trigger_mode="scheduled",
                            status="waiting",
                            priority=50
                        )
                        db.add(queue_item)
                        db.commit()
                        logger.info(f"🗓️ Created queue item for recurring post {post.id}")
                        break
            
        except Exception as e:
            logger.error(f"🗓️ Error checking recurring schedules: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _time_matches(self, current: str, scheduled: str) -> bool:
        """Check if current time matches scheduled time (within 1 minute)"""
        try:
            current_parts = current.split(":")
            scheduled_parts = scheduled.split(":")
            
            current_mins = int(current_parts[0]) * 60 + int(current_parts[1])
            scheduled_mins = int(scheduled_parts[0]) * 60 + int(scheduled_parts[1])
            
            return abs(current_mins - scheduled_mins) <= 1
        except:
            return False
    
    def stop(self):
        """Stop the scheduler"""
        logger.info("🗓️ Stopping ReelForge Scheduler...")
        self.running = False


# Global instance
_scheduler: Optional[ReelForgeScheduler] = None


def get_reelforge_scheduler() -> ReelForgeScheduler:
    """Get the global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReelForgeScheduler()
    return _scheduler


async def start_reelforge_scheduler():
    """Start the global scheduler"""
    scheduler = get_reelforge_scheduler()
    await scheduler.start()
