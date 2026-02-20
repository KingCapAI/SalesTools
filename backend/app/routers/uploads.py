"""File upload routes."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from ..database import get_db
from ..config import get_settings
from ..models import BrandAsset, Brand
from ..services.storage_service import save_upload_file, get_file_url
from ..utils.dependencies import require_auth

router = APIRouter(prefix="/upload", tags=["Uploads"])
settings = get_settings()

# Allowed MIME types (SVG not supported - Gemini API only accepts PNG/JPG/WEBP)
LOGO_TYPES = ["image/png", "image/jpeg", "image/webp"]
BRAND_ASSET_TYPES = [
    "image/png",
    "image/jpeg",
    "image/webp",
    "application/pdf",
]


@router.post("/logo")
async def upload_logo(
    brand_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Upload a brand logo."""
    # Verify brand exists
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    try:
        file_path, mime_type, file_size = await save_upload_file(
            file=file,
            subdir="logos",
            allowed_types=LOGO_TYPES,
            max_size_mb=10,
        )

        # Check if brand already has a logo
        existing_logo = (
            db.query(BrandAsset)
            .filter(
                BrandAsset.brand_id == brand_id,
                BrandAsset.type == "logo",
            )
            .first()
        )

        if existing_logo:
            # Update existing logo
            existing_logo.file_name = file.filename
            existing_logo.file_path = file_path
            existing_logo.mime_type = mime_type
            existing_logo.file_size = file_size
            brand_asset = existing_logo
        else:
            # Create new logo asset
            brand_asset = BrandAsset(
                brand_id=brand_id,
                type="logo",
                file_name=file.filename,
                file_path=file_path,
                mime_type=mime_type,
                file_size=file_size,
            )
            db.add(brand_asset)

        db.commit()
        db.refresh(brand_asset)

        return {
            "id": brand_asset.id,
            "file_path": file_path,
            "file_url": get_file_url(file_path),
            "mime_type": mime_type,
            "file_size": file_size,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/brand-asset")
async def upload_brand_asset(
    brand_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Upload a brand asset (PDF or image)."""
    # Verify brand exists
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    try:
        file_path, mime_type, file_size = await save_upload_file(
            file=file,
            subdir="brand_assets",
            allowed_types=BRAND_ASSET_TYPES,
            max_size_mb=25,
        )

        # Determine asset type
        if mime_type == "application/pdf":
            asset_type = "pdf"
        else:
            asset_type = "image"

        # Create brand asset
        brand_asset = BrandAsset(
            brand_id=brand_id,
            type=asset_type,
            file_name=file.filename,
            file_path=file_path,
            mime_type=mime_type,
            file_size=file_size,
        )
        db.add(brand_asset)
        db.commit()
        db.refresh(brand_asset)

        return {
            "id": brand_asset.id,
            "file_path": file_path,
            "file_url": get_file_url(file_path),
            "mime_type": mime_type,
            "file_size": file_size,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/brand-asset/{asset_id}")
async def delete_brand_asset(
    asset_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Delete a brand asset."""
    asset = db.query(BrandAsset).filter(BrandAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Delete file from storage
    if asset.file_path:
        from ..services.storage_service import delete_file
        delete_file(asset.file_path)

    db.delete(asset)
    db.commit()
    return {"message": "Asset deleted successfully"}


@router.post("/design-logo")
async def upload_design_logo(
    file: UploadFile = File(...),
    user=Depends(require_auth),
):
    """Upload a logo for design generation (not linked to a brand entity)."""
    try:
        file_path, mime_type, file_size = await save_upload_file(
            file=file,
            subdir="design_logos",
            allowed_types=LOGO_TYPES,
            max_size_mb=10,
        )

        return {
            "file_path": file_path,
            "file_url": get_file_url(file_path),
            "mime_type": mime_type,
            "file_size": file_size,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/design-asset")
async def upload_design_asset(
    file: UploadFile = File(...),
    user=Depends(require_auth),
):
    """Upload a brand asset for design generation (not linked to a brand entity)."""
    try:
        file_path, mime_type, file_size = await save_upload_file(
            file=file,
            subdir="design_assets",
            allowed_types=BRAND_ASSET_TYPES,
            max_size_mb=25,
        )

        # Determine asset type
        if mime_type == "application/pdf":
            asset_type = "pdf"
        else:
            asset_type = "image"

        return {
            "file_path": file_path,
            "file_url": get_file_url(file_path),
            "mime_type": mime_type,
            "file_size": file_size,
            "asset_type": asset_type,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Serve uploaded files
uploads_router = APIRouter(prefix="/uploads", tags=["File Serving"])


@uploads_router.get("/{file_path:path}")
async def serve_file(file_path: str):
    """Serve uploaded files."""
    full_path = Path(settings.upload_dir) / file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(full_path)
