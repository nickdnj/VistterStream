"""
Capture Window Scheduler — time-based capture with AI quality scoring.

Manages capture windows throughout the day:
- Morning golden hour: sunrise to sunrise+60min
- Midday: 10AM to 3PM local
- Evening golden hour: sunset-60min to sunset
- Dark hours: skip entirely

During each window, snapshots are scored by AI vision for visual quality.
At the end of a window, the best-scoring frame triggers the capture pipeline.
"""

import asyncio
import logging
import math
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def get_sun_times(latitude: float, longitude: float, date: datetime = None) -> dict:
    """
    Calculate sunrise and sunset times using simplified NOAA algorithm.

    Returns: {"sunrise": datetime (UTC), "sunset": datetime (UTC)}
    """
    if date is None:
        date = datetime.now(timezone.utc)

    # Day of year
    n = date.timetuple().tm_yday

    # Solar noon approximation
    lng_hour = longitude / 15.0

    # Sunrise
    t_rise = n + (6 - lng_hour) / 24
    # Sunset
    t_set = n + (18 - lng_hour) / 24

    # Sun's mean anomaly
    m_rise = (0.9856 * t_rise) - 3.289
    m_set = (0.9856 * t_set) - 3.289

    def _calc(m, t):
        # Sun's true longitude
        l = m + (1.916 * math.sin(math.radians(m))) + (0.020 * math.sin(math.radians(2 * m))) + 282.634
        l = l % 360

        # Right ascension
        ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(l))))
        ra = ra % 360

        l_quad = (math.floor(l / 90)) * 90
        ra_quad = (math.floor(ra / 90)) * 90
        ra = ra + (l_quad - ra_quad)
        ra = ra / 15  # to hours

        # Sun's declination
        sin_dec = 0.39782 * math.sin(math.radians(l))
        cos_dec = math.cos(math.asin(sin_dec))

        # Sunrise/sunset hour angle
        cos_h = (math.cos(math.radians(90.833)) - (sin_dec * math.sin(math.radians(latitude)))) / \
                (cos_dec * math.cos(math.radians(latitude)))

        if cos_h > 1 or cos_h < -1:
            return None  # No sunrise/sunset (polar)

        return ra, cos_h, t

    rise_data = _calc(m_rise, t_rise)
    set_data = _calc(m_set, t_set)

    if not rise_data or not set_data:
        # Fallback: 6 AM / 7 PM
        base = date.replace(hour=0, minute=0, second=0, microsecond=0)
        return {
            "sunrise": base + timedelta(hours=10),  # ~6 AM EDT in UTC
            "sunset": base + timedelta(hours=23),    # ~7 PM EDT in UTC
        }

    # Sunrise hour angle
    ra_r, cos_h_r, t_r = rise_data
    h_r = 360 - math.degrees(math.acos(cos_h_r))
    h_r = h_r / 15
    local_rise = h_r + ra_r - (0.06571 * t_r) - 6.622
    utc_rise = local_rise - lng_hour
    utc_rise = utc_rise % 24

    # Sunset hour angle
    ra_s, cos_h_s, t_s = set_data
    h_s = math.degrees(math.acos(cos_h_s))
    h_s = h_s / 15
    local_set = h_s + ra_s - (0.06571 * t_s) - 6.622
    utc_set = local_set - lng_hour
    utc_set = utc_set % 24

    base = date.replace(hour=0, minute=0, second=0, microsecond=0)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)

    sunrise = base + timedelta(hours=utc_rise)
    sunset = base + timedelta(hours=utc_set)

    return {"sunrise": sunrise, "sunset": sunset}


