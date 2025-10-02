"""
Assets API Router - Manage overlay assets (images, graphics, dynamic API content)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from models.database import get_db, Asset
from models.schemas import AssetCreate, AssetUpdate, Asset as AssetSchema

router = APIRouter(
    prefix="/api/assets",
    tags=["assets"]
)

@router.get("/", response_model=List[AssetSchema])
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

@router.post("/", response_model=AssetSchema)
def create_asset(asset_data: AssetCreate, db: Session = Depends(get_db)):
    """Create a new asset"""
    
    # Validate that either file_path or api_url is provided
    if asset_data.type == "api_image":
        if not asset_data.api_url:
            raise HTTPException(status_code=400, detail="api_url is required for api_image type")
    elif asset_data.type in ["static_image", "video", "graphic"]:
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

