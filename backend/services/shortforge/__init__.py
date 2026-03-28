"""
ShortForge — Automated YouTube Shorts from live camera feeds

Pipeline stages:
1. MomentDetector — lightweight OpenCV frame analysis on RTSP feed
2. ClipCapture — FFmpeg ring buffer + clip extraction
3. HeadlineGenerator — AI vision API (GPT-4o-mini) for contextual headlines
4. VerticalRenderer — FFmpeg portrait crop + overlay compositing
5. Publisher — YouTube Data API v3 shorts upload
6. Scheduler — Posting cadence, frequency caps, quiet hours
"""
