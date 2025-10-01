"""
Emergency controls API - Kill all streams, stop all processes
"""

from fastapi import APIRouter
import subprocess
import signal
import os
import logging

from services.timeline_executor import get_timeline_executor

router = APIRouter(prefix="/api/emergency", tags=["emergency"])

logger = logging.getLogger(__name__)


@router.post("/kill-all-streams")
async def kill_all_streams():
    """
    EMERGENCY: Kill all FFmpeg processes and stop all timelines
    """
    logger.warning("🚨 EMERGENCY: Kill all streams requested!")
    
    killed_processes = []
    errors = []
    
    # 1. Stop all timeline executions
    try:
        executor = get_timeline_executor()
        timeline_ids = list(executor.active_timelines.keys())
        for timeline_id in timeline_ids:
            try:
                await executor.stop_timeline(timeline_id)
                killed_processes.append(f"Timeline {timeline_id}")
            except Exception as e:
                errors.append(f"Failed to stop timeline {timeline_id}: {e}")
        logger.info(f"Stopped {len(timeline_ids)} timelines")
    except Exception as e:
        errors.append(f"Failed to stop timelines: {e}")
    
    # 2. Kill all FFmpeg processes using pgrep
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'ffmpeg'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        killed_processes.append(f"FFmpeg PID {pid}")
                        logger.info(f"Killed FFmpeg process {pid}")
                    except Exception as e:
                        errors.append(f"Failed to kill PID {pid}: {e}")
            
            # Wait a moment, then SIGKILL any survivors
            subprocess.run(['sleep', '2'])
            result = subprocess.run(['pgrep', '-f', 'ffmpeg'], capture_output=True)
            if result.returncode == 0:
                pids = result.stdout.decode().strip().split('\n')
                for pid in pids:
                    if pid:
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                            killed_processes.append(f"FFmpeg PID {pid} (SIGKILL)")
                            logger.warning(f"Force killed FFmpeg process {pid}")
                        except Exception:
                            pass
    except Exception as e:
        errors.append(f"Failed to kill FFmpeg processes: {e}")
    
    logger.warning(f"🚨 Emergency stop complete. Killed: {len(killed_processes)} processes")
    
    return {
        "message": "Emergency stop executed",
        "killed_processes": killed_processes,
        "errors": errors,
        "total_killed": len(killed_processes)
    }


@router.get("/status")
async def emergency_status():
    """Get current stream status for emergency monitoring"""
    
    # Check for FFmpeg processes
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'ffmpeg'],
            capture_output=True,
            text=True
        )
        ffmpeg_count = len(result.stdout.strip().split('\n')) if result.returncode == 0 else 0
    except Exception:
        ffmpeg_count = 0
    
    # Check for active timelines
    try:
        executor = get_timeline_executor()
        timeline_count = len(executor.active_timelines)
    except Exception:
        timeline_count = 0
    
    return {
        "ffmpeg_processes": ffmpeg_count,
        "active_timelines": timeline_count,
        "total_active": ffmpeg_count + timeline_count
    }

