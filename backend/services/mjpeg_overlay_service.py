"""
MJPEG Overlay Streaming Service

Manages per-asset MJPEG streams that FFmpeg reads as continuous video inputs.
Polls each asset's source URL on its api_refresh_interval schedule and serves
frames via multipart/x-mixed-replace MJPEG over HTTP.

This eliminates FFmpeg restarts for overlay image refreshes — FFmpeg reads
fresh frames automatically from the MJPEG stream.
"""

import asyncio
import io
import logging
import time
from dataclasses import dataclass, field
from typing import AsyncGenerator, Dict, Optional

import httpx
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

MJPEG_BOUNDARY = "frame"
KEEPALIVE_INTERVAL = 10  # seconds — re-push current frame to prevent FFmpeg timeout


@dataclass
class MjpegStreamState:
    asset_id: int
    api_url: str
    refresh_interval: int  # seconds (from asset.api_refresh_interval)
    asset_type: str  # 'api_image' or 'google_drawing'
    file_path: Optional[str] = None  # for google_drawing URL parsing
    current_frame: Optional[bytes] = None  # latest JPEG bytes
    frame_event: asyncio.Event = field(default_factory=asyncio.Event)
    poll_task: Optional[asyncio.Task] = None
    last_fetch_time: float = 0.0


class MjpegOverlayService:
    """Singleton service managing MJPEG streams for dynamic overlay assets."""

    def __init__(self):
        self._streams: Dict[int, MjpegStreamState] = {}

    async def start_stream(
        self,
        asset_id: int,
        api_url: str,
        refresh_interval: int,
        asset_type: str = "api_image",
        file_path: Optional[str] = None,
    ) -> None:
        """Start an MJPEG stream for an asset. Spawns a background poll task."""
        if asset_id in self._streams:
            logger.info(f"MJPEG stream for asset {asset_id} already running")
            return

        state = MjpegStreamState(
            asset_id=asset_id,
            api_url=api_url,
            refresh_interval=max(refresh_interval, 5),  # floor at 5s
            asset_type=asset_type,
            file_path=file_path,
        )

        # Fetch the first frame synchronously before starting the loop
        await self._fetch_frame(state)

        state.poll_task = asyncio.create_task(
            self._poll_loop(state),
            name=f"mjpeg-poll-{asset_id}",
        )
        self._streams[asset_id] = state
        logger.info(
            f"🎬 Started MJPEG stream for asset {asset_id} "
            f"(type={asset_type}, interval={state.refresh_interval}s)"
        )

    async def stop_stream(self, asset_id: int) -> None:
        """Stop an MJPEG stream and cancel its poll task."""
        state = self._streams.pop(asset_id, None)
        if state and state.poll_task:
            state.poll_task.cancel()
            try:
                await state.poll_task
            except asyncio.CancelledError:
                pass
        if state:
            logger.info(f"🛑 Stopped MJPEG stream for asset {asset_id}")

    async def stop_all(self) -> None:
        """Stop all MJPEG streams (used during shutdown)."""
        asset_ids = list(self._streams.keys())
        for asset_id in asset_ids:
            await self.stop_stream(asset_id)

    def get_current_frame(self, asset_id: int) -> Optional[bytes]:
        """Return the latest JPEG frame for an asset, or None."""
        state = self._streams.get(asset_id)
        if state:
            return state.current_frame
        return None

    def is_streaming(self, asset_id: int) -> bool:
        """Check if an MJPEG stream is active for an asset."""
        return asset_id in self._streams

    async def frame_generator(self, asset_id: int) -> AsyncGenerator[bytes, None]:
        """
        Yield MJPEG multipart frames for an asset.
        Used by the streaming endpoint's StreamingResponse.
        """
        state = self._streams.get(asset_id)
        if not state:
            return

        # Immediately yield current frame (solves FFmpeg startup delay)
        if state.current_frame:
            yield self._format_mjpeg_frame(state.current_frame)

        while asset_id in self._streams:
            # Wait for a new frame or keepalive timeout
            try:
                state.frame_event.clear()
                await asyncio.wait_for(state.frame_event.wait(), timeout=KEEPALIVE_INTERVAL)
            except asyncio.TimeoutError:
                pass

            # Re-check stream is still active
            state = self._streams.get(asset_id)
            if not state:
                break

            frame = state.current_frame
            if frame:
                # Yield frame (even if same content — keepalive for FFmpeg)
                yield self._format_mjpeg_frame(frame)

    async def _poll_loop(self, state: MjpegStreamState) -> None:
        """Background task: periodically fetch fresh images from the asset source."""
        try:
            while True:
                await asyncio.sleep(state.refresh_interval)
                await self._fetch_frame(state)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"MJPEG poll loop crashed for asset {state.asset_id}: {e}")

    async def _fetch_frame(self, state: MjpegStreamState) -> None:
        """Fetch a fresh image from the asset source and store as JPEG."""
        try:
            url = state.api_url

            # For Google Drawings, convert sharing URL to export URL
            if state.asset_type == "google_drawing" and state.file_path:
                from utils.google_drive import parse_google_drawing_url
                export_url = parse_google_drawing_url(state.file_path)
                if export_url:
                    url = export_url
                else:
                    logger.warning(f"Invalid Google Drawing URL for asset {state.asset_id}")
                    return

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

            # Convert to JPEG (FFmpeg MJPEG demuxer expects JPEG frames)
            image_bytes = response.content
            content_type = response.headers.get("content-type", "")

            if "png" in content_type or "webp" in content_type or "gif" in content_type:
                image_bytes = self._convert_to_jpeg(image_bytes)
            elif "jpeg" not in content_type and "jpg" not in content_type:
                # Unknown format — try to convert via Pillow
                image_bytes = self._convert_to_jpeg(image_bytes)

            state.current_frame = image_bytes
            state.last_fetch_time = time.time()
            state.frame_event.set()

        except Exception as e:
            # Keep the old frame alive — don't kill the stream on a single failure
            logger.warning(
                f"⚠️  Failed to fetch frame for asset {state.asset_id}: {e}"
            )

    @staticmethod
    def _convert_to_jpeg(image_bytes: bytes, quality: int = 95) -> bytes:
        """Convert image bytes (PNG/WebP/GIF/etc) to JPEG."""
        img = PILImage.open(io.BytesIO(image_bytes))
        if img.mode in ("RGBA", "LA", "P"):
            # JPEG doesn't support transparency — composite on white background
            bg = PILImage.new("RGB", img.size, (0, 0, 0))
            if img.mode == "P":
                img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    @staticmethod
    def _format_mjpeg_frame(jpeg_bytes: bytes) -> bytes:
        """Format a JPEG frame as an MJPEG multipart chunk."""
        header = (
            f"--{MJPEG_BOUNDARY}\r\n"
            f"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(jpeg_bytes)}\r\n"
            f"\r\n"
        )
        return header.encode() + jpeg_bytes + b"\r\n"


# --- Singleton ---

_mjpeg_service: Optional[MjpegOverlayService] = None


def get_mjpeg_overlay_service() -> MjpegOverlayService:
    """Get the global MJPEG overlay service instance."""
    global _mjpeg_service
    if _mjpeg_service is None:
        _mjpeg_service = MjpegOverlayService()
    return _mjpeg_service
