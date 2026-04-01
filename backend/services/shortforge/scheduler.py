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
from datetime import datetime, timezone
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
        self._rtsp_url: Optional[str] = None
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

            # Get camera for clip capture RTSP URL
            from models.database import Camera
            camera = db.query(Camera).filter(Camera.id == config.camera_id).first()
            if not camera:
                logger.error("ShortForge camera_id=%d not found", config.camera_id)
                self._pipeline_task = asyncio.create_task(self._standby_loop())
                return

            # Build RTSP URL for clip capture ring buffer
            rtsp_url = self._build_rtsp_url(camera)

        finally:
            db.close()

        # Store RTSP URL for on-demand direct capture (no background ring buffer).
        # The ring buffer ran a continuous FFmpeg process 24/7 which added ~10-20% CPU
        # on the N100 even when no captures were possible (nighttime).
        self._rtsp_url = rtsp_url

        # Moment detection is now driven by the timeline executor (per-preset).
        # The scheduler just runs the pipeline processor and housekeeping.

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
        await detector.close()

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

    def _build_snapshot_url(self, camera) -> Optional[str]:
        """Build snapshot URL from a Camera object, injecting decrypted credentials."""
        if not camera.snapshot_url:
            return None
        snapshot_url = camera.snapshot_url
        # If the snapshot URL already has credentials embedded, use as-is
        if "user=" in snapshot_url or "@" in snapshot_url:
            # Decrypt password and substitute if needed
            if camera.password_enc and "password=" in snapshot_url:
                try:
                    password = decrypt(camera.password_enc)
                    # URL might have a placeholder or the encrypted value
                    # The snapshot_url in the DB should already have the correct creds
                except Exception:
                    pass
            return snapshot_url
        return snapshot_url

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
        """Check for completed capture windows and process best candidates."""
        last_window: Optional[str] = None

        while self._running:
            try:
                db = SessionLocal()
                try:
                    config = db.query(ShortForgeConfig).first()
                    if not config or not config.enabled:
                        await asyncio.sleep(10)
                        continue

                    # Get location for window manager
                    from models.database import Settings
                    settings = db.query(Settings).first()
                    lat = settings.latitude if settings and settings.latitude else 40.338
                    lon = settings.longitude if settings and settings.longitude else -73.977
                finally:
                    db.close()

                from services.shortforge.capture_windows import get_capture_window_manager
                wm = get_capture_window_manager(lat, lon)
                current_window = wm.get_current_window()

                # Detect window transition: we were in a window, now we're not (or in a different one)
                if last_window and last_window != current_window:
                    # Previous window ended — capture best candidate
                    candidate = wm.get_best_candidate(last_window)
                    if candidate:
                        logger.info(
                            "Window '%s' ended. Best: preset=%d score=%.3f. Triggering capture.",
                            last_window, candidate["preset_id"], candidate["score"],
                        )

                        # Create moment from best candidate
                        db = SessionLocal()
                        try:
                            moment = Moment(
                                camera_id=config.camera_id,
                                preset_id=candidate.get("preset_id"),
                                timestamp=datetime.now(timezone.utc),
                                trigger_type="window",
                                score=round(candidate["score"], 3),
                                frame_path=candidate.get("frame_path"),
                                status="detected",
                            )
                            db.add(moment)
                            db.commit()
                            db.refresh(moment)
                            moment_id = moment.id
                            frame_path = candidate.get("frame_path")
                        finally:
                            db.close()

                        wm.mark_captured(last_window)
                        await self._process_moment(moment_id, frame_path, config, preset_id=candidate["preset_id"])
                    else:
                        logger.info("Window '%s' ended with no candidates", last_window)

                last_window = current_window
                await asyncio.sleep(30)  # Check every 30s

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in pipeline loop")
                await asyncio.sleep(10)

    async def _process_moment(self, moment_id: int, frame_path: Optional[str], config: ShortForgeConfig, preset_id: Optional[int] = None):
        """Run a moment through the full pipeline: capture → headline → render → publish."""
        try:
            # Stage 1: Get clip — use the preset clip captured during the timeline segment
            clip_id = None
            capture = get_clip_capture()
            if preset_id:
                clip_id = await capture.create_clip_for_moment(moment_id, preset_id)
            if not clip_id and frame_path and Path(frame_path).exists():
                logger.info("No preset clip for %s, falling back to snapshot", preset_id)
                clip_id = await capture.create_clip_from_snapshot(moment_id, frame_path, duration=15)
            if not clip_id:
                logger.error("No clip available for moment %d — skipping", moment_id)
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

            # Stage 3: Generate narration + TTS
            scene_desc = headline_result.get("scene_description", "")
            audio_path = None
            word_filter = None

            try:
                from services.shortforge.narration import (
                    generate_narration, generate_tts,
                    compute_word_timings, build_word_overlay_filter,
                    mix_narration_with_music,
                )

                narration_result = await generate_narration(scene_desc, config, weather)
                narration_text = narration_result.get("narration", "")
                narration_title = narration_result.get("title", "")

                if narration_text:
                    # Update headline with narration title (better than generic)
                    if narration_title:
                        headline = narration_title

                    # Generate TTS audio
                    raw_audio = await generate_tts(narration_text, clip_id, config)

                    # Mix narration with background music
                    if raw_audio:
                        audio_path = await mix_narration_with_music(raw_audio, clip_id)

                    # Get audio duration for word timing
                    if audio_path:
                        audio_dur = await self._get_audio_duration(audio_path)
                        if audio_dur and audio_dur > 0:
                            timings = compute_word_timings(narration_text, audio_dur)
                            word_filter = build_word_overlay_filter(timings)

                    logger.info("Narration: '%s' (audio=%s)", narration_text[:80], bool(audio_path))
            except Exception:
                logger.exception("Narration generation failed, rendering without narration")

            # Stage 4: Render vertical
            weather_text = ""
            if weather:
                temp = weather.get("temperature", "")
                conditions = weather.get("conditions", "")
                if temp:
                    weather_text = f"{temp}°F {conditions}".strip()

            rendered_path = await render_vertical(
                clip_id, headline, weather_text,
                audio_path=audio_path,
                word_overlay_filter=word_filter,
            )
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

            # Stage 4: Create short record and optionally publish to YouTube
            db = SessionLocal()
            try:
                clip = db.query(Clip).filter(Clip.id == clip_id).first()
                short = PublishedShort(
                    clip_id=clip_id,
                    title=clip.headline if clip else "Marina moment",
                    status="rendered",
                )
                db.add(short)
                db.commit()
                logger.info("Short created: id=%d clip=%d (pending publish)", short.id, clip_id)
            finally:
                db.close()

            # TODO: Wire up YouTube publish using streaming destination OAuth
            # For now, shorts stay in "rendered" status for manual review

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

    async def _get_audio_duration(self, audio_path: str) -> Optional[float]:
        """Get audio duration via ffprobe."""
        try:
            import json as _json
            proc = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", audio_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            data = _json.loads(stdout)
            return float(data.get("format", {}).get("duration", 0))
        except Exception:
            return None

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
