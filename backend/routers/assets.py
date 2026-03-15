"""
Assets API Router - Manage overlay assets (images, graphics, dynamic API content)
"""

import ipaddress
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
import os
import uuid
import shutil
import httpx
from pathlib import Path
from urllib.parse import urlparse

from models.database import get_db, Asset
from models.schemas import AssetCreate, AssetUpdate, Asset as AssetSchema
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

# SSRF-blocked networks (allow 192.168.0.0/16 and *.local for local services like TempestWeather)
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]
_BLOCKED_HOSTNAMES = {"host.docker.internal"}

# Internal hostnames that template-generated URLs may target (e.g. TempestWeather via Docker)
_SSRF_ALLOWED_INTERNAL_HOSTS = set(
    h.strip().lower()
    for h in os.getenv("SSRF_ALLOWED_INTERNAL_HOSTS", "host.docker.internal").split(",")
    if h.strip()
)


def _validate_url(url: str, *, allow_internal: bool = False) -> bool:
    """Validate that a URL is safe to fetch (blocks SSRF targets).

    Allows http/https schemes. Blocks loopback, link-local, 10.x, and
    host.docker.internal. Permits 192.168.x.x and *.local for local
    network services (e.g. TempestWeather).

    If allow_internal=True, hostnames in SSRF_ALLOWED_INTERNAL_HOSTS are
    permitted. This is used for template-generated URLs (e.g. TempestWeather
    running at host.docker.internal) where the URL is constructed by the
    backend, not supplied by the user.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        if not (allow_internal and hostname.lower() in _SSRF_ALLOWED_INTERNAL_HOSTS):
            return False

    try:
        addr = ipaddress.ip_address(hostname)
        for net in _BLOCKED_NETWORKS:
            if addr in net:
                return False
    except ValueError:
        # Not an IP literal — it's a hostname; blocked hostnames already checked above
        pass

    return True


router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
    dependencies=[Depends(get_current_user)]
)

# Public router for endpoints that don't require authentication (e.g. img src tags)
public_router = APIRouter(
    prefix="/api/assets",
    tags=["assets"],
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/assets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("", response_model=List[AssetSchema])
def get_assets(
    skip: int = 0,
    limit: int = 100,
    type: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db)
):
    """Get all active assets, optionally filtered by type and/or search term."""
    query = db.query(Asset).filter(Asset.is_active == True)
    if type:
        # 'template' is a virtual filter: match assets with a template_instance_id
        if type == "template":
            query = query.filter(Asset.template_instance_id.isnot(None))
        else:
            query = query.filter(Asset.type == type)
    if search:
        query = query.filter(Asset.name.ilike(f"%{search}%"))
    assets = query.offset(skip).limit(limit).all()
    return assets

@router.get("/{asset_id}", response_model=AssetSchema)
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """Get a specific asset by ID"""
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_active == True).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset

@router.post("", response_model=AssetSchema)
def create_asset(asset_data: AssetCreate, db: Session = Depends(get_db)):
    """Create a new asset"""

    # Validate that either file_path or api_url is provided
    if asset_data.type == "api_image":
        if not asset_data.api_url:
            raise HTTPException(status_code=400, detail="api_url is required for api_image type")
    elif asset_data.type in ["static_image", "video", "graphic", "google_drawing"]:
        if not asset_data.file_path:
            raise HTTPException(status_code=400, detail="file_path is required for this asset type")

    if asset_data.api_url and not _validate_url(asset_data.api_url):
        raise HTTPException(status_code=400, detail="Asset API URL is not allowed (blocked scheme or address)")

    asset = Asset(
        name=asset_data.name,
        type=asset_data.type,
        file_path=asset_data.file_path,
        api_url=asset_data.api_url,
        api_refresh_interval=asset_data.api_refresh_interval,
        width=asset_data.width,
        height=asset_data.height,
        position_x=asset_data.position_x,
        position_y=asset_data.position_y,
        opacity=asset_data.opacity,
        description=asset_data.description,
        created_at=datetime.now(timezone.utc)
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset

@router.put("/{asset_id}", response_model=AssetSchema)
def update_asset(asset_id: int, asset_data: AssetUpdate, db: Session = Depends(get_db)):
    """Update an existing asset"""
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_active == True).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset_data.api_url and not _validate_url(asset_data.api_url):
        raise HTTPException(status_code=400, detail="Asset API URL is not allowed (blocked scheme or address)")

    # Update fields
    update_data = asset_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)

    asset.last_updated = datetime.now(timezone.utc)

    db.commit()
    db.refresh(asset)

    return asset

@router.delete("/{asset_id}")
def delete_asset(asset_id: int, db: Session = Depends(get_db)):
    """Soft delete an asset"""
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_active == True).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    asset.is_active = False
    asset.last_updated = datetime.now(timezone.utc)

    db.commit()

    return {"message": "Asset deleted successfully", "id": asset_id}

@router.post("/upload")
async def upload_asset_file(
    file: UploadFile = File(...),
    asset_type: str = Form(...)
):
    """Upload an asset file (image or video)"""

    # Validate file type — fall back to extension if content_type is generic
    _EXT_TO_MIME = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".avif": "image/avif",
        ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    }
    content_type = file.content_type
    if content_type in (None, "application/octet-stream") and file.filename:
        ext = Path(file.filename).suffix.lower()
        content_type = _EXT_TO_MIME.get(ext, content_type)

    allowed_image_types = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/avif"}
    allowed_video_types = {"video/mp4", "video/mpeg", "video/quicktime", "video/webm"}

    if asset_type == "static_image":
        if content_type not in allowed_image_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type: {content_type}. Allowed: PNG, JPEG, GIF, WebP, AVIF"
            )
    elif asset_type == "video":
        if content_type not in allowed_video_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid video type: {content_type}. Allowed: MP4, MOV, WebM"
            )
    else:
        raise HTTPException(status_code=400, detail=f"Invalid asset type: {asset_type}")

    # Validate file size (50MB max)
    MAX_SIZE = 50 * 1024 * 1024  # 50MB
    file_size = 0

    # Generate unique filename
    file_extension = Path(file.filename or "file").suffix
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename

    try:
        # Save file with size check
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(8192)  # 8KB chunks
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_SIZE:
                    # Clean up partial file
                    buffer.close()
                    os.unlink(file_path)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size is 50MB"
                    )
                buffer.write(chunk)

        # Auto-convert non-PNG images (AVIF, WebP, GIF) to PNG for FFmpeg compatibility
        final_filename = unique_filename
        if asset_type == "static_image" and content_type not in ("image/png", "image/jpeg", "image/jpg"):
            try:
                from PIL import Image as PILImage
                with PILImage.open(file_path) as img:
                    png_filename = f"{uuid.uuid4()}.png"
                    png_path = UPLOAD_DIR / png_filename
                    img.convert("RGBA").save(png_path, "PNG")
                # Remove original, use PNG
                os.unlink(file_path)
                file_path = png_path
                final_filename = png_filename
                file_size = png_path.stat().st_size
                logger.info("Converted %s to PNG: %s", file.content_type, png_filename)
            except Exception as conv_err:
                logger.warning("Image conversion failed, keeping original: %s", conv_err)

        # Return relative path that can be served
        relative_path = f"/uploads/assets/{final_filename}"

        return {
            "file_path": relative_path,
            "filename": final_filename,
            "original_filename": file.filename,
            "size": file_size,
            "content_type": content_type
        }

    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            os.unlink(file_path)
        logger.error("Upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Upload failed")

@router.post("/{asset_id}/test")
async def test_asset(asset_id: int, db: Session = Depends(get_db)):
    """Test an asset (e.g., check if API URL is accessible)"""
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_active == True).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.type == "api_image":
        if not asset.api_url:
            raise HTTPException(status_code=400, detail="No API URL configured")
        # Template-generated assets may target internal hosts (e.g. host.docker.internal)
        allow_internal = asset.template_instance_id is not None
        if not _validate_url(asset.api_url, allow_internal=allow_internal):
            raise HTTPException(status_code=400, detail="Asset API URL is not allowed (blocked scheme or address)")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(asset.api_url)
                response.raise_for_status()

                content_type = response.headers.get('content-type', '')

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "content_length": len(response.content),
                    "message": "Asset API is accessible"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to access asset API"
            }

    return {"message": "Test not implemented for this asset type"}


@public_router.get("/{asset_id}/proxy")
async def proxy_asset_image(asset_id: int, db: Session = Depends(get_db)):
    """Proxy an API image asset through the backend.

    This avoids mixed-content and DNS issues when the browser can't
    reach the asset's api_url directly (e.g. Cloudflare Tunnel over HTTPS,
    or host.docker.internal / vistter.local not resolvable from client).
    """
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_active == True).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.type != "api_image" or not asset.api_url:
        raise HTTPException(status_code=400, detail="Asset is not an API image")
    if not _validate_url(asset.api_url):
        raise HTTPException(status_code=400, detail="Asset API URL is not allowed (blocked scheme or address)")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(asset.api_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/png")
            return Response(
                content=response.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=30"},
            )
    except Exception as e:
        logger.error("Failed to fetch asset: %s", e)
        raise HTTPException(status_code=502, detail="Failed to fetch asset")
