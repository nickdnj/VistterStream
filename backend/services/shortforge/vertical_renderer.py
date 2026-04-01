"""
Vertical Renderer — FFmpeg portrait crop with horizontal pan + overlay compositing.

Takes a horizontal 1920x1080 clip and produces a vertical 1080x1920 short with:
- Slow horizontal pan across the full 16:9 source (Ken Burns style)
- TikTok-style word-by-word text overlay (synced to narration)
- Weather bug overlay
- Location tag
- Narration audio track
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.database import SessionLocal
from models.shortforge import Clip

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
RENDERED_DIR = DATA_DIR / "rendered"


async def render_vertical(
    clip_id: int,
    headline: str,
    weather_text: str = "",
    location: str = "Wharfside Marina",
    audio_path: Optional[str] = None,
    word_overlay_filter: Optional[str] = None,
) -> Optional[str]:
    """
    Render a vertical (1080x1920) short from a horizontal clip.

    Applies a slow horizontal pan across the 16:9 source, viewed through
    a 9:16 portrait window. Adds word-by-word text overlay, weather, location,
    and narration audio.

    Returns the path to the rendered file, or None on failure.
    """
    RENDERED_DIR.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            logger.error("Clip %d not found", clip_id)
            return None

        input_path = clip.file_path
        if not Path(input_path).exists():
            logger.error("Clip file missing: %s", input_path)
            return None

        clip_duration = clip.duration_seconds or 25.0
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = RENDERED_DIR / f"short_{clip_id}_{ts}.mp4"

        # Get audio duration — this is the master duration for the short.
        # The pan effect, overlays, and output all match the narration length.
        audio_duration = None
        if audio_path and Path(audio_path).exists():
            audio_duration = await _get_duration(audio_path)
        render_duration = audio_duration or clip_duration
        logger.info("Render durations: clip=%.1fs, audio=%.1fs, render=%.1fs",
                     clip_duration, audio_duration or 0, render_duration)

        # Escape text for FFmpeg drawtext
        safe_weather = _escape_ffmpeg_text(weather_text)
        safe_location = _escape_ffmpeg_text(location)

        # Build filter graph with horizontal pan effect
        pan_range = 1313  # 1920 - 607

        filters = [
            # Animated horizontal pan: crop window slides left-to-right
            # Speed based on render_duration (audio length) not clip length
            f"crop=ih*9/16:ih:'min({pan_range},({pan_range})*t/{render_duration:.1f})':0",
            # Scale to output resolution
            "scale=1080:1920:flags=lanczos",
        ]

        # TikTok-style word-by-word overlay (synced to narration)
        if word_overlay_filter:
            filters.append(word_overlay_filter)

        # Weather bug (top-right)
        if safe_weather:
            filters.append(
                f"drawtext=text='{safe_weather}'"
                ":fontsize=32:fontcolor=white:borderw=2:bordercolor=black"
                ":x=w-text_w-40:y=60"
                ":font=DejaVu Sans"
            )

        # Location tag (bottom-left, smaller)
        if safe_location:
            filters.append(
                f"drawtext=text='{safe_location}'"
                ":fontsize=28:fontcolor=white@0.8:borderw=2:bordercolor=black@0.5"
                ":x=40:y=h-120"
                ":font=DejaVu Sans"
            )

        filter_chain = ",".join(filters)

        # Build FFmpeg command
        # If clip is shorter than audio, loop the video input
        cmd = ["ffmpeg", "-y"]
        if clip_duration < render_duration:
            cmd.extend(["-stream_loop", "-1"])  # loop video indefinitely
        cmd.extend(["-i", str(input_path)])

        # Add audio input: narration file or silent track
        if audio_path and Path(audio_path).exists():
            cmd.extend(["-i", audio_path])
            audio_map = "1:a:0"
        else:
            cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])
            audio_map = "1:a:0"

        cmd.extend([
            "-vf", filter_chain,
            "-map", "0:v:0", "-map", audio_map,
            "-t", f"{render_duration:.1f}",  # explicit duration from audio
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(output_path),
        ])

        logger.info("Rendering vertical short for clip %d (pan over %.1fs, audio=%s)",
                     clip_id, render_duration, "narration" if audio_path else "silent")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr[-500:].decode(errors="replace") if stderr else "unknown"
            logger.error("FFmpeg render failed for clip %d: %s", clip_id, error)
            return None

        if not output_path.exists():
            logger.error("Rendered file missing after FFmpeg: %s", output_path)
            return None

        clip.rendered_path = str(output_path)
        db.commit()
        logger.info("Rendered vertical short: %s", output_path)
        return str(output_path)

    except Exception:
        logger.exception("Error rendering vertical short for clip %d", clip_id)
        return None
    finally:
        db.close()


async def _get_duration(path) -> Optional[float]:
    """Get media duration via ffprobe."""
    try:
        import json
        proc = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        return float(data.get("format", {}).get("duration", 0))
    except Exception:
        return None


def _escape_ffmpeg_text(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\\\\\''")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text
