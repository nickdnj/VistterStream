"""
Font Service - Business logic for font management (system, uploaded, Google Fonts)
"""

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from models.font import Font

logger = logging.getLogger(__name__)

# Resolve uploads directory from environment (same pattern as main.py)
UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")

# Popular Google Fonts for Phase 1 hardcoded search
_POPULAR_GOOGLE_FONTS = [
    "Roboto",
    "Open Sans",
    "Lato",
    "Montserrat",
    "Oswald",
    "Raleway",
    "Poppins",
    "Nunito",
    "Ubuntu",
    "Merriweather",
    "PT Sans",
    "Playfair Display",
    "Source Sans 3",
    "Noto Sans",
    "Inter",
    "Bebas Neue",
    "Kanit",
    "Rubik",
    "Work Sans",
    "Quicksand",
]


def _ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def _fonts_base_dir() -> str:
    """Return the base fonts directory.

    Resolves relative to UPLOADS_DIR: go up one level from uploads to reach
    the data root, then into fonts/.
    In Docker this yields /data/fonts; locally it yields ./fonts.
    """
    return str(Path(UPLOADS_DIR).parent / "fonts")


def _extract_font_family(font_path: str) -> str | None:
    """Try to extract the font family name using Pillow's ImageFont."""
    try:
        from PIL import ImageFont

        font = ImageFont.truetype(font_path)
        name_info = font.getname()
        if name_info and name_info[0]:
            return name_info[0]
    except Exception as e:
        logger.debug("Could not extract font family from %s: %s", font_path, e)
    return None


# ---------------------------------------------------------------------------
# System font scanning
# ---------------------------------------------------------------------------

