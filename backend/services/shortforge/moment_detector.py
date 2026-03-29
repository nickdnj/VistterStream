"""
Moment Detector — timeline-embedded frame analysis.

Instead of polling independently, the detector is called by the timeline
executor at each segment start. It maintains per-preset frame history so
PTZ camera preset changes don't trigger false motion detections.

Scores frames for motion and brightness changes using OpenCV.
When a threshold is crossed, logs a Moment to the database.
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

DATA_DIR = Path("/data/shortforge") if Path("/data").exists() else Path("data/shortforge")
SNAPSHOTS_DIR = DATA_DIR / "snapshots"


class MomentDetector:
    """Analyzes camera snapshots per-preset for interesting moments."""

    def __init__(self):
        # Per-preset state: {preset_id: {"prev_frame": ..., "prev_hist": ...}}
        self._preset_state: dict[int, dict] = {}
        self._last_moment_time: float = 0
        self._http_client: Optional[httpx.AsyncClient] = None
        self._log_counter: int = 0
        # HOG person detector (initialized lazily)
        self._hog: Optional[cv2.HOGDescriptor] = None
        # Suppress httpx request logging (snapshot URL contains camera credentials)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    async def _ensure_client(self):
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def evaluate(
        self,
        camera_id: int,
        preset_id: int,
        snapshot_url: str,
    ) -> Optional[int]:
        """
        Called by the timeline executor at each segment start.

        Grabs a snapshot, compares against the previous frame FROM THE SAME PRESET,
        and logs a Moment if the threshold is crossed.

        Returns the moment ID if one was created, or None.
        """
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        await self._ensure_client()

        # Load config
        db = SessionLocal()
        try:
            config = db.query(ShortForgeConfig).first()
            if not config or not config.enabled:
                return None
        finally:
            db.close()

        # Grab frame via HTTP snapshot
        frame = await self._grab_frame(snapshot_url)
        if frame is None:
            return None

        # Analyze against per-preset state
        result = await asyncio.to_thread(self._analyze_frame, frame, preset_id)
        if result is None:
            return None

        trigger_type, score = result
        threshold = self._get_threshold(config, trigger_type)

        # Log every evaluation (only ~8 per 2-minute timeline loop)
        logger.info(
            "ShortForge [preset %d]: %s=%.4f (threshold=%.2f)",
            preset_id, trigger_type, score, threshold,
        )

        if score < threshold:
            return None

        # Person detection gate — reject frames containing people (privacy)
        has_people = await asyncio.to_thread(self._detect_people, frame)
        if has_people:
            logger.info(
                "ShortForge [preset %d]: moment rejected (people detected)",
                preset_id,
            )
            return None

        # Check cooldown (global, not per-preset)
        now = time.time()
        if now - self._last_moment_time < (config.cooldown_seconds or 120):
            return None

        self._last_moment_time = now

        # Save frame snapshot
        frame_path = self._save_snapshot(frame, preset_id)

        # Log moment to database
        db = SessionLocal()
        try:
            moment = Moment(
                camera_id=camera_id,
                timestamp=datetime.now(timezone.utc),
                trigger_type=trigger_type,
                score=round(score, 3),
                frame_path=str(frame_path) if frame_path else None,
                status="detected",
            )
            db.add(moment)
            db.commit()
            db.refresh(moment)
            logger.info(
                "Moment detected: preset=%d type=%s score=%.3f id=%d",
                preset_id, trigger_type, score, moment.id,
            )
            return moment.id
        finally:
            db.close()

    async def _grab_frame(self, snapshot_url: str) -> Optional[np.ndarray]:
        """Grab a frame via HTTP snapshot."""
        try:
            resp = await self._http_client.get(snapshot_url)
            if resp.status_code != 200:
                logger.warning("Snapshot HTTP %d", resp.status_code)
                return None
            arr = np.frombuffer(resp.content, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.warning("Snapshot fetch failed: %s", e)
            return None

    def _analyze_frame(self, frame: np.ndarray, preset_id: int) -> Optional[tuple[str, float]]:
        """Compute motion + brightness scores against same-preset history."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Get or create per-preset state
        state = self._preset_state.get(preset_id, {})

        # --- Motion scoring ---
        motion_score = 0.0
        prev_frame = state.get("prev_frame")
        if prev_frame is not None:
            diff = cv2.absdiff(prev_frame, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            motion_score = float(np.count_nonzero(thresh)) / thresh.size

        # --- Brightness/color shift scoring ---
        brightness_score = 0.0
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        cv2.normalize(hist, hist)
        prev_hist = state.get("prev_hist")
        if prev_hist is not None:
            corr = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            brightness_score = max(0.0, 1.0 - corr)

        # Update per-preset state
        self._preset_state[preset_id] = {
            "prev_frame": gray,
            "prev_hist": hist,
        }

        scores = {
            "motion": motion_score,
            "brightness": brightness_score,
        }
        best_type = max(scores, key=lambda k: scores[k])
        best_score = scores[best_type]

        return (best_type, best_score)

    def _detect_people(self, frame: np.ndarray) -> bool:
        """Detect people in a frame using HOG + SVM. Returns True if people found."""
        if self._hog is None:
            self._hog = cv2.HOGDescriptor()
            self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        # Downscale for speed (HOG is slow on full 1080p)
        h, w = frame.shape[:2]
        scale = 480 / max(h, w)
        if scale < 1.0:
            small = cv2.resize(frame, (int(w * scale), int(h * scale)))
        else:
            small = frame

        rects, weights = self._hog.detectMultiScale(
            small,
            winStride=(8, 8),
            padding=(4, 4),
            scale=1.05,
        )
        # Filter weak detections
        confident = [w for w in weights if w > 0.3]
        return len(confident) > 0

    def _get_threshold(self, config: ShortForgeConfig, trigger_type: str) -> float:
        """Get the threshold for a trigger type from config."""
        thresholds = {
            "motion": config.motion_threshold if config.motion_threshold is not None else 0.05,
            "brightness": config.brightness_threshold if config.brightness_threshold is not None else 0.15,
            "activity": config.activity_threshold if config.activity_threshold is not None else 0.10,
        }
        return thresholds.get(trigger_type, 0.10)

    def _save_snapshot(self, frame: np.ndarray, preset_id: int) -> Optional[Path]:
        """Save a frame as a JPEG snapshot."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = SNAPSHOTS_DIR / f"moment_p{preset_id}_{ts}.jpg"
        cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return path


# Singleton
_detector: Optional[MomentDetector] = None


def get_moment_detector() -> MomentDetector:
    global _detector
    if _detector is None:
        _detector = MomentDetector()
    return _detector
