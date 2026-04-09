"""Public CMS routes — published pages and token-protected previews."""

import hashlib
import hmac
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..config import get_settings
from ..models.cms import CmsPage, CmsSection

router = APIRouter(prefix="/cms", tags=["CMS Public"])

settings = get_settings()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PublicSectionResponse(BaseModel):
    id: str
    module_type: str
    config: Optional[str] = None
    sort_order: int

    class Config:
        from_attributes = True


class CmsPublicPageResponse(BaseModel):
    id: str
    title: str
    slug: str
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    og_image: Optional[str] = None
    template: str
    sections: list[PublicSectionResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Preview token helpers
# ---------------------------------------------------------------------------

def _make_preview_signature(page_id: str, expiry: int) -> str:
    """HMAC-SHA256 over page_id:expiry using jwt_secret."""
    msg = f"{page_id}:{expiry}".encode()
    return hmac.new(settings.jwt_secret.encode(), msg, hashlib.sha256).hexdigest()


def generate_preview_token(page_id: str, ttl_seconds: int = 900) -> dict:
    """Generate a preview token valid for `ttl_seconds` (default 15 min)."""
    expiry = int(time.time()) + ttl_seconds
    sig = _make_preview_signature(page_id, expiry)
    token = f"{expiry}.{sig}"
    return {"token": token, "expires_in": ttl_seconds}


def verify_preview_token(page_id: str, token: str) -> bool:
    """Verify an HMAC preview token."""
    try:
        expiry_str, sig = token.split(".", 1)
        expiry = int(expiry_str)
    except (ValueError, AttributeError):
        return False

    if time.time() > expiry:
        return False

    expected = _make_preview_signature(page_id, expiry)
    return hmac.compare_digest(sig, expected)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@router.get("/pages/{slug}", response_model=CmsPublicPageResponse)
async def get_published_page(slug: str, db: Session = Depends(get_db)):
    """Get a published CMS page by slug (no auth required)."""
    page = (
        db.query(CmsPage)
        .options(joinedload(CmsPage.sections))
        .filter(CmsPage.slug == slug, CmsPage.status == "published")
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Filter to active sections only
    page.sections = [s for s in page.sections if s.is_active]
    return page


@router.get("/preview/{page_id}", response_model=CmsPublicPageResponse)
async def preview_page(
    page_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """Preview any CMS page with a valid HMAC token (no auth required)."""
    if not verify_preview_token(page_id, token):
        raise HTTPException(status_code=403, detail="Invalid or expired preview token")

    page = (
        db.query(CmsPage)
        .options(joinedload(CmsPage.sections))
        .filter(CmsPage.id == page_id)
        .first()
    )
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    # Show active sections only (same filtering as published)
    page.sections = [s for s in page.sections if s.is_active]
    return page
