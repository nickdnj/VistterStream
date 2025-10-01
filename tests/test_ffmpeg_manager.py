"""
Unit tests for FFmpeg Process Manager

Tests process management, lifecycle, monitoring, and restart logic.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.ffmpeg_manager import (
    FFmpegProcessManager,
    StreamStatus,
    EncodingProfile,
    StreamMetrics,
    StreamProcess
)
from backend.services.hardware_detector import HardwareCapabilities


@pytest.fixture
def mock_hw_capabilities():
    """Mock hardware capabilities"""
    return HardwareCapabilities(
        encoder='h264_videotoolbox',
        decoder='h264_videotoolbox',
        platform='mac',
        max_concurrent_streams=10,
        supports_hardware=True
    )


@pytest_asyncio.fixture
async def manager(mock_hw_capabilities):
    """Create FFmpeg manager with mocked hardware detection"""
    with patch('backend.services.ffmpeg_manager.get_hardware_capabilities', 
               return_value=mock_hw_capabilities):
        mgr = FFmpegProcessManager()
        await mgr.initialize()
        yield mgr
        await mgr.shutdown_all()


@pytest.mark.asyncio
class TestFFmpegProcessManager:
    """Test FFmpeg Process Manager"""
    
    async def test_initialization(self, manager, mock_hw_capabilities):
        """Test manager initialization detects hardware"""
        assert manager.hw_capabilities is not None
        assert manager.hw_capabilities.encoder == 'h264_videotoolbox'
        assert manager.hw_capabilities.max_concurrent_streams == 10
    
    async def test_encoding_profile_defaults(self, mock_hw_capabilities):
        """Test reliability profile creation"""
        profile = EncodingProfile.reliability_profile(mock_hw_capabilities)
        
        assert profile.codec == 'h264_videotoolbox'
        assert profile.resolution == (1920, 1080)
        assert profile.framerate == 30
        assert profile.bitrate == "4500k"
        assert profile.keyframe_interval == 2
        assert profile.preset == "fast"
    
    async def test_build_ffmpeg_command_single_output(self, manager):
        """Test FFmpeg command building for single destination"""
        input_url = "rtsp://camera.local/stream"
        output_urls = ["rtmp://youtube.com/stream"]
        profile = EncodingProfile.reliability_profile(manager.hw_capabilities)
        
        command = manager._build_ffmpeg_command(input_url, output_urls, profile)
        
        # Check basic structure
        assert command[0] == 'ffmpeg'
        assert '-i' in command
        assert input_url in command
        assert '-c:v' in command
        assert 'h264_videotoolbox' in command
        assert output_urls[0] in command
    
    async def test_build_ffmpeg_command_multiple_outputs(self, manager):
        """Test FFmpeg command building for multiple destinations"""
        input_url = "rtsp://camera.local/stream"
        output_urls = [
            "rtmp://youtube.com/stream",
            "rtmp://facebook.com/stream",
            "rtmp://twitch.tv/stream"
        ]
        profile = EncodingProfile.reliability_profile(manager.hw_capabilities)
        
        command = manager._build_ffmpeg_command(input_url, output_urls, profile)
        
        # Should use tee muxer for multiple outputs
        assert '-f' in command
        assert 'tee' in command
        
        # Check all outputs are in the tee string
        tee_string = command[-1]
        for url in output_urls:
            assert url in tee_string
    
    async def test_start_stream_success(self, manager):
        """Test successful stream start"""
        stream_id = 1
        input_url = "rtsp://camera.local/stream"
        output_urls = ["rtmp://youtube.com/stream"]
        
        # Mock subprocess
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            stream_process = await manager.start_stream(
                stream_id=stream_id,
                input_url=input_url,
                output_urls=output_urls
            )
        
        assert stream_process.stream_id == stream_id
        assert stream_process.status == StreamStatus.RUNNING
        assert stream_process.process is not None
        assert stream_id in manager.processes
    
    async def test_start_stream_already_running(self, manager):
        """Test error when starting already running stream"""
        stream_id = 1
        
        # Add existing running stream
        manager.processes[stream_id] = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.RUNNING
        )
        
        with pytest.raises(RuntimeError, match="already running"):
            await manager.start_stream(
                stream_id=stream_id,
                input_url="rtsp://test",
                output_urls=["rtmp://test"]
            )
    
    async def test_start_stream_max_concurrent_limit(self, manager):
        """Test maximum concurrent stream limit"""
        # Fill up to max concurrent streams
        for i in range(manager.hw_capabilities.max_concurrent_streams):
            manager.processes[i] = StreamProcess(
                stream_id=i,
                status=StreamStatus.RUNNING
            )
        
        # Try to start one more
        with pytest.raises(RuntimeError, match="Maximum concurrent streams"):
            await manager.start_stream(
                stream_id=999,
                input_url="rtsp://test",
                output_urls=["rtmp://test"]
            )
    
    async def test_stop_stream(self, manager):
        """Test stream stop"""
        stream_id = 1
        
        # Create mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.terminate = Mock()
        mock_process.wait = AsyncMock(return_value=0)
        
        # Add stream
        manager.processes[stream_id] = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.RUNNING,
            process=mock_process
        )
        
        # Create a real async task that we can cancel
        async def dummy_monitor():
            try:
                await asyncio.sleep(1000)
            except asyncio.CancelledError:
                pass
        
        mock_task = asyncio.create_task(dummy_monitor())
        manager._monitoring_tasks[stream_id] = mock_task
        
        await manager.stop_stream(stream_id)
        
        assert manager.processes[stream_id].status == StreamStatus.STOPPED
        mock_process.terminate.assert_called_once()
    
    async def test_parse_ffmpeg_output(self, manager):
        """Test FFmpeg output parsing"""
        stream_id = 1
        
        # Create stream with metrics
        stream_process = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.RUNNING
        )
        manager.processes[stream_id] = stream_process
        
        # Sample FFmpeg output line
        ffmpeg_output = "frame= 1234 fps=30.0 q=28.0 size=12345kB time=00:01:23.45 bitrate=4500.5kbits/s speed=1.00x drop=5"
        
        manager._parse_ffmpeg_output(stream_id, ffmpeg_output)
        
        metrics = stream_process.metrics
        assert metrics.framerate_actual == 30.0
        assert metrics.bitrate_current == pytest.approx(4.5, rel=0.1)  # 4500.5 kbits/s = 4.5 Mbps
        assert metrics.dropped_frames == 5
    
    async def test_restart_stream_backoff(self, manager):
        """Test exponential backoff on restart"""
        stream_id = 1
        
        # Create mock process
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')
        
        # Add stream
        stream_process = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.ERROR,
            process=mock_process,
            command=['ffmpeg', '-i', 'test'],
            retry_count=2  # 3rd retry
        )
        manager.processes[stream_id] = stream_process
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.sleep') as mock_sleep:
                await manager.restart_stream(stream_id)
                
                # Should wait 2^3 = 8 seconds
                mock_sleep.assert_called_once_with(8)
        
        assert stream_process.retry_count == 3
        assert stream_process.status == StreamStatus.RUNNING
    
    async def test_restart_stream_max_retries(self, manager):
        """Test max retries exceeded"""
        stream_id = 1
        
        # Create stream at max retries
        stream_process = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.ERROR,
            retry_count=10
        )
        manager.processes[stream_id] = stream_process
        
        with pytest.raises(RuntimeError, match="Max retries exceeded"):
            await manager.restart_stream(stream_id)
        
        assert stream_process.status == StreamStatus.ERROR
    
    async def test_get_stream_status(self, manager):
        """Test getting stream status"""
        stream_id = 1
        
        # Add stream
        stream_process = StreamProcess(
            stream_id=stream_id,
            status=StreamStatus.RUNNING
        )
        manager.processes[stream_id] = stream_process
        
        status = await manager.get_stream_status(stream_id)
        
        assert status is not None
        assert status.stream_id == stream_id
        assert status.status == StreamStatus.RUNNING
    
    async def test_get_all_streams(self, manager):
        """Test getting all streams"""
        # Add multiple streams
        for i in range(3):
            manager.processes[i] = StreamProcess(
                stream_id=i,
                status=StreamStatus.RUNNING
            )
        
        all_streams = await manager.get_all_streams()
        
        assert len(all_streams) == 3
        assert all(isinstance(s, StreamProcess) for s in all_streams)
    
    async def test_graceful_shutdown(self, manager):
        """Test graceful shutdown with SIGTERM"""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.wait = AsyncMock(return_value=0)
        
        await manager._graceful_shutdown(mock_process, graceful=True)
        
        mock_process.terminate.assert_called_once()
        assert mock_process.kill.call_count == 0  # Should not force kill
    
    async def test_graceful_shutdown_timeout_then_kill(self, manager):
        """Test SIGKILL after SIGTERM timeout"""
        mock_process = AsyncMock()
        mock_process.pid = 12345
        
        # Simulate timeout on wait
        async def wait_with_timeout():
            await asyncio.sleep(10)  # Will timeout
            return 0
        
        mock_process.wait = wait_with_timeout
        
        # Patch wait_for to immediately timeout
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            await manager._graceful_shutdown(mock_process, graceful=True)
        
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()


class TestStreamMetrics:
    """Test stream metrics"""
    
    def test_stream_metrics_initialization(self):
        """Test metrics start with correct defaults"""
        metrics = StreamMetrics()
        
        assert metrics.bitrate_current == 0.0
        assert metrics.framerate_actual == 0.0
        assert metrics.dropped_frames == 0
        assert metrics.uptime_seconds == 0
        assert isinstance(metrics.last_update, datetime)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

