"""
Moment Detector — lightweight frame analysis using HTTP snapshots.

Grabs a JPEG snapshot from the camera every N seconds (configurable).
Scores frames for motion and brightness changes using OpenCV.
When a threshold is crossed, logs a Moment to the database.

Uses HTTP snapshots instead of RTSP to avoid competing for the camera's
limited RTSP sessions (already used by the timeline executor and RTMP relay).
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import httpx
import numpy as np

from models.database import SessionLocal
from models.shortforge import Moment, ShortForgeConfig

logger = logging.getLogger(__name__)

# Data directory for ShortForge artifacts
DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
SNAPSHOTS_DIR = DATA_DIR / "snapshots"


class MomentDetector:
    """Analyzes camera snapshots for interesting moments using OpenCV."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._prev_frame: Optional[np.ndarray] = None
        self._prev_hist: Optional[np.ndarray] = None
        self._last_moment_time: float = 0
        self._snapshot_url: Optional[str] = None
        self._current_frame: Optional[np.ndarray] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._log_counter: int = 0

    async def start(self, snapshot_url: str, config: ShortForgeConfig):
        """Start the moment detection loop."""
        self._snapshot_url = snapshot_url
        self._running = True
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self._http_client = httpx.AsyncClient(timeout=10.0)
        self._task = asyncio.create_task(self._detection_loop(config))
        logger.info("MomentDetector started (snapshot URL: %s)",
                     snapshot_url.split("?")[0] + "?...")

    async def stop(self):
        """Stop the moment detection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        logger.info("MomentDetector stopped")

    async def _grab_frame(self) -> Optional[np.ndarray]:
        """Grab a frame via HTTP snapshot."""
        if not self._snapshot_url or not self._http_client:
            return None
        try:
            resp = await self._http_client.get(self._snapshot_url)
            if resp.status_code != 200:
                logger.warning("Snapshot HTTP %d", resp.status_code)
                return None
            # Decode JPEG to numpy array
            arr = np.frombuffer(resp.content, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.warning("Snapshot fetch failed: %s", e)
            return None

    async def _detection_loop(self, initial_config: ShortForgeConfig):
        """Main detection loop."""
        retry_count = 0
        max_retries = 5

        while self._running:
            try:
                # Reload config each iteration for live threshold changes
                db = SessionLocal()
                try:
                    config = db.query(ShortForgeConfig).first()
                    if not config or not config.enabled:
                        await asyncio.sleep(5)
                        continue
                    interval = config.detector_interval_seconds or 5
                finally:
                    db.close()

                # Grab a frame via HTTP snapshot
                frame = await self._grab_frame()

                if frame is None:
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error("Snapshot unavailable after %d retries, pausing 60s", max_retries)
                        await asyncio.sleep(60)
                        retry_count = 0
                    else:
                        await asyncio.sleep(interval)
                    continue

                retry_count = 0

                # Analyze frame (CPU-bound OpenCV in thread)
                result = await asyncio.to_thread(self._analyze_frame, frame)
                if result is None:
                    await asyncio.sleep(interval)
                    continue

                trigger_type, score = result
                threshold = self._get_threshold(config, trigger_type)

                # Log scores periodically (~1/min at 5s interval)
                self._log_counter += 1
                if self._log_counter % 12 == 1:
                    logger.info(
                        "ShortForge scores: %s=%.4f (threshold=%.2f)",
                        trigger_type, score, threshold,
                    )

                if trigger_type and score >= threshold:
                    # Check cooldown
                    now = time.time()
                    if now - self._last_moment_time < (config.cooldown_seconds or 120):
                        await asyncio.sleep(interval)
                        continue

                    self._last_moment_time = now

                    # Save frame snapshot
                    frame_path = self._save_snapshot()

                    # Log moment to database
                    db = SessionLocal()
                    try:
                        moment = Moment(
                            camera_id=config.camera_id,
                            timestamp=datetime.now(timezone.utc),
                            trigger_type=trigger_type,
                            score=round(score, 3),
                            frame_path=str(frame_path) if frame_path else None,
                            status="detected",
                        )
                        db.add(moment)
                        db.commit()
                        db.refresh(moment)
                        logger.info("Moment detected: type=%s score=%.3f id=%d", trigger_type, score, moment.id)
                    finally:
                        db.close()

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in moment detection loop")
                await asyncio.sleep(5)

    def _analyze_frame(self, frame: np.ndarray) -> Optional[tuple[str, float]]:
        """Compute motion + brightness scores from a frame. Returns (trigger_type, score) or None."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # --- Motion scoring (frame differencing) ---
        motion_score = 0.0
        if self._prev_frame is not None:
            diff = cv2.absdiff(self._prev_frame, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            motion_score = float(np.count_nonzero(thresh)) / thresh.size

        # --- Brightness/color shift scoring (histogram comparison) ---
        brightness_score = 0.0
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        cv2.normalize(hist, hist)
        if self._prev_hist is not None:
            corr = cv2.compareHist(self._prev_hist, hist, cv2.HISTCMP_CORREL)
            brightness_score = max(0.0, 1.0 - corr)

        # Store current frame for next comparison
        self._prev_frame = gray
        self._prev_hist = hist
        self._current_frame = frame

        # Return the highest-scoring trigger
        scores = {
            "motion": motion_score,
            "brightness": brightness_score,
        }
        best_type = max(scores, key=lambda k: scores[k])
        best_score = scores[best_type]

        return (best_type, best_score)

    def _get_threshold(self, config: ShortForgeConfig, trigger_type: str) -> float:
        """Get the threshold for a trigger type from config."""
        thresholds = {
            "motion": config.motion_threshold if config.motion_threshold is not None else 0.05,
            "brightness": config.brightness_threshold if config.brightness_threshold is not None else 0.15,
            "activity": config.activity_threshold if config.activity_threshold is not None else 0.10,
        }
        return thresholds.get(trigger_type, 0.10)

    def _save_snapshot(self) -> Optional[Path]:
        """Save the current frame as a JPEG snapshot."""
        if self._current_frame is None:
            return None
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = SNAPSHOTS_DIR / f"moment_{ts}.jpg"
        cv2.imwrite(str(path), self._current_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return path


# Singleton
_detector: Optional[MomentDetector] = None


def get_moment_detector() -> MomentDetector:
    global _detector
    if _detector is None:
        _detector = MomentDetector()
    return _detector
