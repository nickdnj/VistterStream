"""
Hardware Acceleration Detector for FFmpeg
Detects available hardware encoders on Pi 5 and Mac platforms.

References:
    See docs/StreamingPipeline-TechnicalSpec.md §"Hardware Acceleration"
"""

import os
import platform
import subprocess
import asyncio
from typing import Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HardwareCapabilities:
    """Hardware encoder capabilities detected on the system"""
    encoder: str  # 'h264_v4l2m2m', 'h264_videotoolbox', or 'libx264'
    decoder: Optional[str]
    platform: str  # 'pi5', 'mac', 'linux', 'unknown'
    max_concurrent_streams: int
    supports_hardware: bool


class HardwareDetector:
    """
    Detects available hardware encoders and capabilities.
    
    Detection priority:
    1. Raspberry Pi 5 V4L2 (h264_v4l2m2m)
    2. Mac VideoToolbox (h264_videotoolbox)
    3. Software fallback (libx264)
    """
    
    def __init__(self):
        self.capabilities: Optional[HardwareCapabilities] = None
        self._ffmpeg_encoders: List[str] = []
    
    async def detect(self) -> HardwareCapabilities:
        """
        Detect hardware encoder capabilities.
        
        Returns:
            HardwareCapabilities with detected encoder and limits
        """
        logger.info("Detecting hardware acceleration capabilities...")
        
        # Get available FFmpeg encoders
        await self._probe_ffmpeg_encoders()
        
        # Detect platform and hardware
        system = platform.system()
        machine = platform.machine()
        
        if self._is_pi5():
            capabilities = await self._detect_pi5()
        elif system == 'Darwin':  # macOS
            capabilities = await self._detect_mac()
        else:
            capabilities = self._fallback_software()
        
        self.capabilities = capabilities
        logger.info(f"Hardware detection complete: {capabilities.encoder} on {capabilities.platform}")
        logger.info(f"Max concurrent streams: {capabilities.max_concurrent_streams}")
        
        return capabilities
    
    def _is_pi5(self) -> bool:
        """Check if running on Raspberry Pi 5"""
        try:
            # Check for Pi 5 specific device tree
            if os.path.exists('/proc/device-tree/model'):
                with open('/proc/device-tree/model', 'r') as f:
                    model = f.read()
                    return 'Raspberry Pi 5' in model
        except Exception:
            pass
        
        # Check for V4L2 encoder device (Pi 5 specific)
        return os.path.exists('/dev/video11')
    
    async def _detect_pi5(self) -> HardwareCapabilities:
        """Detect Raspberry Pi 5 hardware capabilities"""
        logger.info("Raspberry Pi 5 detected")
        
        # Check if h264_v4l2m2m encoder is available
        if 'h264_v4l2m2m' in self._ffmpeg_encoders:
            # Verify encoder device is accessible
            if os.path.exists('/dev/video11') and os.access('/dev/video11', os.R_OK | os.W_OK):
                logger.info("Pi 5 hardware encoder available: h264_v4l2m2m")
                return HardwareCapabilities(
                    encoder='h264_v4l2m2m',
                    decoder='h264_v4l2m2m',
                    platform='pi5',
                    max_concurrent_streams=3,  # 3x 1080p30
                    supports_hardware=True
                )
            else:
                logger.warning("/dev/video11 not accessible, falling back to software encoding")
        else:
            logger.warning("h264_v4l2m2m not available in FFmpeg, falling back to software")
        
        return self._fallback_software()
    
    async def _detect_mac(self) -> HardwareCapabilities:
        """Detect Mac VideoToolbox hardware capabilities"""
        logger.info("macOS detected")
        
        # Check if VideoToolbox encoder is available
        if 'h264_videotoolbox' in self._ffmpeg_encoders:
            # Test if VideoToolbox is actually working
            if await self._test_videotoolbox():
                logger.info("Mac hardware encoder available: h264_videotoolbox")
                
                # M-series Macs have virtually unlimited encoding capacity
                # Set conservative limit for safety
                max_streams = 10 if self._is_apple_silicon() else 5
                
                return HardwareCapabilities(
                    encoder='h264_videotoolbox',
                    decoder='h264_videotoolbox',
                    platform='mac',
                    max_concurrent_streams=max_streams,
                    supports_hardware=True
                )
            else:
                logger.warning("VideoToolbox test failed, falling back to software encoding")
        else:
            logger.warning("h264_videotoolbox not available in FFmpeg, falling back to software")
        
        return self._fallback_software()
    
    def _fallback_software(self) -> HardwareCapabilities:
        """Fallback to software encoding"""
        logger.info("Using software encoder: libx264")
        
        return HardwareCapabilities(
            encoder='libx264',
            decoder=None,
            platform='software',
            max_concurrent_streams=2,  # Limited by CPU
            supports_hardware=False
        )
    
    async def _probe_ffmpeg_encoders(self) -> None:
        """Probe available FFmpeg encoders"""
        try:
            result = await asyncio.create_subprocess_exec(
                'ffmpeg', '-encoders',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await result.communicate()
            output = stdout.decode('utf-8', errors='ignore')
            
            # Parse encoder list
            self._ffmpeg_encoders = []
            for line in output.split('\n'):
                # Lines with encoders start with " V" or " A"
                if line.strip().startswith('V') and 'h264' in line.lower():
                    # Extract encoder name (format: " V..... encodername ...")
                    parts = line.split()
                    if len(parts) >= 2:
                        encoder_name = parts[1]
                        self._ffmpeg_encoders.append(encoder_name)
            
            logger.debug(f"Available H.264 encoders: {', '.join(self._ffmpeg_encoders)}")
            
        except FileNotFoundError:
            logger.error("FFmpeg not found! Please install FFmpeg.")
            raise RuntimeError("FFmpeg is required but not installed")
        except Exception as e:
            logger.error(f"Failed to probe FFmpeg encoders: {e}")
            # Don't fail, just continue with empty list
    
    async def _test_videotoolbox(self) -> bool:
        """Test if VideoToolbox encoder actually works"""
        try:
            # Quick test: try to encode a 1-second test pattern
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', 'testsrc=duration=1:size=320x240:rate=30',
                '-c:v', 'h264_videotoolbox',
                '-t', '1',
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait with timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
                return process.returncode == 0
            except asyncio.TimeoutError:
                process.kill()
                return False
                
        except Exception as e:
            logger.debug(f"VideoToolbox test failed: {e}")
            return False
    
    def _is_apple_silicon(self) -> bool:
        """Check if running on Apple Silicon (M-series)"""
        return platform.machine() == 'arm64' and platform.system() == 'Darwin'
    
    def get_encoder_command_args(self) -> List[str]:
        """
        Get FFmpeg command arguments for the detected encoder.
        
        Returns:
            List of FFmpeg arguments for hardware-accelerated encoding
        """
        if not self.capabilities:
            raise RuntimeError("Hardware detection not run. Call detect() first.")
        
        encoder = self.capabilities.encoder
        
        if encoder == 'h264_v4l2m2m':
            # Pi 5 V4L2 encoder args
            return [
                '-c:v', 'h264_v4l2m2m',
                '-num_output_buffers', '32',
                '-num_capture_buffers', '16'
            ]
        
        elif encoder == 'h264_videotoolbox':
            # Mac VideoToolbox encoder args
            return [
                '-c:v', 'h264_videotoolbox',
                '-allow_sw', '1',  # Allow software fallback if HW busy
                '-realtime', '1'
            ]
        
        else:  # libx264 software
            return [
                '-c:v', 'libx264',
                '-preset', 'veryfast',  # Fastest software encoding
                '-tune', 'zerolatency'
            ]


# Global detector instance
_detector: Optional[HardwareDetector] = None


async def get_hardware_capabilities() -> HardwareCapabilities:
    """
    Get hardware capabilities (singleton pattern).
    
    Returns:
        HardwareCapabilities for the current system
    """
    global _detector
    
    if _detector is None:
        _detector = HardwareDetector()
        await _detector.detect()
    
    return _detector.capabilities


def get_detector() -> HardwareDetector:
    """Get the global hardware detector instance"""
    global _detector
    
    if _detector is None:
        _detector = HardwareDetector()
    
    return _detector

