"""
ShortForge Scheduler — orchestrates the full pipeline and manages posting cadence.

Responsibilities:
- Watches for new detected moments and triggers the pipeline
- Enforces posting frequency caps and quiet hours
- Manages disk cleanup (retention policies)
- Triggers view count refresh
"""

import asyncio
import logging
from datetime import datetime, timezone, time as dtime
from pathlib import Path
from typing import Optional

from models.database import SessionLocal
from models.shortforge import Moment, Clip, PublishedShort, ShortForgeConfig
from services.shortforge.clip_capture import get_clip_capture
from services.shortforge.headline_generator import generate_headline, fetch_weather_data
from services.shortforge.vertical_renderer import render_vertical
from services.shortforge.publisher import publish_short, refresh_view_counts
from services.shortforge.moment_detector import get_moment_detector
from utils.crypto import decrypt
from utils.rtsp import build_rtsp_url

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")


class ShortForgeScheduler:
    """Orchestrates the ShortForge pipeline."""

    def __init__(self):
        self._running = False
        self._pipeline_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._views_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler and all pipeline components."""
        self._running = True

        db = SessionLocal()
        try:
            config = db.query(ShortForgeConfig).first()
            if not config:
                # Create default config
                config = ShortForgeConfig()
                db.add(config)
                db.commit()
                db.refresh(config)
                logger.info("Created default ShortForge config")

            if not config.enabled:
                logger.info("ShortForge is disabled, scheduler standing by")
                self._pipeline_task = asyncio.create_task(self._standby_loop())
                return

            if not config.camera_id:
                logger.warning("ShortForge enabled but no camera configured")
                self._pipeline_task = asyncio.create_task(self._standby_loop())
                return

            # Build RTSP URL from camera
            from models.database import Camera
            camera = db.query(Camera).filter(Camera.id == config.camera_id).first()
            if not camera:
                logger.error("ShortForge camera_id=%d not found", config.camera_id)
                self._pipeline_task = asyncio.create_task(self._standby_loop())
                return

            rtsp_url = self._build_rtsp_url(camera)

        finally:
            db.close()

        # Start pipeline components
        detector = get_moment_detector()
        capture = get_clip_capture()

        await detector.start(rtsp_url, config)
        await capture.start(rtsp_url)

        # Start pipeline processor (watches for new moments)
        self._pipeline_task = asyncio.create_task(self._pipeline_loop())

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Start view count refresh task
        self._views_task = asyncio.create_task(self._views_refresh_loop())

        logger.info("ShortForge scheduler started (camera=%d)", config.camera_id)

    async def stop(self):
        """Stop all pipeline components."""
        self._running = False

        detector = get_moment_detector()
        capture = get_clip_capture()

        await detector.stop()
        await capture.stop()

        for task in [self._pipeline_task, self._cleanup_task, self._views_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        logger.info("ShortForge scheduler stopped")

    def _build_rtsp_url(self, camera) -> str:
        """Build RTSP URL from a Camera object, decrypting the password."""
        password = None
        if camera.password_enc:
            try:
                password = decrypt(camera.password_enc)
            except Exception:
                pass
        return build_rtsp_url(camera.address, camera.port, camera.username, password, camera.stream_path)

    async def _standby_loop(self):
        """Wait for config to become enabled, then restart."""
        while self._running:
            try:
                await asyncio.sleep(10)
                db = SessionLocal()
                try:
                    config = db.query(ShortForgeConfig).first()
                    if config and config.enabled and config.camera_id:
                        logger.info("ShortForge config enabled, starting pipeline")
                        # Restart with full pipeline
                        await self.stop()
                        await self.start()
                        return
                finally:
                    db.close()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in standby loop")
                await asyncio.sleep(30)

    async def _pipeline_loop(self):
        """Watch for new detected moments and process them through the pipeline."""
        while self._running:
            try:
                db = SessionLocal()
                try:
                    config = db.query(ShortForgeConfig).first()
                    if not config or not config.enabled:
                        await asyncio.sleep(10)
                        continue

                    # Find unprocessed moments
                    moment = (
                        db.query(Moment)
                        .filter(Moment.status == "detected")
                        .order_by(Moment.timestamp.asc())
                        .first()
                    )

                    if not moment:
                        await asyncio.sleep(5)
                        continue

                    # Check posting limits
                    if not self._can_publish(db, config):
                        moment.status = "skipped"
                        moment.error_message = "Posting limit reached or quiet hours"
                        db.commit()
                        logger.info("Moment %d skipped (posting limits)", moment.id)
                        await asyncio.sleep(5)
                        continue

                    moment_id = moment.id
                    frame_path = moment.frame_path
                finally:
                    db.close()

                # Process through pipeline stages
                await self._process_moment(moment_id, frame_path, config)
                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in pipeline loop")
                await asyncio.sleep(10)

    async def _process_moment(self, moment_id: int, frame_path: Optional[str], config: ShortForgeConfig):
        """Run a moment through the full pipeline: capture → headline → render → publish."""
        try:
            # Stage 1: Capture clip
            capture = get_clip_capture()
            clip_id = await capture.capture_clip(moment_id)
            if not clip_id:
                return

            # Stage 2: Generate headline
            weather = await fetch_weather_data()
            headline_result = await generate_headline(
                frame_path or "",
                config,
                weather_data=weather,
            )

            headline = headline_result["headline"]
            safe = headline_result["safe_to_publish"]

            # Update clip with headline and safety
            db = SessionLocal()
            try:
                clip = db.query(Clip).filter(Clip.id == clip_id).first()
                if clip:
                    clip.headline = headline
                    clip.safe_to_publish = safe
                    db.commit()
            finally:
                db.close()

            # Safety gate
            if config.safety_gate_enabled and not safe:
                db = SessionLocal()
                try:
                    moment = db.query(Moment).filter(Moment.id == moment_id).first()
                    if moment:
                        moment.status = "skipped"
                        moment.error_message = "Content safety: flagged by AI"
                    db.commit()
                finally:
                    db.close()
                logger.info("Moment %d blocked by safety gate", moment_id)
                return

            # Stage 3: Render vertical
            weather_text = ""
            if weather:
                temp = weather.get("temperature", "")
                conditions = weather.get("conditions", "")
                if temp:
                    weather_text = f"{temp}°F {conditions}".strip()

            rendered_path = await render_vertical(clip_id, headline, weather_text)
            if not rendered_path:
                db = SessionLocal()
                try:
                    moment = db.query(Moment).filter(Moment.id == moment_id).first()
                    if moment:
                        moment.status = "failed"
                        moment.error_message = "Render failed"
                    db.commit()
                finally:
                    db.close()
                return

            # Update moment status
            db = SessionLocal()
            try:
                moment = db.query(Moment).filter(Moment.id == moment_id).first()
                if moment:
                    moment.status = "rendered"
                db.commit()
            finally:
                db.close()

            # Stage 4: Publish to YouTube
            await publish_short(clip_id, config)

        except Exception:
            logger.exception("Pipeline failed for moment %d", moment_id)

    def _can_publish(self, db, config: ShortForgeConfig) -> bool:
        """Check if we can publish right now (quota + quiet hours)."""
        now = datetime.now(timezone.utc)

        # Check daily quota
        from sqlalchemy import func
        today_count = (
            db.query(func.count(PublishedShort.id))
            .filter(
                PublishedShort.status == "published",
                func.date(PublishedShort.published_at) == now.date(),
            )
            .scalar()
        )
        if today_count >= (config.max_shorts_per_day or 6):
            return False

        # Check quiet hours (local time)
        try:
            local_hour = now.hour  # simplified — should use configured timezone
            quiet_start = int((config.quiet_hours_start or "22:00").split(":")[0])
            quiet_end = int((config.quiet_hours_end or "06:00").split(":")[0])

            if quiet_start > quiet_end:
                # Crosses midnight (e.g., 22:00-06:00)
                if local_hour >= quiet_start or local_hour < quiet_end:
                    return False
            else:
                if quiet_start <= local_hour < quiet_end:
                    return False
        except ValueError:
            pass  # invalid format, skip quiet hours check

        # Check minimum posting interval
        last_short = (
            db.query(PublishedShort)
            .filter(PublishedShort.status == "published")
            .order_by(PublishedShort.published_at.desc())
            .first()
        )
        if last_short and last_short.published_at:
            elapsed = (now - last_short.published_at).total_seconds()
            min_interval = (config.min_posting_interval_minutes or 60) * 60
            if elapsed < min_interval:
                return False

        return True

    async def _cleanup_loop(self):
        """Periodic disk cleanup based on retention policies."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # run every hour

                db = SessionLocal()
                try:
                    config = db.query(ShortForgeConfig).first()
                    if not config:
                        continue
                finally:
                    db.close()

                # Clean snapshots
                await self._cleanup_dir(
                    DATA_DIR / "snapshots",
                    config.snapshot_retention_days or 3,
                )
                # Clean raw clips
                await self._cleanup_dir(
                    DATA_DIR / "clips",
                    config.raw_clip_retention_days or 7,
                )
                # Clean rendered clips
                await self._cleanup_dir(
                    DATA_DIR / "rendered",
                    config.rendered_clip_retention_days or 30,
                )

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in cleanup loop")
                await asyncio.sleep(3600)

    async def _cleanup_dir(self, directory: Path, retention_days: int):
        """Delete files older than retention_days in a directory."""
        if not directory.exists():
            return
        import time
        cutoff = time.time() - (retention_days * 86400)
        count = 0
        for f in directory.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                count += 1
        if count:
            logger.info("Cleaned %d files from %s (retention: %dd)", count, directory, retention_days)

    async def _views_refresh_loop(self):
        """Refresh YouTube view counts every 15 minutes."""
        while self._running:
            try:
                await asyncio.sleep(900)  # 15 minutes
                await refresh_view_counts()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error refreshing view counts")
                await asyncio.sleep(900)


# Singleton
_scheduler: Optional[ShortForgeScheduler] = None


def get_shortforge_scheduler() -> ShortForgeScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ShortForgeScheduler()
    return _scheduler
