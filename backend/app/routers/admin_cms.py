"""Admin CMS management routes - pages, sections, and media."""

import uuid
import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.cms import CmsPage, CmsSection, CmsMedia
from ..utils.store_dependencies import require_store_role

router = APIRouter(prefix="/admin/cms", tags=["Admin CMS"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PageCreate(BaseModel):
    title: str
    slug: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    template: str = "default"


class PageUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image: Optional[str] = None
    template: Optional[str] = None
    status: Optional[str] = None


class SectionCreate(BaseModel):
    module_type: str
    config: Optional[str] = None  # JSON string
    sort_order: int = 0
    is_active: bool = True


class SectionUpdate(BaseModel):
    module_type: Optional[str] = None
    config: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class SectionReorder(BaseModel):
    section_ids: list[str]


class PageResponse(BaseModel):
    id: str
    title: str
    slug: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image: Optional[str] = None
    status: str
    template: str
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SectionResponse(BaseModel):
    id: str
    page_id: str
    module_type: str
    config: Optional[str] = None
    sort_order: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PageDetailResponse(PageResponse):
    sections: list[SectionResponse] = []


class MediaResponse(BaseModel):
    id: str
    filename: str
    url: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    alt: Optional[str] = None
    folder: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Page endpoints
# ---------------------------------------------------------------------------

@router.get("/pages", response_model=list[PageResponse])
async def list_pages(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """List all CMS pages."""
    query = db.query(CmsPage)

    if status_filter:
        query = query.filter(CmsPage.status == status_filter)
    if search:
        query = query.filter(
            CmsPage.title.ilike(f"%{search}%")
            | CmsPage.slug.ilike(f"%{search}%")
        )

    return query.order_by(CmsPage.updated_at.desc()).all()


@router.post("/pages", response_model=PageResponse, status_code=201)
async def create_page(
    data: PageCreate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Create a new CMS page."""
    existing = db.query(CmsPage).filter(CmsPage.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    page = CmsPage(
        **data.model_dump(),
        created_by=admin.id,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.get("/pages/{page_id}", response_model=PageDetailResponse)
async def get_page(
    page_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Get page with all sections."""
    page = (
        db.query(CmsPage)
        .options(joinedload(CmsPage.sections))
        .filter(CmsPage.id == page_id)
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.put("/pages/{page_id}", response_model=PageResponse)
async def update_page(
    page_id: str,
    data: PageUpdate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Update page metadata."""
    page = db.query(CmsPage).filter(CmsPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(page, key, value)
    db.commit()
    db.refresh(page)
    return page


@router.delete("/pages/{page_id}")
async def delete_page(
    page_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Delete a CMS page and all its sections."""
    page = db.query(CmsPage).filter(CmsPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    db.delete(page)
    db.commit()
    return {"message": "Page deleted"}


@router.post("/pages/{page_id}/preview-token")
async def generate_preview_token(
    page_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Generate a time-limited preview token for a CMS page."""
    page = db.query(CmsPage).filter(CmsPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    from .cms_public import generate_preview_token as _gen_token

    result = _gen_token(page_id, ttl_seconds=900)
    preview_url = f"/pages/preview/{page_id}?token={result['token']}"
    return {
        "token": result["token"],
        "preview_url": preview_url,
        "expires_in": result["expires_in"],
    }


@router.post("/pages/{page_id}/publish", response_model=PageResponse)
async def publish_page(
    page_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Publish a CMS page."""
    page = db.query(CmsPage).filter(CmsPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    page.status = "published"
    page.published_at = datetime.utcnow()
    db.commit()
    db.refresh(page)
    return page


# ---------------------------------------------------------------------------
# Section endpoints
# ---------------------------------------------------------------------------

@router.post("/pages/{page_id}/sections", response_model=SectionResponse, status_code=201)
async def create_section(
    page_id: str,
    data: SectionCreate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Add a section to a page."""
    page = db.query(CmsPage).filter(CmsPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Validate config is valid JSON if provided
    if data.config:
        try:
            json.loads(data.config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Config must be valid JSON")

    section = CmsSection(page_id=page_id, **data.model_dump())
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.put("/sections/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: str,
    data: SectionUpdate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Update a section."""
    section = db.query(CmsSection).filter(CmsSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    if data.config is not None:
        try:
            json.loads(data.config)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Config must be valid JSON")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(section, key, value)
    db.commit()
    db.refresh(section)
    return section


@router.delete("/sections/{section_id}")
async def delete_section(
    section_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Delete a section."""
    section = db.query(CmsSection).filter(CmsSection.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    db.delete(section)
    db.commit()
    return {"message": "Section deleted"}


@router.put("/pages/{page_id}/sections/reorder")
async def reorder_sections(
    page_id: str,
    data: SectionReorder,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Reorder sections within a page."""
    for idx, section_id in enumerate(data.section_ids):
        db.query(CmsSection).filter(
            CmsSection.id == section_id,
            CmsSection.page_id == page_id,
        ).update({"sort_order": idx})
    db.commit()
    return {"message": "Sections reordered"}


# ---------------------------------------------------------------------------
# Media endpoints
# ---------------------------------------------------------------------------

@router.get("/media", response_model=list[MediaResponse])
async def list_media(
    folder: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """List uploaded media files."""
    query = db.query(CmsMedia)

    if folder:
        query = query.filter(CmsMedia.folder == folder)
    if search:
        query = query.filter(CmsMedia.filename.ilike(f"%{search}%"))

    return query.order_by(CmsMedia.created_at.desc()).offset(offset).limit(limit).all()


@router.post("/media", response_model=MediaResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    alt: str = Form(default=""),
    folder: str = Form(default="general"),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Upload a media file."""
    from ..services.storage_service import save_file_bytes, generate_unique_filename

    ext = os.path.splitext(file.filename or "file")[1]
    filename = generate_unique_filename(f"upload{ext}")
    content = await file.read()
    relative_path = await save_file_bytes(content, f"cms/{folder}", filename, file.content_type or "application/octet-stream")

    media = CmsMedia(
        filename=file.filename or filename,
        url=relative_path,
        mime_type=file.content_type,
        size=len(content),
        alt=alt,
        folder=folder,
        uploaded_by=admin.id,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    return media


@router.delete("/media/{media_id}")
async def delete_media(
    media_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Delete a media file."""
    media = db.query(CmsMedia).filter(CmsMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    # Delete file from storage
    from ..services.storage_service import delete_file
    delete_file(media.url)

    db.delete(media)
    db.commit()
    return {"message": "Media deleted"}
