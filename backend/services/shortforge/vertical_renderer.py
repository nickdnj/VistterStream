"""
Vertical Renderer — FFmpeg portrait crop with horizontal pan + overlay compositing.

Takes a horizontal 1920x1080 clip and produces a vertical 1080x1920 short with:
- Slow horizontal pan across the full 16:9 source (Ken Burns style)
- Text overlay (headline)
- Weather bug overlay
- Location tag
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
) -> Optional[str]:
    """
    Render a vertical (1080x1920) short from a horizontal clip.

    Applies a slow horizontal pan across the 16:9 source, viewed through
    a 9:16 portrait window. Adds headline, weather, and location overlays.
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

        # Get clip duration for pan timing
        duration = clip.duration_seconds or 25.0

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = RENDERED_DIR / f"short_{clip_id}_{ts}.mp4"

        # Escape text for FFmpeg drawtext
        safe_headline = _escape_ffmpeg_text(headline)
        safe_weather = _escape_ffmpeg_text(weather_text)
        safe_location = _escape_ffmpeg_text(location)

        # Build filter graph with horizontal pan effect:
        #
        # Source: 1920x1080 (16:9)
        # Output: 1080x1920 (9:16)
        #
        # The 9:16 crop window at source height (1080) is 607px wide.
        # Pan range: 0 to (1920 - 607) = 1313 pixels
        # We animate the crop X position from 0 → 1313 over the clip duration.
        #
        # crop=w:h:x:y where x animates with time: x = (1313) * (t / duration)
        pan_range = 1313  # 1920 - 607

        filters = [
            # Animated horizontal pan: crop window slides left-to-right
            f"crop=ih*9/16:ih:'min({pan_range},({pan_range})*t/{duration:.1f})':0",
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
            # Silent audio track (YouTube requires audio) — must be before output options
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", filter_chain,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

        logger.info("Rendering vertical short for clip %d (pan over %.1fs)", clip_id, duration)
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
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\\\\\''")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text
