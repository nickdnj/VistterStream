# Watchdog Integration Fixed ✅

## Problem

The watchdog was not monitoring running streams because:
1. It couldn't find which stream was associated with each destination
2. It only started on backend initialization, missing streams that started later
3. There was no mechanism to link destinations to active streams

## Solution

### 1. Track Destination URLs in Stream Processes

**File:** `backend/services/ffmpeg_manager.py`

- Added `output_urls` field to `StreamProcess` dataclass
- Stores the RTMP destination URLs when stream starts
- Added `find_stream_by_destination_url()` method to lookup streams by destination

```python
def find_stream_by_destination_url(self, destination_url: str) -> Optional[int]:
    """Find a running stream streaming to a specific destination URL"""
    for stream_id, stream_process in self.processes.items():
        if stream_process.status == StreamStatus.RUNNING:
            if destination_url in stream_process.output_urls:
                return stream_id
    return None
```

### 2. Auto-Detect Active Streams

**File:** `backend/services/watchdog_manager.py`

- Updated `start_watchdog()` to auto-detect stream_id if not provided
- Looks up the stream by destination URL using FFmpeg manager
- Only starts watchdog if there's an active stream

```python
# Auto-detect stream_id if not provided
if stream_id is None:
    ffmpeg_manager = await get_ffmpeg_manager()
    destination_url = destination.get_full_rtmp_url()
    stream_id = ffmpeg_manager.find_stream_by_destination_url(destination_url)
    
    if stream_id is None:
        logger.warning("No active stream found, watchdog will not start")
        return
```

### 3. Notify on Stream Start/Stop

**File:** `backend/services/watchdog_manager.py`

Added two new notification methods:

```python
async def notify_stream_started(destination_ids, stream_id, db_session):
    """Start watchdogs when a stream goes live to destinations"""
    
async def notify_stream_stopped(stream_id):
    """Stop watchdogs when a stream stops"""
```

### 4. Hook Into Stream Lifecycle

**File:** `backend/services/stream_router.py`

- Calls `notify_stream_started()` when going live
- Calls `notify_stream_stopped()` when stopping

```python
# In go_live():
await watchdog_manager.notify_stream_started(
    destination_ids=destination_ids,
    stream_id=stream_id,
    db_session=db_session
)

# In stop():
await watchdog_manager.notify_stream_stopped(stream_id)
```

## How It Works Now

1. **Setup**: User enables watchdog in destination settings
2. **Go Live**: User starts streaming to that destination
3. **Auto-Start**: Watchdog automatically detects the stream and starts monitoring
4. **Monitoring**: Watchdog checks FFmpeg health every 30s (or configured interval)
5. **Optional YouTube Check**: If channel `/live` URL is provided, also checks YouTube's side
6. **Auto-Recovery**: If 3 consecutive checks fail, automatically restarts the stream
7. **Auto-Stop**: When stream stops, watchdog automatically stops

## Testing

```bash
# On Raspberry Pi, after pulling updates:
cd ~/VistterStream
./deploy.sh

# After deployment:
# 1. Go to Settings → Destinations
# 2. Enable watchdog for your YouTube destination
# 3. Go to Timeline → Preview → Go Live
# 4. Check watchdog status:
curl http://localhost:8000/api/watchdog/status

# You should see:
# {"1": {"running": true, "consecutive_unhealthy": 0, ...}}
```

## What Changed (Files Modified)

- `backend/services/ffmpeg_manager.py` - Track destination URLs, add lookup method
- `backend/services/watchdog_manager.py` - Auto-detect streams, notification methods
- `backend/services/stream_router.py` - Hook watchdog into stream lifecycle
- `WATCHDOG_README.md` - Updated documentation

## Benefits

✅ **Zero Configuration**: Watchdog automatically starts when stream goes live  
✅ **Automatic Detection**: Finds the right stream by matching destination URL  
✅ **Lifecycle Management**: Starts/stops with stream lifecycle  
✅ **Dual-Layer Protection**: FFmpeg process + optional YouTube live check  
✅ **Auto-Recovery**: Restarts encoder on failure  
✅ **No API Keys Needed**: Works entirely locally (YouTube check is optional HTTP)

---

**Status:** Ready to deploy and test on Raspberry Pi
**Next Step:** Run `./deploy.sh` on the Pi and test with a live stream

