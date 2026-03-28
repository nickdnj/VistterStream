"""
Vertical Renderer — FFmpeg portrait crop + overlay compositing.

Takes a horizontal 1920x1080 clip and produces a vertical 1080x1920 short with:
- Center crop (or motion-centroid offset)
- Text overlay (headline)
- Weather bug overlay
- Location tag
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.shortforge import Clip, Moment

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
RENDERED_DIR = DATA_DIR / "rendered"


async def render_vertical(
    clip_id: int,
    headline: str,
    weather_text: str = "",
    location: str = "Wharfside Marina",
) -> Optional[str]:
    """
    Render a vertical (1080x1920) short from a horizontal clip.

    Applies center crop, headline text overlay, weather bug, and location tag.
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

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = RENDERED_DIR / f"short_{clip_id}_{ts}.mp4"

        # Build FFmpeg filter chain:
        # 1. Center crop 1080x1920 from 1920x1080 (take center 607px horizontal slice, scale up)
        # 2. Text overlays
        #
        # For 16:9 → 9:16 center crop: crop the center portion and scale
        # Source is 1920x1080. For 9:16 output at 1080x1920:
        # Crop width from source = 1080 * (1080/1920) = 607px centered
        # Then scale to 1080x1920

        # Escape text for FFmpeg drawtext
        safe_headline = _escape_ffmpeg_text(headline)
        safe_weather = _escape_ffmpeg_text(weather_text)
        safe_location = _escape_ffmpeg_text(location)

        # Build filter graph
        filters = [
            # Center crop to 9:16 aspect from 16:9 source
            "crop=ih*9/16:ih:(iw-ih*9/16)/2:0",
            # Scale to output resolution
            "scale=1080:1920:flags=lanczos",
        ]

        # Headline text overlay (bottom area, large white text with shadow)
        if safe_headline:
            filters.append(
                f"drawtext=text='{safe_headline}'"
                ":fontsize=48:fontcolor=white:borderw=3:bordercolor=black"
                ":x=(w-text_w)/2:y=h-200"
                ":font=DejaVu Sans"
            )

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

        cmd = [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-vf", filter_chain,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            # Add silent audio track (YouTube requires audio)
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:a", "aac",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info("Rendering vertical short for clip %d", clip_id)
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

        # Update clip record with rendered path
        clip.rendered_path = str(output_path)
        db.commit()
        logger.info("Rendered vertical short: %s", output_path)
        return str(output_path)

    except Exception:
        logger.exception("Error rendering vertical short for clip %d", clip_id)
        return None
    finally:
        db.close()


def _escape_ffmpeg_text(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    if not text:
        return ""
    # FFmpeg drawtext escaping: single quotes, colons, backslashes
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\\\\\''")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text
