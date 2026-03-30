"""
Clip Capture — FFmpeg ring buffer + clip extraction.

Maintains a rolling buffer of 10-second segment files via FFmpeg segment muxer.
When a moment is detected, concatenates segments into a 20-30s clip.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.shortforge import Moment, Clip

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
SEGMENTS_DIR = DATA_DIR / "segments"
CLIPS_DIR = DATA_DIR / "clips"


class ClipCapture:
    """Manages the FFmpeg segment ring buffer and clip extraction."""

    def __init__(self):
        self._running = False
        self._segment_process: Optional[asyncio.subprocess.Process] = None
        self._task: Optional[asyncio.Task] = None
        self._rtsp_url: Optional[str] = None

    async def start(self, rtsp_url: str):
        """Start the segment ring buffer."""
        self._rtsp_url = rtsp_url
        self._running = True
        SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        self._task = asyncio.create_task(self._segment_loop())
        logger.info("ClipCapture ring buffer started")

    async def stop(self):
        """Stop the segment ring buffer."""
        self._running = False
        if self._segment_process:
            self._segment_process.terminate()
            try:
                await asyncio.wait_for(self._segment_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._segment_process.kill()
            self._segment_process = None
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ClipCapture ring buffer stopped")

    async def _segment_loop(self):
        """Run FFmpeg segment muxer in a loop, restart on failure."""
        while self._running:
            try:
                await self._run_segmenter()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Segment muxer crashed, restarting in 5s")
                await asyncio.sleep(5)

    async def _run_segmenter(self):
        """Run FFmpeg to produce rolling 10s segment files."""
        segment_pattern = str(SEGMENTS_DIR / "seg_%04d.ts")

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", self._rtsp_url,
            "-c:v", "copy",
            "-an",  # strip audio for MVP (silent shorts)
            "-f", "segment",
            "-segment_time", "10",
            "-segment_wrap", "6",  # keep 6 segments = 60s rolling buffer
            "-segment_format", "mpegts",
            "-reset_timestamps", "1",
            segment_pattern,
        ]

        logger.info("Starting FFmpeg segmenter: %s", " ".join(cmd[:8]) + " ...")
        self._segment_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await self._segment_process.communicate()
        if self._running:
            logger.warning("FFmpeg segmenter exited: %s", stderr[-500:].decode(errors="replace") if stderr else "no output")

    async def capture_clip(self, moment_id: int, pre_seconds: int = 10, post_seconds: int = 20) -> Optional[int]:
        """
        Capture a clip around a moment by concatenating recent segments.
        Returns the clip ID, or None on failure.
        """
        try:
            # Wait for post-trigger footage to accumulate
            await asyncio.sleep(post_seconds)

            # Find recent segment files sorted by modification time
            segments = sorted(
                SEGMENTS_DIR.glob("seg_*.ts"),
                key=lambda p: p.stat().st_mtime,
            )

            if not segments:
                logger.error("No segment files found for clip capture")
                return await self._mark_moment_failed(moment_id, "No segment files")

            # Take the most recent segments covering pre+post duration
            # Each segment is ~10s, we want ~30s total = 3 segments
            total_seconds = pre_seconds + post_seconds
            num_segments = max(1, total_seconds // 10)
            segments = segments[-num_segments:]

            # Concatenate segments into a single clip
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            clip_path = CLIPS_DIR / f"clip_{moment_id}_{ts}.mp4"
            concat_file = CLIPS_DIR / f"concat_{moment_id}.txt"

            # Write concat file
            with open(concat_file, "w") as f:
                for seg in segments:
                    f.write(f"file '{seg}'\n")

            # Concatenate with FFmpeg
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "copy",
                "-movflags", "+faststart",
                str(clip_path),
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            # Clean up concat file
            concat_file.unlink(missing_ok=True)

            if proc.returncode != 0:
                logger.error("FFmpeg clip extraction failed: %s", stderr[-300:].decode(errors="replace") if stderr else "")
                return await self._mark_moment_failed(moment_id, "FFmpeg clip extraction failed")

            if not clip_path.exists():
                return await self._mark_moment_failed(moment_id, "Output clip file missing")

            # Get clip duration via ffprobe
            duration = await self._get_duration(clip_path)

            # Save clip to database
            db = SessionLocal()
            try:
                clip = Clip(
                    moment_id=moment_id,
                    file_path=str(clip_path),
                    duration_seconds=duration,
                    width=1920,
                    height=1080,
                )
                db.add(clip)
                # Update moment status
                moment = db.query(Moment).filter(Moment.id == moment_id).first()
                if moment:
                    moment.status = "captured"
                db.commit()
                db.refresh(clip)
                logger.info("Clip captured: id=%d path=%s duration=%.1fs", clip.id, clip_path, duration or 0)
                return clip.id
            finally:
                db.close()

        except Exception:
            logger.exception("Error capturing clip for moment %d", moment_id)
            return await self._mark_moment_failed(moment_id, "Clip capture exception")

    async def _get_duration(self, path: Path) -> Optional[float]:
        """Get video duration via ffprobe."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await proc.communicate()
            import json
            data = json.loads(stdout)
            return float(data.get("format", {}).get("duration", 0))
        except Exception:
            return None

    async def capture_from_snapshot(self, moment_id: int, snapshot_url: str, duration: int = 15) -> Optional[int]:
        """
        Create a video clip from an HTTP snapshot (no RTSP/RTMP needed).
        Generates a 15s video from a single still image using FFmpeg loop.
        Returns the clip ID, or None on failure.
        """
        try:
            CLIPS_DIR.mkdir(parents=True, exist_ok=True)

            # Download snapshot
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(snapshot_url)
                if resp.status_code != 200:
                    return await self._mark_moment_failed(moment_id, f"Snapshot HTTP {resp.status_code}")

            snap_path = CLIPS_DIR / f"snap_{moment_id}.jpg"
            snap_path.write_bytes(resp.content)

            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            clip_path = CLIPS_DIR / f"clip_{moment_id}_{ts}.mp4"

            # Create video from still image (FFmpeg loop)
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", str(snap_path),
                "-t", str(duration),
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", "15",
                "-preset", "fast",
                str(clip_path),
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            # Clean up snapshot
            snap_path.unlink(missing_ok=True)

            if proc.returncode != 0 or not clip_path.exists():
                error = stderr[-300:].decode(errors="replace") if stderr else ""
                return await self._mark_moment_failed(moment_id, f"Snapshot video failed: {error}")

            db = SessionLocal()
            try:
                clip = Clip(
                    moment_id=moment_id,
                    file_path=str(clip_path),
                    duration_seconds=float(duration),
                    width=1920,
                    height=1080,
                )
                db.add(clip)
                moment = db.query(Moment).filter(Moment.id == moment_id).first()
                if moment:
                    moment.status = "captured"
                db.commit()
                db.refresh(clip)
                logger.info("Snapshot clip created: id=%d duration=%ds", clip.id, duration)
                return clip.id
            finally:
                db.close()

        except Exception:
            logger.exception("Error creating snapshot clip for moment %d", moment_id)
            return await self._mark_moment_failed(moment_id, "Snapshot clip exception")

    async def capture_direct(self, moment_id: int, rtsp_url: str, duration: int = 25) -> Optional[int]:
        """
        Capture a clean clip directly from the RTSP stream for a fixed duration.
        Called by the timeline executor while the preset is locked.
        Returns the clip ID, or None on failure.
        """
        try:
            CLIPS_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            clip_path = CLIPS_DIR / f"clip_{moment_id}_{ts}.mp4"

            cmd = [
                "ffmpeg", "-y",
                "-i", rtsp_url,
                "-t", str(duration),
                "-c:v", "copy",
                "-an",
                "-movflags", "+faststart",
                str(clip_path),
            ]

            logger.info("Direct capture: %ds from RTSP for moment %d", duration, moment_id)
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                error = stderr[-300:].decode(errors="replace") if stderr else ""
                logger.error("Direct capture failed for moment %d: %s", moment_id, error)
                return await self._mark_moment_failed(moment_id, "Direct capture failed")

            if not clip_path.exists():
                return await self._mark_moment_failed(moment_id, "Output clip missing")

            clip_duration = await self._get_duration(clip_path)

            db = SessionLocal()
            try:
                clip = Clip(
                    moment_id=moment_id,
                    file_path=str(clip_path),
                    duration_seconds=clip_duration,
                    width=1920,
                    height=1080,
                )
                db.add(clip)
                moment = db.query(Moment).filter(Moment.id == moment_id).first()
                if moment:
                    moment.status = "captured"
                db.commit()
                db.refresh(clip)
                logger.info("Direct clip captured: id=%d path=%s duration=%.1fs", clip.id, clip_path, clip_duration or 0)
                return clip.id
            finally:
                db.close()

        except Exception:
            logger.exception("Error in direct capture for moment %d", moment_id)
            return await self._mark_moment_failed(moment_id, "Direct capture exception")

    async def _mark_moment_failed(self, moment_id: int, error: str) -> None:
        """Mark a moment as failed."""
        db = SessionLocal()
        try:
            moment = db.query(Moment).filter(Moment.id == moment_id).first()
            if moment:
                moment.status = "failed"
                moment.error_message = error
                db.commit()
        finally:
            db.close()
        return None


# Singleton
_capture: Optional[ClipCapture] = None


def get_clip_capture() -> ClipCapture:
    global _capture
    if _capture is None:
        _capture = ClipCapture()
    return _capture
