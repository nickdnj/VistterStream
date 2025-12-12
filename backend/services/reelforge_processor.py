"""
ReelForge Processing Service
Handles the full processing pipeline: portrait conversion, AI content generation, text overlay rendering.
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.reelforge import ReelPost, ReelTemplate

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ReelForgeProcessor:
    """
    Processes captured clips through the full pipeline:
    1. Portrait conversion with panning effect
    2. AI content generation (headlines)
    3. Text overlay rendering
    4. Thumbnail generation
    """
    
    def __init__(self):
        # Directory paths
        self._uploads_dir = Path(__file__).parent.parent / "uploads" / "reelforge"
        self._clips_dir = self._uploads_dir / "clips"
        self._portraits_dir = self._uploads_dir / "portraits"
        self._outputs_dir = self._uploads_dir / "outputs"
        self._thumbnails_dir = self._uploads_dir / "thumbnails"
        
        for dir_path in [self._clips_dir, self._portraits_dir, self._outputs_dir, self._thumbnails_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self._processing_lock = asyncio.Lock()
        self._active_processing: Dict[int, bool] = {}
    
    async def process_post(self, post_id: int) -> bool:
        """Process a captured post through the full pipeline"""
        
        # Prevent duplicate processing
        async with self._processing_lock:
            if post_id in self._active_processing:
                logger.warning(f"🎬 ReelForge: Post {post_id} already being processed")
                return False
            self._active_processing[post_id] = True
        
        db = SessionLocal()
        
        try:
            # Load post
            post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
            if not post:
                logger.error(f"🎬 ReelForge: Post {post_id} not found")
                return False
            
            if not post.source_clip_path or not Path(post.source_clip_path).exists():
                logger.error(f"🎬 ReelForge: Source clip not found for post {post_id}")
                post.status = "failed"
                post.error_message = "Source clip not found"
                db.commit()
                return False
            
            # Update status
            post.status = "processing"
            post.processing_started_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"🎬 ReelForge: Starting processing for post {post_id}")
            
            # Load template for settings
            template = None
            if post.template_id:
                template = db.query(ReelTemplate).filter(ReelTemplate.id == post.template_id).first()
            
            # Step 1: Portrait conversion with panning
            logger.info(f"🎬 ReelForge: Step 1 - Portrait conversion")
            portrait_path = await self._convert_to_portrait(
                post_id=post_id,
                source_path=post.source_clip_path,
                pan_direction=template.pan_direction if template else "left_to_right",
                pan_speed=template.pan_speed if template else 1.0,
                clip_duration=template.clip_duration if template else 30
            )
            
            if not portrait_path:
                post.status = "failed"
                post.error_message = "Portrait conversion failed"
                db.commit()
                return False
            
            post.portrait_clip_path = portrait_path
            db.commit()
            
            # Step 2: AI content generation
            logger.info(f"🎬 ReelForge: Step 2 - AI content generation")
            headlines = await self._generate_ai_content(
                template=template,
                clip_duration=template.clip_duration if template else 30
            )
            
            post.generated_headlines = headlines
            db.commit()
            
            # Step 3: Text overlay rendering
            logger.info(f"🎬 ReelForge: Step 3 - Text overlay rendering")
            output_path = await self._render_text_overlays(
                post_id=post_id,
                portrait_path=portrait_path,
                headlines=headlines,
                template=template
            )
            
            if not output_path:
                post.status = "failed"
                post.error_message = "Text overlay rendering failed"
                db.commit()
                return False
            
            post.output_path = output_path
            db.commit()
            
            # Step 4: Thumbnail generation
            logger.info(f"🎬 ReelForge: Step 4 - Thumbnail generation")
            thumbnail_path = await self._generate_thumbnail(
                post_id=post_id,
                video_path=output_path
            )
            
            if thumbnail_path:
                post.thumbnail_path = thumbnail_path
            
            # Mark as ready
            post.status = "ready"
            post.processing_completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"🎬 ReelForge: Processing complete for post {post_id}")
            return True
            
        except Exception as e:
            logger.error(f"🎬 ReelForge: Processing failed for post {post_id}: {e}")
            
            try:
                post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
                if post:
                    post.status = "failed"
                    post.error_message = str(e)[:500]
                    db.commit()
            except:
                pass
            
            return False
        
        finally:
            async with self._processing_lock:
                if post_id in self._active_processing:
                    del self._active_processing[post_id]
            db.close()
    
    async def _convert_to_portrait(
        self,
        post_id: int,
        source_path: str,
        pan_direction: str,
        pan_speed: float,
        clip_duration: int
    ) -> Optional[str]:
        """
        Convert landscape video to portrait (9:16) with panning effect.
        
        The magic FFmpeg filter:
        - Crops a 9:16 portion from the 16:9 source
        - Pans across the source video over time
        """
        try:
            output_path = str(self._portraits_dir / f"{post_id}.mp4")
            
            # Calculate crop dimensions for 9:16 from 16:9
            # For 1920x1080 input: crop to 607x1080 (9:16 ratio)
            # We'll use dynamic expressions to handle any input size
            
            # Pan expression based on direction
            # t = time, iw = input width, ow = output width (crop width)
            # For 30 second clip: t goes from 0 to 30
            duration = clip_duration * pan_speed
            
            if pan_direction == "left_to_right":
                # Pan from left edge to right edge
                x_expr = f"'t*(iw-ih*9/16)/{duration}'"
            elif pan_direction == "right_to_left":
                # Pan from right edge to left edge
                x_expr = f"'(iw-ih*9/16)-t*(iw-ih*9/16)/{duration}'"
            else:  # center
                # Stay centered
                x_expr = "'(iw-ih*9/16)/2'"
            
            # Build FFmpeg command
            # crop=out_w:out_h:x:y
            # out_w = ih*9/16 (height * 9/16 to get portrait width)
            # out_h = ih (full height)
            # x = dynamic pan expression
            # y = 0 (top of frame)
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',
                '-i', source_path,
                '-vf', f"crop=ih*9/16:ih:{x_expr}:0,scale=1080:1920",
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',
                output_path
            ]
            
            logger.debug(f"🎬 ReelForge: Portrait conversion command: {' '.join(ffmpeg_cmd[:10])}...")
            
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and Path(output_path).exists():
                logger.info(f"🎬 ReelForge: Portrait conversion complete for post {post_id}")
                return output_path
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"🎬 ReelForge: Portrait conversion failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"🎬 ReelForge: Portrait conversion error: {e}")
            return None
    
    async def _generate_ai_content(
        self,
        template: Optional[ReelTemplate],
        clip_duration: int
    ) -> List[Dict]:
        """
        Generate AI headlines using the template configuration.
        Returns list of headlines with timing info.
        """
        try:
            # Import AI content generator
            from utils.ai_content import generate_headlines
            
            if template and template.ai_config:
                ai_config = template.ai_config
            else:
                # Default config
                ai_config = {
                    "tone": "casual",
                    "voice": "friendly guide",
                    "instructions": "Create engaging short-form video content",
                    "prompt_1": "Opening hook",
                    "prompt_2": "Main content",
                    "prompt_3": "Supporting detail",
                    "prompt_4": "Call to action",
                    "prompt_5": "Sign off"
                }
            
            # Generate headlines
            headlines_text = await generate_headlines(ai_config)
            
            # Calculate timing (5 slides for the clip duration)
            num_slides = 5
            slide_duration = clip_duration / num_slides
            
            headlines = []
            for i, text in enumerate(headlines_text[:num_slides]):
                headlines.append({
                    "text": text,
                    "start_time": i * slide_duration,
                    "duration": slide_duration
                })
            
            logger.info(f"🎬 ReelForge: Generated {len(headlines)} headlines")
            return headlines
            
        except ImportError:
            logger.warning("🎬 ReelForge: AI content generator not available, using placeholders")
            # Return placeholder headlines
            num_slides = 5
            slide_duration = clip_duration / num_slides
            return [
                {"text": f"Headline {i+1}", "start_time": i * slide_duration, "duration": slide_duration}
                for i in range(num_slides)
            ]
        except Exception as e:
            logger.error(f"🎬 ReelForge: AI content generation error: {e}")
            # Return placeholder headlines on error
            num_slides = 5
            slide_duration = clip_duration / num_slides
            return [
                {"text": f"Headline {i+1}", "start_time": i * slide_duration, "duration": slide_duration}
                for i in range(num_slides)
            ]
    
    def _split_into_lines(self, text: str, max_chars: int = 25) -> List[str]:
        """Split text into multiple lines for word wrapping"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > max_chars and current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + 1
        
        if current_line:
            lines.append(" ".join(current_line))
        return lines if lines else [text]
    
    async def _render_text_overlays(
        self,
        post_id: int,
        portrait_path: str,
        headlines: List[Dict],
        template: Optional[ReelTemplate]
    ) -> Optional[str]:
        """
        Render text overlays onto the portrait video using FFmpeg drawtext filter.
        Features:
        - Vertically centered text
        - Word wrapping for long text
        - Typewriter effect (words appear one at a time)
        """
        try:
            output_path = str(self._outputs_dir / f"{post_id}.mp4")
            
            # Get styling from template or use defaults
            font_family = template.font_family if template else "Arial"
            font_size = template.font_size if template else 48
            text_color = template.text_color if template else "#FFFFFF"
            text_shadow = template.text_shadow if template else True
            text_background = template.text_background if template else "rgba(0,0,0,0.5)"
            text_position_y = template.text_position_y if template else 0.5  # Centered vertically
            
            # Convert hex color to FFmpeg format
            if text_color.startswith("#"):
                text_color = text_color[1:]  # Remove #
            
            # Build drawtext filters with typewriter effect
            drawtext_filters = []
            
            for headline in headlines:
                text = headline["text"]
                headline_start = headline["start_time"]
                headline_end = headline_start + headline["duration"]
                
                # Split text into lines for word wrapping
                lines = self._split_into_lines(text, max_chars=25)
                
                # Calculate vertical positioning for multiple lines
                # Center the text block around the specified Y position
                line_height = font_size * 1.4  # Line height with some spacing
                total_height = len(lines) * line_height
                
                # For typewriter effect: reveal lines one at a time
                # Use 60% of headline duration for line reveal, 40% for all lines visible
                reveal_duration = headline["duration"] * 0.6
                line_interval = reveal_duration / len(lines) if len(lines) > 0 else 0
                
                # Create drawtext filter for each line with staggered timing
                for line_idx, line in enumerate(lines):
                    line_start = headline_start + (line_idx * line_interval)
                    
                    # Escape special characters for FFmpeg
                    line_escaped = line.replace("'", "'\\''").replace(":", "\\:").replace("\\", "\\\\")
                    
                    # Calculate Y position - center the block, then offset each line
                    y_offset = line_idx * line_height
                    # Center text block vertically, accounting for total height
                    y_expr = f"(h*{text_position_y} - {total_height/2} + {y_offset})"
                    
                    # Build filter string
                    filter_str = (
                        f"drawtext=text='{line_escaped}'"
                        f":fontsize={font_size}"
                        f":fontcolor=white"
                        f":x=(w-text_w)/2"  # Center horizontally
                        f":y={y_expr}"
                        f":enable='between(t,{line_start:.2f},{headline_end:.2f})'"
                    )
                    
                    # Add shadow for readability
                    if text_shadow:
                        filter_str += f":shadowcolor=black:shadowx=3:shadowy=3"
                    
                    drawtext_filters.append(filter_str)
            
            if not drawtext_filters:
                # No text to render, just copy the video
                import shutil
                shutil.copy(portrait_path, output_path)
                return output_path
            
            # Combine all filters
            filter_complex = ",".join(drawtext_filters)
            
            # Build FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',
                '-i', portrait_path,
                '-vf', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'copy',
                '-movflags', '+faststart',
                output_path
            ]
            
            logger.debug(f"🎬 ReelForge: Text overlay command with {len(drawtext_filters)} word filters")
            
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and Path(output_path).exists():
                logger.info(f"🎬 ReelForge: Text overlay rendering complete for post {post_id}")
                return output_path
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"🎬 ReelForge: Text overlay rendering failed: {error_msg}")
                
                # If drawtext fails (e.g., font issues), try without overlays
                logger.info(f"🎬 ReelForge: Falling back to video without overlays")
                
                # Just copy the portrait video as output
                import shutil
                shutil.copy(portrait_path, output_path)
                
                if Path(output_path).exists():
                    return output_path
                
                return None
                
        except Exception as e:
            logger.error(f"🎬 ReelForge: Text overlay error: {e}")
            return None
    
    async def _generate_thumbnail(
        self,
        post_id: int,
        video_path: str,
        timestamp: float = 3.0
    ) -> Optional[str]:
        """Generate a thumbnail from the video at the specified timestamp"""
        try:
            output_path = str(self._thumbnails_dir / f"{post_id}.jpg")
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',
                '-i', video_path,
                '-ss', str(timestamp),
                '-vframes', '1',
                '-q:v', '2',  # High quality JPEG
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0 and Path(output_path).exists():
                logger.info(f"🎬 ReelForge: Thumbnail generated for post {post_id}")
                return output_path
            else:
                logger.warning(f"🎬 ReelForge: Thumbnail generation failed for post {post_id}")
                return None
                
        except Exception as e:
            logger.error(f"🎬 ReelForge: Thumbnail generation error: {e}")
            return None
    
    def get_status(self) -> dict:
        """Get processor status"""
        return {
            "active_processing": len(self._active_processing),
            "processing_posts": list(self._active_processing.keys())
        }


# Global instance
_processor: Optional[ReelForgeProcessor] = None


def get_reelforge_processor() -> ReelForgeProcessor:
    """Get the global ReelForge processor"""
    global _processor
    if _processor is None:
        _processor = ReelForgeProcessor()
    return _processor
