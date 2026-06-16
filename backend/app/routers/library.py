"""Shared design library — publish/browse/remix endpoints.

Any authenticated user can publish their own design (with an industry tag)
to the library, and any authenticated user can browse all published designs.
Remix data is exposed so the AI Designer can prefill its form from a library
design (using the design's image as a reference, plus its spec).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Design
from ..schemas.design import (
    PublishToLibraryRequest,
    LibraryDesignListItem,
    IndustryCount,
)
from ..services.design_service import (
    publish_design_to_library,
    unpublish_design_from_library,
    list_library_designs,
    get_library_industry_counts,
    get_library_design_remix_data,
)
from ..utils.dependencies import require_auth


router = APIRouter(prefix="/library", tags=["Design Library"])


@router.post("/designs/{design_id}/publish")
async def publish_design(
    design_id: str,
    body: PublishToLibraryRequest,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Publish a design (yours or anyone's) to the shared library."""
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    try:
        publish_design_to_library(
            db=db,
            design_id=design_id,
            industry=body.industry,
            user_id=str(user.id),
        )
        return {"success": True, "industry": body.industry.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/designs/{design_id}/unpublish")
async def unpublish_design(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Remove a design from the library."""
    design = db.query(Design).filter(Design.id == design_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="Design not found")
    try:
        unpublish_design_from_library(db=db, design_id=design_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/designs", response_model=List[LibraryDesignListItem])
async def list_published_designs(
    industry: Optional[str] = Query(None, description="Filter by industry slug; omit for all"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Browse the library. Optionally filter by industry."""
    return list_library_designs(db=db, industry=industry, skip=skip, limit=limit)


@router.get("/industries", response_model=List[IndustryCount])
async def list_industries(
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Industry filter chips — only shows industries with at least one published design."""
    return get_library_industry_counts(db=db)


@router.get("/designs/{design_id}/remix-data")
async def get_remix_data(
    design_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Spec + reference image path for prefilling the AI Designer form."""
    data = get_library_design_remix_data(db=db, design_id=design_id)
    if not data:
        raise HTTPException(status_code=404, detail="Library design not found")
    return data
