"""
ReelForge API endpoints - Automated social media content generation

Note: This is the MVP version focused on content generation only.
Posts are downloaded manually and uploaded by the user to social platforms.
Automatic publishing will be available in VistterStream Cloud.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import base64

from models.database import get_db, Camera, Preset, ReelForgeSettings
from models.reelforge import ReelTemplate, ReelPost, ReelPublishTarget, ReelExport, ReelCaptureQueue
from models.schemas import (
    ReelTemplateCreate, ReelTemplateUpdate, ReelTemplate as ReelTemplateSchema,
    ReelPostCreate, ReelPostQueue, ReelPost as ReelPostSchema, ReelPostWithDetails,
    ReelPublishTargetCreate, ReelPublishTargetUpdate, ReelPublishTarget as ReelPublishTargetSchema,
    ReelExportCreate, ReelExportUpdate, ReelExport as ReelExportSchema,
    CameraWithPresets, Preset as PresetSchema,
    ReelCaptureQueueItem, ReelPostStatus,
    ReelForgeSettingsUpdate, ReelForgeSettings as ReelForgeSettingsSchema,
    ReelForgeSettingsTestResult
)

router = APIRouter(prefix="/api/reelforge", tags=["reelforge"])


# ============================================================================
# Settings Endpoints
# ============================================================================

def _encrypt_api_key(api_key: str) -> str:
    """Simple base64 encoding for API key storage (in production, use proper encryption)"""
    return base64.b64encode(api_key.encode()).decode()


def _decrypt_api_key(encrypted: str) -> str:
    """Decode base64 encoded API key"""
    return base64.b64decode(encrypted.encode()).decode()


@router.get("/settings", response_model=ReelForgeSettingsSchema)
def get_settings(db: Session = Depends(get_db)):
    """Get ReelForge settings"""
    settings = db.query(ReelForgeSettings).first()
    
    # If no settings exist, create default settings
    if not settings:
        settings = ReelForgeSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Return with has_api_key flag
    return {
        "id": settings.id,
        "openai_model": settings.openai_model,
        "system_prompt": settings.system_prompt,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "default_template_id": settings.default_template_id,
        "has_api_key": bool(settings.openai_api_key_enc),
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }


@router.post("/settings", response_model=ReelForgeSettingsSchema)
def update_settings(
    settings_update: ReelForgeSettingsUpdate,
    db: Session = Depends(get_db)
):
    """Update ReelForge settings"""
    settings = db.query(ReelForgeSettings).first()
    
    # If no settings exist, create them
    if not settings:
        settings = ReelForgeSettings()
        db.add(settings)
    
    # Update fields
    if settings_update.openai_api_key is not None:
        if settings_update.openai_api_key == "":
            settings.openai_api_key_enc = None
        else:
            settings.openai_api_key_enc = _encrypt_api_key(settings_update.openai_api_key)
    
    if settings_update.openai_model is not None:
        settings.openai_model = settings_update.openai_model
    
    if settings_update.system_prompt is not None:
        settings.system_prompt = settings_update.system_prompt
    
    if settings_update.temperature is not None:
        settings.temperature = settings_update.temperature
    
    if settings_update.max_tokens is not None:
        settings.max_tokens = settings_update.max_tokens
    
    if settings_update.default_template_id is not None:
        settings.default_template_id = settings_update.default_template_id
    
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    
    return {
        "id": settings.id,
        "openai_model": settings.openai_model,
        "system_prompt": settings.system_prompt,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "default_template_id": settings.default_template_id,
        "has_api_key": bool(settings.openai_api_key_enc),
        "created_at": settings.created_at,
        "updated_at": settings.updated_at
    }


@router.post("/settings/test", response_model=ReelForgeSettingsTestResult)
def test_openai_connection(db: Session = Depends(get_db)):
    """Test the OpenAI connection with current settings"""
    settings = db.query(ReelForgeSettings).first()
    
    if not settings or not settings.openai_api_key_enc:
        return {
            "success": False,
            "message": "No API key configured",
            "model_used": None
        }
    
    try:
        from openai import OpenAI
        
        api_key = _decrypt_api_key(settings.openai_api_key_enc)
        client = OpenAI(api_key=api_key)
        
        # Make a simple test call (v1.0.0+ API)
        response = client.chat.completions.create(
            model=settings.openai_model or "gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Say 'Hello' in one word."}
            ],
            max_tokens=10
        )
        
        return {
            "success": True,
            "message": "Connection successful!",
            "model_used": settings.openai_model or "gpt-4o-mini"
        }
        
    except ImportError:
        return {
            "success": False,
            "message": "OpenAI package not installed",
            "model_used": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "model_used": None
        }


# ============================================================================
# Template Endpoints
# ============================================================================

@router.get("/templates", response_model=List[ReelTemplateSchema])
def get_templates(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all ReelForge templates"""
    query = db.query(ReelTemplate)
    if active_only:
        query = query.filter(ReelTemplate.is_active == True)
    return query.order_by(ReelTemplate.name).all()