class CaptureWindowManager:
    """Manages capture windows and tracks best-scoring snapshots per window."""

    def __init__(self, latitude: float, longitude: float, tz_name: str = "America/New_York"):
        self.latitude = latitude
        self.longitude = longitude
        self.tz_name = tz_name

        # Best candidate per window: {"window_name": {"score": float, "preset_id": int, "snapshot_url": str, "frame_path": str}}
        self._candidates: dict[str, dict] = {}
        # Track which windows have been captured today
        self._captured_today: set[str] = set()
        self._last_date: Optional[str] = None

    def get_current_window(self) -> Optional[str]:
        """
        Determine which capture window we're currently in.

        Returns window name ("morning_golden", "midday_1", "midday_2", "evening_golden")
        or None if outside all windows (dark hours).
        """
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        # Reset daily tracking
        if self._last_date != today_str:
            self._captured_today.clear()
            self._candidates.clear()
            self._last_date = today_str

        sun = get_sun_times(self.latitude, self.longitude, now)
        sunrise = sun["sunrise"]
        sunset = sun["sunset"]

        # Define windows (all in UTC)
        windows = {
            "morning_golden": (sunrise, sunrise + timedelta(minutes=60)),
            "midday_1": (sunrise + timedelta(hours=3), sunrise + timedelta(hours=5)),
            "midday_2": (sunset - timedelta(hours=4), sunset - timedelta(hours=2)),
            "evening_golden": (sunset - timedelta(minutes=60), sunset),
        }

        for name, (start, end) in windows.items():
            if start <= now <= end:
                return name

        return None

    def get_windows_for_today(self) -> list[dict]:
        """Get all capture windows for today with their times and status."""
        now = datetime.now(timezone.utc)
        sun = get_sun_times(self.latitude, self.longitude, now)
        sunrise = sun["sunrise"]
        sunset = sun["sunset"]

        windows = [
            {"name": "morning_golden", "label": "Morning Golden Hour", "start": sunrise, "end": sunrise + timedelta(minutes=60)},
            {"name": "midday_1", "label": "Late Morning", "start": sunrise + timedelta(hours=3), "end": sunrise + timedelta(hours=5)},
            {"name": "midday_2", "label": "Early Afternoon", "start": sunset - timedelta(hours=4), "end": sunset - timedelta(hours=2)},
            {"name": "evening_golden", "label": "Evening Golden Hour", "start": sunset - timedelta(minutes=60), "end": sunset},
        ]

        for w in windows:
            w["captured"] = w["name"] in self._captured_today
            w["active"] = w["start"] <= now <= w["end"]
            best = self._candidates.get(w["name"])
            w["best_score"] = best["score"] if best else None
            # Convert to ISO strings for API
            w["start"] = w["start"].isoformat()
            w["end"] = w["end"].isoformat()

        return windows

    def submit_score(self, window_name: str, preset_id: int, score: float,
                     snapshot_url: str, frame_path: Optional[str] = None) -> bool:
        """
        Submit a quality score for the current window. Returns True if this is the new best.
        """
        if window_name in self._captured_today:
            return False  # Already captured for this window

        current = self._candidates.get(window_name)
        if current is None or score > current["score"]:
            self._candidates[window_name] = {
                "score": score,
                "preset_id": preset_id,
                "snapshot_url": snapshot_url,
                "frame_path": frame_path,
            }
            logger.info("New best for %s: score=%.3f preset=%d", window_name, score, preset_id)
            return True
        return False

    def get_best_candidate(self, window_name: str) -> Optional[dict]:
        """Get the best-scoring candidate for a window."""
        return self._candidates.get(window_name)

    def mark_captured(self, window_name: str):
        """Mark a window as captured (no more captures for this window today)."""
        self._captured_today.add(window_name)
        if window_name in self._candidates:
            del self._candidates[window_name]
        logger.info("Window %s captured for today", window_name)

    def is_daylight(self) -> bool:
        """Check if it's currently between sunrise and sunset."""
        now = datetime.now(timezone.utc)
        sun = get_sun_times(self.latitude, self.longitude, now)
        return sun["sunrise"] <= now <= sun["sunset"]


# Singleton
_manager: Optional[CaptureWindowManager] = None


def get_capture_window_manager(latitude: float = 40.338, longitude: float = -73.977) -> CaptureWindowManager:
    global _manager
    if _manager is None:
        _manager = CaptureWindowManager(latitude, longitude)
    return _manager
