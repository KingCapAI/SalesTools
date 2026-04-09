"""Store product catalog routes."""

import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..config import get_settings
from ..models.store_product import (
    Product, ProductCategory, ProductImage,
    ProductColorway, DecorationOption,
)
from ..schemas.store_product import (
    ProductListResponse,
    ProductDetailResponse,
    ProductCategoryResponse,
    ProductCreate,
    ProductUpdate,
)
from ..utils.store_dependencies import require_store_role

router = APIRouter(prefix="/store/products", tags=["Store Products"])


@router.get("/categories", response_model=list[ProductCategoryResponse])
async def list_categories(db: Session = Depends(get_db)):
    """List all active product categories."""
    categories = (
        db.query(ProductCategory)
        .filter(ProductCategory.is_active == True)
        .order_by(ProductCategory.sort_order)
        .all()
    )
    return categories


STYLE_FAMILY_PREFIXES = {
    "crest": ["260", "360", "460"],
    "ace": ["250", "450", "150"],
    "origin": ["100"],
    "buddy": ["230"],
}


@router.get("", response_model=list[ProductListResponse])
async def list_products(
    collection: Optional[str] = None,
    category_slug: Optional[str] = None,
    featured: Optional[bool] = None,
    search: Optional[str] = None,
    style_family: Optional[str] = None,
    is_trucker: Optional[bool] = None,
    is_perforated: Optional[bool] = None,
    material: Optional[str] = None,
    sweatband: Optional[str] = None,
    closure_type: Optional[str] = None,
    profile: Optional[str] = None,
    color: Optional[str] = None,
    sort: str = "name",
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List products with filtering and sorting."""
    query = db.query(Product).filter(Product.is_active == True)

    if collection:
        query = query.filter(Product.collection == collection)

    if category_slug:
        category = db.query(ProductCategory).filter(
            ProductCategory.slug == category_slug
        ).first()
        if category:
            query = query.filter(Product.category_id == category.id)

    if featured is not None:
        query = query.filter(Product.is_featured == featured)

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%")
            | Product.style_number.ilike(f"%{search}%")
            | Product.description.ilike(f"%{search}%")
        )

    # Style family filter (maps family name to style_number prefixes)
    if style_family:
        from sqlalchemy import or_
        prefixes = STYLE_FAMILY_PREFIXES.get(style_family.lower(), [])
        if prefixes:
            query = query.filter(
                or_(*[Product.style_number.like(f"{p}%") for p in prefixes])
            )

    # Boolean filters
    if is_trucker is not None:
        query = query.filter(Product.is_trucker == is_trucker)
    if is_perforated is not None:
        query = query.filter(Product.is_perforated == is_perforated)

    # String filters
    if material:
        query = query.filter(Product.material.ilike(f"%{material}%"))
    if sweatband:
        query = query.filter(Product.sweatband.ilike(f"%{sweatband}%"))
    if closure_type:
        query = query.filter(Product.closure_type == closure_type)
    if profile:
        query = query.filter(Product.profile == profile)

    # Color filter — join to colorways
    if color:
        query = query.join(ProductColorway).filter(
            ProductColorway.name.ilike(f"%{color}%")
        ).distinct()

    # Sorting
    if sort == "price_asc":
        query = query.order_by(Product.base_price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.base_price.desc())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    else:
        query = query.order_by(Product.name.asc())

    products = query.offset(offset).limit(limit).all()

    # Attach primary image
    result = []
    for product in products:
        primary_img = (
            db.query(ProductImage)
            .filter(ProductImage.product_id == product.id, ProductImage.is_primary == True)
            .first()
        )
        data = ProductListResponse.model_validate(product)
        data.primary_image = primary_img.url if primary_img else None
        result.append(data)

    return result


@router.get("/{slug}", response_model=ProductDetailResponse)
async def get_product(slug: str, db: Session = Depends(get_db)):
    """Get product detail by slug."""
    product = (
        db.query(Product)
        .options(
            joinedload(Product.images),
            joinedload(Product.colorways),
            joinedload(Product.variants),
            joinedload(Product.decoration_options),
        )
        .filter(Product.slug == slug, Product.is_active == True)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/by-style/{style_number}", response_model=ProductDetailResponse)
async def get_product_by_style(style_number: str, db: Session = Depends(get_db)):
    """Get product by style number."""
    product = (
        db.query(Product)
        .options(
            joinedload(Product.images),
            joinedload(Product.colorways),
            joinedload(Product.variants),
            joinedload(Product.decoration_options),
        )
        .filter(Product.style_number == style_number, Product.is_active == True)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# === Admin product management ===

@router.post("/", response_model=ProductDetailResponse, status_code=201)
async def create_product(
    data: ProductCreate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Create a new product (admin only)."""
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductDetailResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Update a product (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Soft-delete a product (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    db.commit()
    return {"message": "Product deactivated"}


# === Admin product listing (includes inactive) ===

class AdminProductListItem(BaseModel):
    id: str
    name: str
    slug: str
    style_number: str
    collection: str
    base_price: int
    is_active: bool
    is_featured: bool
    primary_image: Optional[str] = None
    category_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/admin/all", response_model=list[AdminProductListItem])
async def admin_list_products(
    search: Optional[str] = None,
    collection: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """List ALL products including inactive (admin only)."""
    query = db.query(Product)

    if search:
        query = query.filter(
            Product.name.ilike(f"%{search}%")
            | Product.style_number.ilike(f"%{search}%")
        )
    if collection:
        query = query.filter(Product.collection == collection)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    products = query.order_by(Product.style_number.asc()).offset(offset).limit(limit).all()

    result = []
    for product in products:
        primary_img = (
            db.query(ProductImage)
            .filter(ProductImage.product_id == product.id, ProductImage.is_primary == True)
            .first()
        )
        item = AdminProductListItem(
            id=product.id,
            name=product.name,
            slug=product.slug,
            style_number=product.style_number,
            collection=product.collection or "",
            base_price=product.base_price,
            is_active=product.is_active,
            is_featured=product.is_featured,
            primary_image=primary_img.url if primary_img else None,
            category_id=product.category_id,
            created_at=product.created_at.isoformat() if product.created_at else None,
        )
        result.append(item)

    return result


# === Admin product images ===

@router.post("/{product_id}/images")
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    alt: str = Form(default=""),
    is_primary: bool = Form(default=False),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Upload a product image (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    from ..services.storage_service import save_file_bytes, generate_unique_filename

    ext = os.path.splitext(file.filename or "image.jpg")[1]
    filename = generate_unique_filename(f"upload{ext}")
    content = await file.read()
    relative_path = await save_file_bytes(content, "products", filename, file.content_type or "image/jpeg")
    url = relative_path

    # If setting as primary, unset existing primary
    if is_primary:
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.is_primary == True,
        ).update({"is_primary": False})

    # Get next sort order
    max_sort = (
        db.query(ProductImage.sort_order)
        .filter(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.desc())
        .first()
    )
    next_sort = (max_sort[0] + 1) if max_sort else 0

    image = ProductImage(
        product_id=product_id,
        url=url,
        alt=alt or product.name,
        sort_order=next_sort,
        is_primary=is_primary,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return {"id": image.id, "url": image.url, "sort_order": image.sort_order, "is_primary": image.is_primary}


class ImageReorderRequest(BaseModel):
    image_ids: list[str]


@router.put("/{product_id}/images/reorder")
async def reorder_product_images(
    product_id: str,
    data: ImageReorderRequest,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Reorder product images (admin only)."""
    for idx, image_id in enumerate(data.image_ids):
        db.query(ProductImage).filter(
            ProductImage.id == image_id,
            ProductImage.product_id == product_id,
        ).update({"sort_order": idx})
    db.commit()
    return {"message": "Images reordered"}


@router.delete("/images/{image_id}")
async def delete_product_image(
    image_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Delete a product image (admin only)."""
    image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    db.delete(image)
    db.commit()
    return {"message": "Image deleted"}


# === Admin colorway management ===

class ColorwayCreate(BaseModel):
    name: str
    crown_color: Optional[str] = None
    visor_color: Optional[str] = None
    mesh_color: Optional[str] = None
    sweatband_color: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0


class ColorwayUpdate(BaseModel):
    name: Optional[str] = None
    crown_color: Optional[str] = None
    visor_color: Optional[str] = None
    mesh_color: Optional[str] = None
    sweatband_color: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@router.post("/{product_id}/colorways", status_code=201)
async def create_colorway(
    product_id: str,
    data: ColorwayCreate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Add a colorway to a product (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    colorway = ProductColorway(product_id=product_id, **data.model_dump())
    db.add(colorway)
    db.commit()
    db.refresh(colorway)
    return {"id": colorway.id, "name": colorway.name}


@router.put("/colorways/{colorway_id}")
async def update_colorway(
    colorway_id: str,
    data: ColorwayUpdate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Update a colorway (admin only)."""
    colorway = db.query(ProductColorway).filter(ProductColorway.id == colorway_id).first()
    if not colorway:
        raise HTTPException(status_code=404, detail="Colorway not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(colorway, key, value)
    db.commit()
    db.refresh(colorway)
    return {"id": colorway.id, "name": colorway.name}


@router.delete("/colorways/{colorway_id}")
async def delete_colorway(
    colorway_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Delete a colorway (admin only)."""
    colorway = db.query(ProductColorway).filter(ProductColorway.id == colorway_id).first()
    if not colorway:
        raise HTTPException(status_code=404, detail="Colorway not found")
    db.delete(colorway)
    db.commit()
    return {"message": "Colorway deleted"}


# === Admin decoration option management ===

class DecorationCreate(BaseModel):
    location: str
    method: str
    is_available: bool = True
    additional_cost: int = 0


class DecorationUpdate(BaseModel):
    location: Optional[str] = None
    method: Optional[str] = None
    is_available: Optional[bool] = None
    additional_cost: Optional[int] = None


@router.post("/{product_id}/decorations", status_code=201)
async def create_decoration(
    product_id: str,
    data: DecorationCreate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Add a decoration option to a product (admin only)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    decoration = DecorationOption(product_id=product_id, **data.model_dump())
    db.add(decoration)
    db.commit()
    db.refresh(decoration)
    return {"id": decoration.id, "location": decoration.location, "method": decoration.method}


@router.put("/decorations/{decoration_id}")
async def update_decoration(
    decoration_id: str,
    data: DecorationUpdate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Update a decoration option (admin only)."""
    decoration = db.query(DecorationOption).filter(DecorationOption.id == decoration_id).first()
    if not decoration:
        raise HTTPException(status_code=404, detail="Decoration option not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(decoration, key, value)
    db.commit()
    db.refresh(decoration)
    return {"id": decoration.id, "location": decoration.location, "method": decoration.method}


@router.delete("/decorations/{decoration_id}")
async def delete_decoration(
    decoration_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Delete a decoration option (admin only)."""
    decoration = db.query(DecorationOption).filter(DecorationOption.id == decoration_id).first()
    if not decoration:
        raise HTTPException(status_code=404, detail="Decoration option not found")
    db.delete(decoration)
    db.commit()
    return {"message": "Decoration option deleted"}


# === Admin category management ===

class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    parent_id: Optional[str] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    parent_id: Optional[str] = None


@router.post("/categories", response_model=ProductCategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Create a product category (admin only)."""
    category = ProductCategory(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=ProductCategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Update a product category (admin only)."""
    category = db.query(ProductCategory).filter(ProductCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category
