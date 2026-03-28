"""
Moment Detector — lightweight OpenCV frame analysis on RTSP feed.

Runs every N seconds (configurable). Scores frames for motion, brightness changes,
and activity. When a threshold is crossed, logs a Moment to the database.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.shortforge import Moment, ShortForgeConfig

logger = logging.getLogger(__name__)

# Data directory for ShortForge artifacts
DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
SNAPSHOTS_DIR = DATA_DIR / "snapshots"


class MomentDetector:
    """Analyzes RTSP frames for interesting moments using OpenCV."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._prev_frame: Optional[np.ndarray] = None
        self._prev_hist: Optional[np.ndarray] = None
        self._last_moment_time: float = 0
        self._rtsp_url: Optional[str] = None
        self._cap: Optional[cv2.VideoCapture] = None

    async def start(self, rtsp_url: str, config: ShortForgeConfig):
        """Start the moment detection loop."""
        self._rtsp_url = rtsp_url
        self._running = True
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        self._task = asyncio.create_task(self._detection_loop(config))
        logger.info("MomentDetector started for %s", rtsp_url)

    async def stop(self):
        """Stop the moment detection loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._cap and self._cap.isOpened():
            self._cap.release()
            self._cap = None
        logger.info("MomentDetector stopped")

    def _open_capture(self) -> bool:
        """Open or reopen the RTSP capture."""
        if self._cap and self._cap.isOpened():
            return True
        if not self._rtsp_url:
            return False
        self._cap = cv2.VideoCapture(self._rtsp_url, cv2.CAP_FFMPEG)
        if not self._cap.isOpened():
            logger.error("Failed to open RTSP stream: %s", self._rtsp_url)
            self._cap = None
            return False
        # Set buffer size to 1 to always get the latest frame
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return True

    async def _detection_loop(self, initial_config: ShortForgeConfig):
        """Main detection loop — runs in asyncio, offloads CV to thread."""
        retry_count = 0
        max_retries = 3

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

                # Grab and analyze a frame in a thread (blocking OpenCV call)
                result = await asyncio.to_thread(self._analyze_frame, config)

                if result is None:
                    # Frame grab failed
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error("RTSP feed lost after %d retries, pausing detection", max_retries)
                        if self._cap:
                            self._cap.release()
                            self._cap = None
                        await asyncio.sleep(30)  # wait before reconnect
                        retry_count = 0
                    else:
                        await asyncio.sleep(2)
                    continue

                retry_count = 0
                trigger_type, score = result

                if trigger_type and score >= self._get_threshold(config, trigger_type):
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

    def _analyze_frame(self, config: ShortForgeConfig) -> Optional[tuple[str, float]]:
        """Grab a frame and compute motion + brightness scores. Returns (trigger_type, score) or None."""
        if not self._open_capture():
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None

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
            # Correlation: 1.0 = identical, lower = more change
            corr = cv2.compareHist(self._prev_hist, hist, cv2.HISTCMP_CORREL)
            brightness_score = max(0.0, 1.0 - corr)  # invert so higher = more change

        # Store current frame for next comparison
        self._prev_frame = gray
        self._prev_hist = hist
        # Keep the color frame for snapshot
        self._current_frame = frame

        # Return the highest-scoring trigger
        scores = {
            "motion": motion_score,
            "brightness": brightness_score,
        }
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        return (best_type, best_score)

    def _get_threshold(self, config: ShortForgeConfig, trigger_type: str) -> float:
        """Get the threshold for a trigger type from config."""
        thresholds = {
            "motion": config.motion_threshold or 0.6,
            "brightness": config.brightness_threshold or 0.5,
            "activity": config.activity_threshold or 0.7,
        }
        return thresholds.get(trigger_type, 0.5)

    def _save_snapshot(self) -> Optional[Path]:
        """Save the current frame as a JPEG snapshot."""
        if not hasattr(self, '_current_frame') or self._current_frame is None:
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
