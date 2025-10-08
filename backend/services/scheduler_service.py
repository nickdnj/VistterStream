"""
Background scheduler that starts timelines based on saved schedules.
Runs a periodic loop checking active windows and orchestrating playback.
"""

import asyncio
from datetime import datetime, time
from typing import Optional
import logging

from models.database import SessionLocal
from models.schedule import Schedule, ScheduleTimeline
from models.timeline import Timeline
from models.destination import StreamingDestination
from services.timeline_executor import get_timeline_executor

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()
        self._active_schedule_id: Optional[int] = None
        self._active_timeline_id: Optional[int] = None

    async def start(self):
        if self._task and not self._task.done():
            return
        self._shutdown.clear()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        if self._task:
            self._shutdown.set()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self):
        logger.info("🗓️ Scheduler loop started")
        while not self._shutdown.is_set():
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Scheduler tick error: {e}")
            await asyncio.sleep(30)  # check every 30s
        logger.info("🗓️ Scheduler loop stopped")

    async def _tick(self):
        now = datetime.now()
        db = SessionLocal()
        try:
            # Fetch enabled schedules
            schedules = db.query(Schedule).filter(Schedule.is_enabled == True).all()
            if not schedules:
                return

            # Pick first schedule whose day matches and within window
            for s in schedules:
                if (now.weekday() not in (s.days_of_week or [])):
                    continue
                if not self._is_in_window(now, s.window_start, s.window_end):
                    continue

                # If already running this schedule, keep going
                if self._active_schedule_id == s.id:
                    return

                # Start new schedule: stop any active
                await self._stop_active()

                # Determine destinations
                dests = db.query(StreamingDestination).filter(StreamingDestination.id.in_(s.destination_ids or [])).all()
                output_urls = [d.get_full_rtmp_url() for d in dests]
                if not output_urls:
                    logger.warning("Scheduler: no destinations configured, skipping")
                    return

                # Play timelines in order (looping). For v1, start the first timeline only.
                items = sorted(s.timelines, key=lambda x: x.order_index)
                if not items:
                    logger.warning("Scheduler: no timelines attached, skipping")
                    return

                tl_id = items[0].timeline_id
                exec = get_timeline_executor()
                ok = await exec.start_timeline(timeline_id=tl_id, output_urls=output_urls, encoding_profile=None)
                if ok:
                    self._active_schedule_id = s.id
                    self._active_timeline_id = tl_id
                    logger.info(f"Scheduler started timeline {tl_id} for schedule {s.name}")
                return

            # If we reach here, no schedule window matches; stop active if any
            await self._stop_active()
        finally:
            db.close()

    async def _stop_active(self):
        if self._active_timeline_id is not None:
            exec = get_timeline_executor()
            await exec.stop_timeline(self._active_timeline_id)
            logger.info(f"Scheduler stopped timeline {self._active_timeline_id}")
        self._active_schedule_id = None
        self._active_timeline_id = None

    def _is_in_window(self, now: datetime, start_str: str, end_str: str) -> bool:
        try:
            sh, sm = map(int, (start_str or '00:00').split(':'))
            eh, em = map(int, (end_str or '23:59').split(':'))
            start_t = time(sh, sm)
            end_t = time(eh, em)
        except Exception:
            return True
        t = now.time()
        if start_t <= end_t:
            return start_t <= t <= end_t
        # Over-midnight window
        return t >= start_t or t <= end_t


_scheduler: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerService()
    return _scheduler


