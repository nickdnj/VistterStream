"""
Background scheduler service that evaluates schedule windows and launches timelines.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import selectinload

from models.database import SessionLocal
from models.schedule import Schedule
from models.timeline import Timeline
from models.destination import StreamingDestination
from services.timeline_executor import get_timeline_executor

logger = logging.getLogger("scheduler_service")


def _parse_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _safe_timezone(tz_name: Optional[str]) -> ZoneInfo:
    name = tz_name or "UTC"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.warning("Unknown timezone '%s', defaulting to UTC", name)
        return ZoneInfo("UTC")


def _is_schedule_active(schedule: Schedule, now_utc: datetime) -> bool:
    if not schedule.is_enabled:
        return False

    active_days: List[int] = schedule.days_of_week or []
    if not active_days:
        return False

    tz = _safe_timezone(schedule.timezone)
    now_local = now_utc.astimezone(tz)
    minutes_now = now_local.hour * 60 + now_local.minute

    start_min = _parse_minutes(schedule.window_start)
    end_min = _parse_minutes(schedule.window_end)

    if start_min == end_min:
        # Zero-length window → never active
        return False

    weekday = now_local.weekday()

    if start_min < end_min:
        # Same-day window (e.g. 06:00-23:00)
        return weekday in active_days and start_min <= minutes_now < end_min

    # Overnight window (e.g. 22:00-02:00)
    if minutes_now >= start_min:
        # Before midnight: use current day
        return weekday in active_days

    # After midnight: treat as previous day
    prev_day = (weekday - 1) % 7
    return prev_day in active_days


def _next_timeline_id(schedule: Schedule, current_index: Optional[int]) -> Optional[int]:
    ordered = sorted(schedule.timelines, key=lambda item: item.order_index)
    if not ordered:
        return None

    if current_index is None:
        return ordered[0].timeline_id

    for item in ordered:
        if item.order_index > current_index:
            return item.timeline_id

    # Loop back to first timeline
    return ordered[0].timeline_id


def _timeline_index(schedule: Schedule, timeline_id: int) -> Optional[int]:
    for item in sorted(schedule.timelines, key=lambda entry: entry.order_index):
        if item.timeline_id == timeline_id:
            return item.order_index
    return None


@dataclass
class RunningSchedule:
    schedule_id: int
    timeline_id: int
    started_at: datetime
    window_started_at: datetime
    timeline_index: int


class SchedulerService:
    """Evaluate schedule windows and control timeline execution."""

    _POLL_INTERVAL_SECONDS = 30

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._running: Dict[int, RunningSchedule] = {}
        self._service_lock = asyncio.Lock()
        self._state_lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._service_lock:
            if self._task and not self._task.done():
                return
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_loop(), name="schedule-runner")
            logger.info("Scheduler service started")

    async def stop(self) -> None:
        async with self._service_lock:
            if not self._task:
                return
            self._stop_event.set()
            await self._task
            self._task = None
            logger.info("Scheduler service stopped")

    async def trigger_schedule(self, schedule_id: int, *, force: bool = False) -> bool:
        """Manually start a schedule immediately."""
        now_utc = datetime.now(timezone.utc)
        schedule = self._load_schedule(schedule_id)
        if not schedule:
            return False

        if not force and not _is_schedule_active(schedule, now_utc):
            return False

        async with self._state_lock:
            if schedule_id in self._running:
                await self._stop_schedule(schedule_id, reason="manual restart")
            await self._start_schedule(schedule, now_utc)
        return True

    async def stop_schedule(self, schedule_id: int) -> bool:
        async with self._state_lock:
            if schedule_id not in self._running:
                return False
            await self._stop_schedule(schedule_id, reason="manual stop")
        return True

    def list_running(self) -> List[RunningSchedule]:
        return list(self._running.values())

    async def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                await self._evaluate_schedules()
                await asyncio.wait(
                    [self._stop_event.wait()],
                    timeout=self._POLL_INTERVAL_SECONDS,
                )
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        finally:
            await self._shutdown_running()

    async def _evaluate_schedules(self) -> None:
        now_utc = datetime.now(timezone.utc)

        db = SessionLocal()
        try:
            schedules: List[Schedule] = (
                db.query(Schedule)
                .options(selectinload(Schedule.timelines))
                .all()
            )
        finally:
            db.close()

        async with self._state_lock:
            active_ids = {s.id for s in schedules if s.is_enabled}

            for schedule in schedules:
                is_active = _is_schedule_active(schedule, now_utc)
                running = schedule.id in self._running

                if is_active and not running:
                    await self._start_schedule(schedule, now_utc)
                elif is_active and running:
                    await self._maybe_advance_schedule(schedule, now_utc)
                elif not is_active and running:
                    await self._stop_schedule(schedule.id, reason="window ended")

            # Stop schedules that were removed or disabled
            for schedule_id in list(self._running.keys()):
                if schedule_id not in active_ids:
                    await self._stop_schedule(schedule_id, reason="schedule removed or disabled")

    async def _start_schedule(self, schedule: Schedule, now_utc: datetime) -> None:
        timeline_id = _next_timeline_id(schedule, None)
        if timeline_id is None:
            logger.warning("Schedule %s has no timelines; skipping", schedule.name)
            return

        destinations = await self._load_destinations(schedule.destination_ids)
        if not destinations:
            logger.warning("Schedule %s has no valid destinations; skipping", schedule.name)
            return

        await self._launch_timeline(schedule, timeline_id, destinations, now_utc)

    async def _maybe_advance_schedule(self, schedule: Schedule, now_utc: datetime) -> None:
        state = self._running.get(schedule.id)
        if not state:
            return

        timeline = self._load_timeline(state.timeline_id)
        if not timeline:
            await self._stop_schedule(schedule.id, reason="timeline missing")
            return

        if timeline.loop:
            # Looping timelines run until the window closes
            return

        duration_seconds = timeline.duration or 0
        if duration_seconds <= 0:
            return

        elapsed = (now_utc - state.started_at).total_seconds()
        if elapsed < duration_seconds:
            return

        next_timeline_id = _next_timeline_id(schedule, state.timeline_index)
        if not next_timeline_id:
            next_timeline_id = state.timeline_id

        await self._stop_schedule(schedule.id, reason="advancing to next timeline")

        destinations = await self._load_destinations(schedule.destination_ids)
        if not destinations:
            logger.warning("Schedule %s has no valid destinations; skipping advance", schedule.name)
            return

        await self._launch_timeline(schedule, next_timeline_id, destinations, now_utc)

    async def _launch_timeline(
        self,
        schedule: Schedule,
        timeline_id: int,
        destinations: List[StreamingDestination],
        now_utc: datetime,
    ) -> None:
        executor = get_timeline_executor()
        output_urls = [dest.get_full_rtmp_url() for dest in destinations if dest.is_active]
        if not output_urls:
            logger.warning("Schedule %s destinations are inactive; skipping", schedule.name)
            return

        try:
            success = await executor.start_timeline(
                timeline_id=timeline_id,
                output_urls=output_urls,
                encoding_profile=None,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to start timeline %s for schedule %s: %s", timeline_id, schedule.name, exc)
            return

        timeline_index = _timeline_index(schedule, timeline_id) or 0

        if not success:
            logger.info(
                "Timeline %s already running; schedule %s will monitor existing run",
                timeline_id,
                schedule.name,
            )
        else:
            logger.info(
                "Started schedule %s with timeline %s → %d destinations",
                schedule.name,
                timeline_id,
                len(output_urls),
            )

        self._running[schedule.id] = RunningSchedule(
            schedule_id=schedule.id,
            timeline_id=timeline_id,
            started_at=now_utc,
            window_started_at=now_utc,
            timeline_index=timeline_index,
        )

    async def _stop_schedule(self, schedule_id: int, reason: str) -> None:
        state = self._running.pop(schedule_id, None)
        if not state:
            return

        executor = get_timeline_executor()
        try:
            await executor.stop_timeline(state.timeline_id)
            logger.info(
                "Stopped schedule %s (timeline %s): %s",
                schedule_id,
                state.timeline_id,
                reason,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to stop timeline %s for schedule %s: %s",
                state.timeline_id,
                schedule_id,
                exc,
            )

    async def _shutdown_running(self) -> None:
        async with self._state_lock:
            for schedule_id in list(self._running.keys()):
                await self._stop_schedule(schedule_id, reason="service shutdown")

    async def _load_destinations(self, destination_ids: List[int]) -> List[StreamingDestination]:
        if not destination_ids:
            return []
        db = SessionLocal()
        try:
            return (
                db.query(StreamingDestination)
                .filter(StreamingDestination.id.in_(destination_ids))
                .all()
            )
        finally:
            db.close()

    def _load_schedule(self, schedule_id: int) -> Optional[Schedule]:
        db = SessionLocal()
        try:
            schedule = (
                db.query(Schedule)
                .options(selectinload(Schedule.timelines))
                .filter(Schedule.id == schedule_id)
                .first()
            )
            return schedule
        finally:
            db.close()

    def _load_timeline(self, timeline_id: int) -> Optional[Timeline]:
        db = SessionLocal()
        try:
            return db.query(Timeline).filter(Timeline.id == timeline_id).first()
        finally:
            db.close()


_SCHEDULER_SERVICE: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    global _SCHEDULER_SERVICE
    if _SCHEDULER_SERVICE is None:
        _SCHEDULER_SERVICE = SchedulerService()
    return _SCHEDULER_SERVICE