@router.get("/templates/{template_id}", response_model=ReelTemplateSchema)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific template"""
    template = db.query(ReelTemplate).filter(ReelTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates", response_model=ReelTemplateSchema)
def create_template(template_data: ReelTemplateCreate, db: Session = Depends(get_db)):
    """Create a new template"""
    try:
        # Validate camera exists if specified
        if template_data.camera_id:
            camera = db.query(Camera).filter(Camera.id == template_data.camera_id).first()
            if not camera:
                raise HTTPException(status_code=400, detail="Camera not found")
        
        # Validate preset exists and belongs to camera if specified
        if template_data.preset_id:
            preset = db.query(Preset).filter(Preset.id == template_data.preset_id).first()
            if not preset:
                raise HTTPException(status_code=400, detail="Preset not found")
            if template_data.camera_id and preset.camera_id != template_data.camera_id:
                raise HTTPException(status_code=400, detail="Preset does not belong to specified camera")
        
        template = ReelTemplate(
            name=template_data.name,
            description=template_data.description,
            camera_id=template_data.camera_id,
            preset_id=template_data.preset_id,
            clip_duration=template_data.clip_duration,
            pan_direction=template_data.pan_direction.value if template_data.pan_direction else "left_to_right",
            pan_speed=template_data.pan_speed,
            ai_config=template_data.ai_config.model_dump() if template_data.ai_config else {},
            overlay_style=template_data.overlay_style,
            font_family=template_data.font_family,
            font_size=template_data.font_size,
            text_color=template_data.text_color,
            text_shadow=template_data.text_shadow,
            text_background=template_data.text_background,
            text_position_y=template_data.text_position_y,
            publish_mode=template_data.publish_mode.value if template_data.publish_mode else "manual",
            schedule_times=template_data.schedule_times,
            default_title_template=template_data.default_title_template,
            default_description_template=template_data.default_description_template,
            default_hashtags=template_data.default_hashtags
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.put("/templates/{template_id}", response_model=ReelTemplateSchema)
def update_template(
    template_id: int,
    template_data: ReelTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a template"""
    template = db.query(ReelTemplate).filter(ReelTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        update_dict = template_data.model_dump(exclude_unset=True)
        
        # Handle enum values
        if 'pan_direction' in update_dict and update_dict['pan_direction']:
            update_dict['pan_direction'] = update_dict['pan_direction'].value if hasattr(update_dict['pan_direction'], 'value') else update_dict['pan_direction']
        if 'publish_mode' in update_dict and update_dict['publish_mode']:
            update_dict['publish_mode'] = update_dict['publish_mode'].value if hasattr(update_dict['publish_mode'], 'value') else update_dict['publish_mode']
        
        # Handle ai_config
        if 'ai_config' in update_dict and update_dict['ai_config']:
            update_dict['ai_config'] = update_dict['ai_config'].model_dump() if hasattr(update_dict['ai_config'], 'model_dump') else update_dict['ai_config']
        
        for key, value in update_dict.items():
            setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        return template
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template"""
    template = db.query(ReelTemplate).filter(ReelTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    try:
        db.delete(template)
        db.commit()
        return {"message": "Template deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


# ============================================================================
# Post Endpoints
# ============================================================================

@router.get("/posts", response_model=List[ReelPostWithDetails])
def get_posts(
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all posts, optionally filtered by status"""
    query = db.query(ReelPost).options(
        joinedload(ReelPost.camera),
        joinedload(ReelPost.preset),
        joinedload(ReelPost.template)
    )
    
    if status:
        query = query.filter(ReelPost.status == status)
    
    posts = query.order_by(ReelPost.created_at.desc()).limit(limit).all()
    
    # Map to response with additional details
    result = []
    for post in posts:
        post_dict = {
            "id": post.id,
            "template_id": post.template_id,
            "status": post.status,
            "error_message": post.error_message,
            "camera_id": post.camera_id,
            "preset_id": post.preset_id,
            "source_clip_path": post.source_clip_path,
            "portrait_clip_path": post.portrait_clip_path,
            "output_path": post.output_path,
            "thumbnail_path": post.thumbnail_path,
            "generated_headlines": post.generated_headlines or [],
            "download_count": post.download_count or 0,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "capture_started_at": post.capture_started_at,
            "capture_completed_at": post.capture_completed_at,
            "processing_started_at": post.processing_started_at,
            "processing_completed_at": post.processing_completed_at,
            "camera_name": post.camera.name if post.camera else None,
            "preset_name": post.preset.name if post.preset else None,
            "template_name": post.template.name if post.template else None,
        }
        result.append(post_dict)
    
    return result


@router.get("/posts/{post_id}", response_model=ReelPostWithDetails)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a specific post"""
    post = db.query(ReelPost).options(
        joinedload(ReelPost.camera),
        joinedload(ReelPost.preset),
        joinedload(ReelPost.template)
    ).filter(ReelPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "id": post.id,
        "template_id": post.template_id,
        "status": post.status,
        "error_message": post.error_message,
        "camera_id": post.camera_id,
        "preset_id": post.preset_id,
        "source_clip_path": post.source_clip_path,
        "portrait_clip_path": post.portrait_clip_path,
        "output_path": post.output_path,
        "thumbnail_path": post.thumbnail_path,
        "generated_headlines": post.generated_headlines or [],
        "download_count": post.download_count or 0,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "capture_started_at": post.capture_started_at,
        "capture_completed_at": post.capture_completed_at,
        "processing_started_at": post.processing_started_at,
        "processing_completed_at": post.processing_completed_at,
        "camera_name": post.camera.name if post.camera else None,
        "preset_name": post.preset.name if post.preset else None,
        "template_name": post.template.name if post.template else None,
    }


@router.post("/posts/queue", response_model=ReelPostSchema)
def queue_capture(
    queue_data: ReelPostQueue,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Queue a new capture request
    
    Trigger modes:
    - 'next_view': Capture when timeline naturally switches to this camera/preset
    - 'scheduled': Capture at the specified scheduled_at time
    """
    try:
        # Validate camera exists
        camera = db.query(Camera).filter(Camera.id == queue_data.camera_id).first()
        if not camera:
            raise HTTPException(status_code=400, detail="Camera not found")

        # Validate preset exists and belongs to camera if specified
        if queue_data.preset_id:
            preset = db.query(Preset).filter(Preset.id == queue_data.preset_id).first()
            if not preset:
                raise HTTPException(status_code=400, detail="Preset not found")
            if preset.camera_id != queue_data.camera_id:
                raise HTTPException(status_code=400, detail="Preset does not belong to specified camera")

        # Validate template exists if specified
        if queue_data.template_id:
            template = db.query(ReelTemplate).filter(ReelTemplate.id == queue_data.template_id).first()
            if not template:
                raise HTTPException(status_code=400, detail="Template not found")
        
        # Validate trigger mode and scheduled_at
        trigger_mode = queue_data.trigger_mode or "next_view"
        if trigger_mode == "scheduled" and not queue_data.scheduled_at:
            raise HTTPException(status_code=400, detail="scheduled_at is required for scheduled trigger mode")

        # Create the post record
        post = ReelPost(
            template_id=queue_data.template_id,
            camera_id=queue_data.camera_id,
            preset_id=queue_data.preset_id,
            status="queued"
        )
        db.add(post)
        db.flush()

        # Create queue entry
        queue_entry = ReelCaptureQueue(
            post_id=post.id,
            camera_id=queue_data.camera_id,
            preset_id=queue_data.preset_id,
            trigger_mode=trigger_mode,
            scheduled_at=queue_data.scheduled_at,
            status="waiting"
        )
        db.add(queue_entry)

        db.commit()
        db.refresh(post)

        return post
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to queue capture: {str(e)}")


@router.get("/posts/{post_id}/download")
def download_post(
    post_id: int,
    target_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Download the generated video file for manual posting
    
    Optionally specify a target_id to get platform-specific metadata (hashtags, etc.)
    """
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.status != "ready":
        raise HTTPException(status_code=400, detail=f"Post is not ready for download (status: {post.status})")
    
    if not post.output_path:
        raise HTTPException(status_code=404, detail="Video file not found")
    
    video_path = Path(post.output_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")
    
    # Increment download count
    post.download_count = (post.download_count or 0) + 1
    
    # Create export record
    export = ReelExport(
        post_id=post_id,
        target_id=target_id,
        status="exported"
    )
    
    # If target specified, get default metadata
    if target_id:
        target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
        if target:
            # Format title from template
            title = target.default_title_template or "{headline_1}"
            if post.generated_headlines and len(post.generated_headlines) > 0:
                title = title.replace("{headline_1}", post.generated_headlines[0].get('text', ''))
            export.title = title
            export.description = target.default_description_template
            export.hashtags = target.default_hashtags
    
    db.add(export)
    db.commit()
    
    # Return the video file
    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"reelforge_{post_id}.mp4"
    )


@router.get("/posts/{post_id}/metadata")
def get_post_metadata(
    post_id: int,
    target_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get metadata (title, description, hashtags) for a post
    
    Useful for copying text when manually posting to social platforms.
    Optionally specify target_id to get platform-specific defaults.
    """
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Start with headlines
    headlines = post.generated_headlines or []
    headline_1 = headlines[0].get('text', '') if headlines else ''
    
    # Get all headlines as description
    description = "\n".join([h.get('text', '') for h in headlines])
    
    # Default hashtags
    hashtags = "#shorts"
    title = headline_1
    
    # Override with target-specific defaults if provided
    if target_id:
        target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
        if target:
            if target.default_title_template:
                title = target.default_title_template.replace("{headline_1}", headline_1)
            if target.default_description_template:
                description = target.default_description_template + "\n\n" + description
            if target.default_hashtags:
                hashtags = target.default_hashtags
    
    return {
        "title": title,
        "description": description,
        "hashtags": hashtags,
        "headlines": headlines
    }


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    """Delete a post"""
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Also delete any queue entries
    db.query(ReelCaptureQueue).filter(ReelCaptureQueue.post_id == post_id).delete()
    
    try:
        db.delete(post)
        db.commit()
        return {"message": "Post deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete post: {str(e)}")


# ============================================================================
# Publish Target Endpoints
# ============================================================================

@router.get("/targets", response_model=List[ReelPublishTargetSchema])
def get_targets(
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """Get all publish targets"""
    query = db.query(ReelPublishTarget)
    if active_only:
        query = query.filter(ReelPublishTarget.is_active == True)
    return query.order_by(ReelPublishTarget.name).all()


@router.get("/targets/{target_id}", response_model=ReelPublishTargetSchema)
def get_target(target_id: int, db: Session = Depends(get_db)):
    """Get a specific publish target"""
    target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.post("/targets", response_model=ReelPublishTargetSchema)
def create_target(target_data: ReelPublishTargetCreate, db: Session = Depends(get_db)):
    """Create a new platform preference target
    
    Targets store default metadata (hashtags, description templates) for each platform.
    No OAuth/API credentials needed - posts are downloaded and manually uploaded.
    """
    try:
        target = ReelPublishTarget(
            name=target_data.name,
            platform=target_data.platform.value if hasattr(target_data.platform, 'value') else target_data.platform,
            default_title_template=target_data.default_title_template,
            default_description_template=target_data.default_description_template,
            default_hashtags=target_data.default_hashtags
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        return target
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create target: {str(e)}")


@router.put("/targets/{target_id}", response_model=ReelPublishTargetSchema)
def update_target(
    target_id: int,
    target_data: ReelPublishTargetUpdate,
    db: Session = Depends(get_db)
):
    """Update a publish target"""
    target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    try:
        update_dict = target_data.model_dump(exclude_unset=True)
        
        # Handle enum values
        if 'platform' in update_dict and update_dict['platform']:
            update_dict['platform'] = update_dict['platform'].value if hasattr(update_dict['platform'], 'value') else update_dict['platform']
        
        for key, value in update_dict.items():
            setattr(target, key, value)
        
        target.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(target)
        return target
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update target: {str(e)}")


@router.delete("/targets/{target_id}")
def delete_target(target_id: int, db: Session = Depends(get_db)):
    """Delete a publish target"""
    target = db.query(ReelPublishTarget).filter(ReelPublishTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    try:
        db.delete(target)
        db.commit()
        return {"message": "Target deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete target: {str(e)}")


# ============================================================================
# Camera Selection Endpoints (for UI)
# ============================================================================

@router.get("/cameras", response_model=List[CameraWithPresets])
def get_cameras_with_presets(db: Session = Depends(get_db)):
    """Get all cameras with their presets for ReelForge selection UI"""
    cameras = db.query(Camera).options(
        joinedload(Camera.presets)
    ).filter(Camera.is_active == True).order_by(Camera.name).all()
    
    result = []
    for camera in cameras:
        camera_dict = {
            "id": camera.id,
            "name": camera.name,
            "type": camera.type,
            "presets": [
                {
                    "id": p.id,
                    "name": p.name,
                    "pan": p.pan,
                    "tilt": p.tilt,
                    "zoom": p.zoom,
                    "camera_id": p.camera_id,
                    "camera_preset_token": p.camera_preset_token,
                    "created_at": p.created_at
                }
                for p in sorted(camera.presets, key=lambda x: x.name)
            ]
        }
        result.append(camera_dict)
    
    return result


# ============================================================================
# Capture Queue Endpoints
# ============================================================================

@router.get("/queue", response_model=List[ReelCaptureQueueItem])
def get_capture_queue(db: Session = Depends(get_db)):
    """Get current capture queue"""
    queue_items = db.query(ReelCaptureQueue).options(
        joinedload(ReelCaptureQueue.camera),
        joinedload(ReelCaptureQueue.preset)
    ).filter(
        ReelCaptureQueue.status == "waiting"
    ).order_by(
        ReelCaptureQueue.priority.desc(),
        ReelCaptureQueue.created_at
    ).all()

    result = []
    for item in queue_items:
        result.append({
            "id": item.id,
            "post_id": item.post_id,
            "camera_id": item.camera_id,
            "preset_id": item.preset_id,
            "trigger_mode": item.trigger_mode or "next_view",
            "scheduled_at": item.scheduled_at,
            "status": item.status,
            "priority": item.priority,
            "created_at": item.created_at,
            "expires_at": item.expires_at,
            "camera_name": item.camera.name if item.camera else None,
            "preset_name": item.preset.name if item.preset else None
        })

    return result


@router.delete("/queue/{queue_id}")
def cancel_queued_capture(queue_id: int, db: Session = Depends(get_db)):
    """Cancel a queued capture request"""
    queue_item = db.query(ReelCaptureQueue).filter(ReelCaptureQueue.id == queue_id).first()
    if not queue_item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    if queue_item.status != "waiting":
        raise HTTPException(status_code=400, detail=f"Cannot cancel - capture already {queue_item.status}")
    
    try:
        # Update associated post status
        post = db.query(ReelPost).filter(ReelPost.id == queue_item.post_id).first()
        if post:
            post.status = "failed"
            post.error_message = "Cancelled by user"
        
        db.delete(queue_item)
        db.commit()
        return {"message": "Capture cancelled"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel capture: {str(e)}")


# ============================================================================
# Export Tracking Endpoints
# ============================================================================

@router.get("/posts/{post_id}/exports", response_model=List[ReelExportSchema])
def get_post_exports(post_id: int, db: Session = Depends(get_db)):
    """Get all export records for a post (download history)"""
    post = db.query(ReelPost).filter(ReelPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return post.exports


@router.put("/exports/{export_id}", response_model=ReelExportSchema)
def update_export(
    export_id: int,
    export_data: ReelExportUpdate,
    db: Session = Depends(get_db)
):
    """Update an export record (e.g., mark as posted, add platform URL)
    
    Use this after manually posting to a platform to track where it was shared.
    """
    export = db.query(ReelExport).filter(ReelExport.id == export_id).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    
    try:
        if export_data.status:
            export.status = export_data.status.value if hasattr(export_data.status, 'value') else export_data.status
            if export_data.status == "posted":
                export.posted_at = datetime.utcnow()
        
        if export_data.platform_url:
            export.platform_url = export_data.platform_url
        
        db.commit()
        db.refresh(export)
        return export
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update export: {str(e)}")
