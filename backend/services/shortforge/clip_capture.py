"""
Clip Capture — per-preset video clips captured during timeline segments.

Simple architecture:
- Timeline executor calls capture_for_preset() synchronously during each segment
  while the camera is guaranteed to be at that preset
- Clips are stored in preset_clips dict, one per preset, overwritten each loop
- When a short is triggered, create_clip_for_moment() copies the preset clip
- No background tasks, no ring buffers, no timing races
"""

import asyncio
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.database import SessionLocal
from models.shortforge import Moment, Clip

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
CLIPS_DIR = DATA_DIR / "clips"


class ClipCapture:
    """Per-preset clip capture. One clip per preset, updated each timeline loop."""

    def __init__(self):
        # preset_id → absolute path to clip file
        self.preset_clips: dict[int, str] = {}

    async def capture_for_preset(self, preset_id: int, relay_url: str, duration: int = 10):
        """
        Capture a clip from the RTMP relay for this preset.
        Called SYNCHRONOUSLY (awaited) by the timeline executor during the segment,
        so the camera is guaranteed to be at this preset.
        """
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        clip_path = CLIPS_DIR / f"preset_{preset_id}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-i", relay_url,
            "-t", str(duration),
            "-c:v", "copy",
            "-an",
            "-movflags", "+faststart",
            str(clip_path),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=duration + 10)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.warning("Preset %d clip capture timed out after %ds", preset_id, duration + 10)
                return

            if proc.returncode == 0 and clip_path.exists():
                self.preset_clips[preset_id] = str(clip_path)
                logger.info("Preset %d clip captured (%ds): %s", preset_id, duration, clip_path)
            else:
                error = stderr[-200:].decode(errors="replace") if stderr else ""
                logger.warning("Preset %d clip capture failed: %s", preset_id, error)
        except Exception:
            logger.exception("Error capturing clip for preset %d", preset_id)

    async def create_clip_for_moment(self, moment_id: int, preset_id: int) -> Optional[int]:
        """
        Create a DB Clip record from the preset clip.
        Copies the file so the preset clip can be overwritten next loop.
        Returns clip ID or None.
        """
        src = self.preset_clips.get(preset_id)
        if not src or not Path(src).exists():
            logger.warning("No clip available for preset %d", preset_id)
            return None

        try:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            dest = CLIPS_DIR / f"clip_{moment_id}_{ts}.mp4"
            shutil.copy2(src, dest)

            duration = await self._get_duration(dest)

            db = SessionLocal()
            try:
                clip = Clip(
                    moment_id=moment_id,
                    file_path=str(dest),
                    duration_seconds=duration,
                    width=1920,
                    height=1080,
                )
                db.add(clip)
                moment = db.query(Moment).filter(Moment.id == moment_id).first()
                if moment:
                    moment.status = "captured"
                db.commit()
                db.refresh(clip)
                logger.info("Clip for moment %d from preset %d: id=%d (%.1fs)",
                            moment_id, preset_id, clip.id, duration or 0)
                return clip.id
            finally:
                db.close()
        except Exception:
            logger.exception("Error creating clip for moment %d from preset %d", moment_id, preset_id)
            return None

    async def create_clip_from_snapshot(self, moment_id: int, image_path: str, duration: int = 15) -> Optional[int]:
        """Last-resort fallback: create a video from a still image."""
        CLIPS_DIR.mkdir(parents=True, exist_ok=True)
        if not Path(image_path).exists():
            return None

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clip_path = CLIPS_DIR / f"clip_{moment_id}_{ts}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-t", str(duration),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "15", "-preset", "fast",
            str(clip_path),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0 or not clip_path.exists():
                logger.warning("Snapshot clip failed for moment %d", moment_id)
                return None

            db = SessionLocal()
            try:
                clip = Clip(
                    moment_id=moment_id,
                    file_path=str(clip_path),
                    duration_seconds=float(duration),
                    width=1920, height=1080,
                )
                db.add(clip)
                moment = db.query(Moment).filter(Moment.id == moment_id).first()
                if moment:
                    moment.status = "captured"
                db.commit()
                db.refresh(clip)
                logger.info("Snapshot fallback clip for moment %d: id=%d", moment_id, clip.id)
                return clip.id
            finally:
                db.close()
        except Exception:
            logger.exception("Snapshot clip error for moment %d", moment_id)
            return None

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


# Singleton
_capture: Optional[ClipCapture] = None


def get_clip_capture() -> ClipCapture:
    global _capture
    if _capture is None:
        _capture = ClipCapture()
    return _capture
