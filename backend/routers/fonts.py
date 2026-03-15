"""
Fonts API Router - Manage fonts for the Asset Management Studio
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from models.database import get_db
from models.schemas import FontRead
from routers.auth import get_current_user
from services import font_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/fonts",
    tags=["fonts"],
    dependencies=[Depends(get_current_user)],
)

# Max upload size: 10 MB for font files
MAX_FONT_SIZE = 10 * 1024 * 1024


class GoogleFontInstall(BaseModel):
    """Request body for installing a Google Font."""
    family: str = Field(..., min_length=1, max_length=100)
    weight: str = Field(default="400")


@router.get("", response_model=List[FontRead])
def list_fonts(
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all active fonts, optionally filtered by source (system, uploaded, google)."""
    if source and source not in ("system", "uploaded", "google"):
        raise HTTPException(status_code=400, detail="Invalid source filter. Use: system, uploaded, or google")
    return font_service.get_fonts(db, source=source)


@router.post("/upload", response_model=FontRead)
async def upload_font(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a custom TTF or OTF font file."""
    # Validate content type (best-effort; magic bytes are the real check)
    allowed_types = {
        "font/ttf",
        "font/otf",
        "font/sfnt",
        "application/x-font-ttf",
        "application/x-font-opentype",
        "application/octet-stream",
    }
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Upload a .ttf or .otf file.",
        )

    # Read file with size limit
    file_data = b""
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        file_data += chunk
        if len(file_data) > MAX_FONT_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Font file too large. Maximum size is 10 MB.",
            )

    if not file_data:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        font = font_service.upload_font(db, file_data, file.filename or "font.ttf")
        return font
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/google")
def search_google_fonts(q: Optional[str] = None):
    """Search available Google Fonts (Phase 1: hardcoded popular fonts)."""
    results = font_service.search_google_fonts(query=q)
    return {"fonts": results, "count": len(results)}


@router.post("/google/install", response_model=FontRead)
async def install_google_font(
    data: GoogleFontInstall,
    db: Session = Depends(get_db),
):
    """Download and install a Google Font by family and weight."""
    try:
        font = await font_service.install_google_font(db, family=data.family, weight=data.weight)
        return font
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{font_id}")
def delete_font(font_id: int, db: Session = Depends(get_db)):
    """Delete an uploaded font. System and Google fonts cannot be deleted."""
    try:
        deleted = font_service.delete_font(db, font_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail="Font not found")

    return {"message": "Font deleted successfully", "id": font_id}
