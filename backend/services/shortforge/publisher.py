"""
Publisher — YouTube Shorts upload via Data API v3.

Uses the existing YouTube OAuth credentials from ReelForge settings
(or ShortForge-specific credentials if configured).
Handles upload, metadata, retry with exponential backoff.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from models.database import SessionLocal
from models.shortforge import Clip, PublishedShort, Moment, ShortForgeConfig
from models.database import ReelForgeSettings
from utils.crypto import decrypt

logger = logging.getLogger(__name__)

# YouTube Shorts metadata
SHORTS_CATEGORY_ID = "22"  # People & Blogs (common for Shorts)
MAX_RETRIES = 3
RETRY_DELAYS = [60, 300, 1800]  # 1min, 5min, 30min


async def publish_short(
    clip_id: int,
    config: ShortForgeConfig,
) -> Optional[int]:
    """
    Upload a rendered vertical clip to YouTube as a Short.

    Returns the PublishedShort ID, or None on failure.
    """
    db = SessionLocal()
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip or not clip.rendered_path:
            logger.error("Clip %d not found or not rendered", clip_id)
            return None

        rendered_path = Path(clip.rendered_path)
        if not rendered_path.exists():
            logger.error("Rendered file missing: %s", clip.rendered_path)
            return None

        moment = db.query(Moment).filter(Moment.id == clip.moment_id).first()

        # Build title and description
        title = clip.headline or "Live from the marina"
        if len(title) > 95:
            title = title[:92] + "..."
        # YouTube requires #Shorts in title or description
        title_with_tag = f"{title} #Shorts"

        description = _build_description(clip, moment, config)
        tags = [t.strip() for t in (config.default_tags or "").split(",") if t.strip()]
        tags.extend(["Shorts", "marina", "live camera"])

        # Get YouTube credentials
        credentials = await _get_youtube_credentials(db)
        if not credentials:
            logger.error("No YouTube credentials available for publishing")
            return await _create_failed_short(db, clip_id, "No YouTube credentials")

        # Upload with retry
        for attempt in range(MAX_RETRIES):
            try:
                video_id = await asyncio.to_thread(
                    _upload_to_youtube,
                    credentials,
                    str(rendered_path),
                    title_with_tag,
                    description,
                    tags,
                )

                if video_id:
                    # Create published short record
                    short = PublishedShort(
                        clip_id=clip_id,
                        youtube_video_id=video_id,
                        title=title,
                        description=description,
                        tags=",".join(tags),
                        published_at=datetime.now(timezone.utc),
                        status="published",
                    )
                    db.add(short)

                    # Update moment status
                    if moment:
                        moment.status = "published"

                    db.commit()
                    db.refresh(short)
                    logger.info("Published short: id=%d youtube=%s title='%s'", short.id, video_id, title)
                    return short.id

            except Exception as e:
                logger.warning("Upload attempt %d failed: %s", attempt + 1, e)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])

        # All retries failed
        return await _create_failed_short(db, clip_id, f"Upload failed after {MAX_RETRIES} attempts")

    except Exception:
        logger.exception("Error publishing short for clip %d", clip_id)
        return None
    finally:
        db.close()


def _upload_to_youtube(
    credentials: Credentials,
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
) -> Optional[str]:
    """Synchronous YouTube upload (runs in thread)."""
    youtube = build("youtube", "v3", credentials=credentials)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": SHORTS_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        file_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024,  # 1MB chunks
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response.get("id")
    logger.info("YouTube upload complete: %s", video_id)
    return video_id


async def _get_youtube_credentials(db) -> Optional[Credentials]:
    """Get YouTube OAuth credentials from ReelForge settings (shared)."""
    try:
        rf_settings = db.query(ReelForgeSettings).first()
        if not rf_settings or not rf_settings.youtube_connected:
            return None

        client_id = rf_settings.youtube_client_id
        client_secret = decrypt(rf_settings.youtube_client_secret_enc) if rf_settings.youtube_client_secret_enc else None
        refresh_token = decrypt(rf_settings.youtube_refresh_token_enc) if rf_settings.youtube_refresh_token_enc else None

        if not all([client_id, client_secret, refresh_token]):
            return None

        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
        )
        return credentials

    except Exception:
        logger.exception("Failed to load YouTube credentials")
        return None


def _build_description(clip: Clip, moment: Optional[Moment], config: ShortForgeConfig) -> str:
    """Build YouTube description from template."""
    template = config.description_template or "{{headline}} | Live camera"
    desc = template.replace("{{headline}}", clip.headline or "")
    desc = desc.replace("{{location}}", "Wharfside Marina, Monmouth Beach NJ")
    desc = desc.replace("{{conditions}}", "")

    if moment:
        desc += f"\n\nDetected: {moment.trigger_type} (score: {moment.score:.2f})"
    desc += "\n\nCaptured automatically by ShortForge | VistterStream"
    return desc


async def _create_failed_short(db, clip_id: int, error: str) -> None:
    """Create a failed short record."""
    short = PublishedShort(
        clip_id=clip_id,
        status="failed",
        error_message=error,
    )
    db.add(short)
    db.commit()
    logger.error("Short publishing failed for clip %d: %s", clip_id, error)
    return None


async def refresh_view_counts(limit: int = 50):
    """Batch refresh YouTube view counts for recent published shorts."""
    db = SessionLocal()
    try:
        shorts = (
            db.query(PublishedShort)
            .filter(
                PublishedShort.status == "published",
                PublishedShort.youtube_video_id.isnot(None),
            )
            .order_by(PublishedShort.published_at.desc())
            .limit(limit)
            .all()
        )

        if not shorts:
            return

        credentials = await _get_youtube_credentials(db)
        if not credentials:
            return

        # Batch fetch by video IDs (up to 50 per API call)
        video_ids = [s.youtube_video_id for s in shorts if s.youtube_video_id]
        if not video_ids:
            return

        try:
            youtube = build("youtube", "v3", credentials=credentials)
            response = youtube.videos().list(
                part="statistics",
                id=",".join(video_ids),
            ).execute()

            views_map = {}
            for item in response.get("items", []):
                vid = item["id"]
                views = int(item.get("statistics", {}).get("viewCount", 0))
                views_map[vid] = views

            for short in shorts:
                if short.youtube_video_id in views_map:
                    short.views = views_map[short.youtube_video_id]

            db.commit()
            logger.info("Refreshed view counts for %d shorts", len(views_map))

        except Exception:
            logger.exception("Failed to refresh view counts")

    finally:
        db.close()
