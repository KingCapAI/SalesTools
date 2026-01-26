"""Brand management routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Brand, Customer
from ..schemas.brand import BrandCreate, BrandResponse, BrandUpdate, BrandList
from ..utils.dependencies import require_auth, get_current_user

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get("", response_model=List[BrandList])
async def list_brands(
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """List brands with optional filters."""
    query = db.query(Brand)

    if customer_id:
        query = query.filter(Brand.customer_id == customer_id)
    if search:
        query = query.filter(Brand.name.ilike(f"%{search}%"))

    brands = query.order_by(Brand.name).offset(skip).limit(limit).all()
    return brands


@router.post("", response_model=BrandResponse)
async def create_brand(
    brand_data: BrandCreate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Create a new brand."""
    # Verify customer exists
    customer = db.query(Customer).filter(Customer.id == brand_data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    brand = Brand(
        customer_id=brand_data.customer_id,
        name=brand_data.name,
        website=brand_data.website,
        created_by_id=user.id,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


@router.get("/{brand_id}", response_model=BrandResponse)
async def get_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get a brand by ID."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return brand


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: str,
    brand_data: BrandUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Update a brand."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    if brand_data.name is not None:
        brand.name = brand_data.name
    if brand_data.website is not None:
        brand.website = brand_data.website

    db.commit()
    db.refresh(brand)
    return brand


@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Delete a brand."""
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    db.delete(brand)
    db.commit()
    return {"message": "Brand deleted successfully"}