def scan_system_fonts(db: Session) -> int:
    """Walk /usr/share/fonts/ and upsert discovered .ttf/.otf fonts.

    Returns the count of fonts found.
    """
    fonts_root = "/usr/share/fonts/"
    if not os.path.isdir(fonts_root):
        logger.info(
            "System fonts directory %s not found (probably dev machine); skipping scan",
            fonts_root,
        )
        return 0

    found = 0
    for dirpath, _dirnames, filenames in os.walk(fonts_root):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in (".ttf", ".otf"):
                continue

            full_path = os.path.join(dirpath, filename)
            family = _extract_font_family(full_path)
            if not family:
                # Fallback: derive from filename
                family = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ")

            # Upsert: check if font with same family + source already exists
            existing = (
                db.query(Font)
                .filter(Font.family == family, Font.source == "system")
                .first()
            )
            if existing:
                # Update path if it changed
                if existing.file_path != full_path:
                    existing.file_path = full_path
                found += 1
                continue

            font = Font(
                family=family,
                weight="400",
                style="normal",
                source="system",
                file_path=full_path,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(font)
            found += 1

    db.commit()
    logger.info("System font scan complete: %d fonts found", found)
    return found


# ---------------------------------------------------------------------------
# Font listing
# ---------------------------------------------------------------------------

def get_fonts(db: Session, source: str | None = None) -> list[Font]:
    """List active fonts, optionally filtered by source."""
    query = db.query(Font).filter(Font.is_active == True)
    if source:
        query = query.filter(Font.source == source)
    return query.order_by(Font.family).all()


# ---------------------------------------------------------------------------
# Font upload
# ---------------------------------------------------------------------------

# Magic bytes for font validation
_TTF_MAGIC = b"\x00\x01\x00\x00"
_OTF_MAGIC = b"OTTO"


def upload_font(db: Session, file_data: bytes, filename: str) -> Font:
    """Upload and register a custom font file.

    Validates magic bytes, saves the file, extracts the family name,
    and creates a Font record with source='uploaded'.
    """
    # Validate magic bytes
    if len(file_data) < 4:
        raise ValueError("File too small to be a valid font")

    header = file_data[:4]
    if header != _TTF_MAGIC and header != _OTF_MAGIC:
        raise ValueError(
            "Invalid font file: expected TTF or OTF format "
            "(magic bytes do not match)"
        )

    # Determine extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".ttf", ".otf"):
        ext = ".otf" if header == _OTF_MAGIC else ".ttf"

    # Save file
    upload_dir = os.path.join(_fonts_base_dir(), "uploads")
    _ensure_dir(upload_dir)

    file_uuid = str(uuid.uuid4())
    saved_filename = f"{file_uuid}{ext}"
    saved_path = os.path.join(upload_dir, saved_filename)

    with open(saved_path, "wb") as f:
        f.write(file_data)

    # Extract family name
    family = _extract_font_family(saved_path)
    if not family:
        family = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ")

    font = Font(
        family=family,
        weight="400",
        style="normal",
        source="uploaded",
        file_path=f"/fonts/uploads/{saved_filename}",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(font)
    db.commit()
    db.refresh(font)
    logger.info("Uploaded font id=%d family=%s file=%s", font.id, family, saved_filename)
    return font


# ---------------------------------------------------------------------------
# Font deletion
# ---------------------------------------------------------------------------

def delete_font(db: Session, font_id: int) -> bool:
    """Delete a font. Only uploaded fonts can be deleted (not system or google)."""
    font = (
        db.query(Font)
        .filter(Font.id == font_id, Font.is_active == True)
        .first()
    )
    if not font:
        return False

    if font.source != "uploaded":
        raise ValueError("Only uploaded fonts can be deleted")

    font.is_active = False
    db.commit()
    logger.info("Deleted font id=%d family=%s", font.id, font.family)
    return True


# ---------------------------------------------------------------------------
# Google Fonts - search
# ---------------------------------------------------------------------------

def search_google_fonts(query: str | None = None) -> list[dict]:
    """Search available Google Fonts.

    Phase 1: returns a hardcoded list of popular fonts, filtered by query.
    Phase 2 (TODO): use Google Fonts Developer API when API key is available.
    """
    results = []
    q_lower = (query or "").lower()

    for family in _POPULAR_GOOGLE_FONTS:
        if not q_lower or q_lower in family.lower():
            results.append({
                "family": family,
                "variants": ["400", "700"],
                "category": "sans-serif",
                "preview_url": f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}&display=swap",
            })

    return results


# ---------------------------------------------------------------------------
# Google Fonts - install
# ---------------------------------------------------------------------------

async def install_google_font(
    db: Session,
    family: str,
    weight: str = "400",
) -> Font:
    """Download and install a Google Font.

    Fetches the font from Google Fonts CSS2 API, caches the .ttf file locally,
    and creates a Font record with source='google'.
    """
    # Check if already installed
    existing = (
        db.query(Font)
        .filter(Font.family == family, Font.weight == weight, Font.source == "google", Font.is_active == True)
        .first()
    )
    if existing:
        return existing

    # Build Google Fonts CSS2 URL
    css_url = (
        f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}"
        f":wght@{weight}&display=swap"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Fetch CSS - need to request with a user-agent that triggers .ttf URLs
            css_response = await client.get(
                css_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
            css_response.raise_for_status()
            css_text = css_response.text

            # Extract .ttf or .woff2 URL from the CSS
            # Google Fonts returns url(...) in @font-face blocks
            url_match = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css_text)
            if not url_match:
                raise ValueError(f"Could not find font URL in Google Fonts CSS for {family}")

            font_url = url_match.group(1)

            # Download the actual font file
            font_response = await client.get(font_url)
            font_response.raise_for_status()
            font_bytes = font_response.content

    except httpx.HTTPError as e:
        raise ValueError(f"Failed to download Google Font '{family}': {e}")

    # Determine file extension from URL
    ext = ".woff2"
    if font_url.endswith(".ttf"):
        ext = ".ttf"
    elif font_url.endswith(".otf"):
        ext = ".otf"

    # Save to cache directory
    cache_dir = os.path.join(_fonts_base_dir(), "google", family.replace(" ", "_"))
    _ensure_dir(cache_dir)

    cached_filename = f"{weight}{ext}"
    cached_path = os.path.join(cache_dir, cached_filename)

    with open(cached_path, "wb") as f:
        f.write(font_bytes)

    # Build the serve path relative to fonts mount
    family_dir = family.replace(" ", "_")
    serve_path = f"/fonts/google/{family_dir}/{cached_filename}"

    font = Font(
        family=family,
        weight=weight,
        style="normal",
        source="google",
        file_path=serve_path,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(font)
    db.commit()
    db.refresh(font)
    logger.info("Installed Google Font id=%d family=%s weight=%s", font.id, family, weight)
    return font
