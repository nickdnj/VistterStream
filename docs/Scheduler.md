# Scheduler

## Overview
Run timelines automatically based on saved schedules with day/time windows and destination selection. A background loop evaluates schedules and starts/stops the appropriate timeline.

## Data Model
- `Schedule`:
  - `name`, `is_enabled`, `timezone`
  - `days_of_week`: [0..6] (Mon..Sun)
  - `window_start`, `window_end` ("HH:MM"; overnight supported)
  - `destination_ids`: array of `StreamingDestination` ids
  - `timelines`: ordered list via `ScheduleTimeline {timeline_id, order_index}`

## API
- `GET /api/scheduler/` → list schedules
- `POST /api/scheduler/` → create schedule
  - body: `{ name, is_enabled, timezone, days_of_week, window_start, window_end, destination_ids, timelines: [{timeline_id, order_index}] }`
- `DELETE /api/scheduler/{schedule_id}` → delete schedule

## Background Execution
- Service: `backend/services/scheduler_service.py`
- Runs every 30s:
  - Finds enabled schedules matching current weekday and within window
  - Starts the first configured timeline to configured destinations
  - Stops when outside any matching windows

## Frontend
- Page: `Scheduler.tsx`
  - Create schedule form (days, start/end, timeline picker)
  - Overlap warning across days and time (overnight aware)
  - List schedules with Delete
  - Uses `api` client (base `/api` → `http://localhost:8000/api`)

## Notes / Future
- UI for selecting destinations per schedule
- Cycle multiple timelines within the active window (round-robin)
- Pause/Resume controls and Run-Now









