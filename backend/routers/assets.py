"""
Assets API Router - Manage overlay assets (images, graphics, dynamic API content)
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import os
import uuid
import shutil
from pathlib import Path

from models.database import get_db, Asset
from models.schemas import AssetCreate, AssetUpdate, Asset as AssetSchema

router = APIRouter(
    prefix="/api/assets",
    tags=["assets"]
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/assets")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("", response_model=List[AssetSchema])
def get_assets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all active assets"""
    assets = db.query(Asset).filter(Asset.is_active == True).offset(skip).limit(limit).all()
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
        created_at=datetime.utcnow()
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
    
    # Update fields
    update_data = asset_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    
    asset.last_updated = datetime.utcnow()
    
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
    asset.last_updated = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Asset deleted successfully", "id": asset_id}

@router.post("/upload")
async def upload_asset_file(
    file: UploadFile = File(...),
    asset_type: str = Form(...)
):
    """Upload an asset file (image or video)"""
    
    # Validate file type
    allowed_image_types = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}
    allowed_video_types = {"video/mp4", "video/mpeg", "video/quicktime", "video/webm"}
    
    if asset_type == "static_image":
        if file.content_type not in allowed_image_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image type: {file.content_type}. Allowed: PNG, JPEG, GIF, WebP"
            )
    elif asset_type == "video":
        if file.content_type not in allowed_video_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid video type: {file.content_type}. Allowed: MP4, MOV, WebM"
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
        
        # Return relative path that can be served
        relative_path = f"/uploads/assets/{unique_filename}"
        
        return {
            "file_path": relative_path,
            "filename": unique_filename,
            "original_filename": file.filename,
            "size": file_size,
            "content_type": file.content_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Clean up file on error
        if file_path.exists():
            os.unlink(file_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/{asset_id}/test")
def test_asset(asset_id: int, db: Session = Depends(get_db)):
    """Test an asset (e.g., check if API URL is accessible)"""
    import requests
    
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.is_active == True).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    if asset.type == "api_image":
        if not asset.api_url:
            raise HTTPException(status_code=400, detail="No API URL configured")
        
        try:
            response = requests.get(asset.api_url, timeout=10)
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

