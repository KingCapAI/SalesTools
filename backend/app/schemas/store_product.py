"""Schemas for store products."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProductCategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    sort_order: int
    is_active: bool
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True


class ProductImageResponse(BaseModel):
    id: str
    url: str
    alt: Optional[str] = None
    sort_order: int
    is_primary: bool

    class Config:
        from_attributes = True


class ProductColorwayResponse(BaseModel):
    id: str
    name: str
    crown_color: str
    visor_color: str
    mesh_color: Optional[str] = None
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class ProductVariantResponse(BaseModel):
    id: str
    size: Optional[str] = None
    sku: str
    stock_qty: int
    is_active: bool
    colorway_id: Optional[str] = None

    class Config:
        from_attributes = True


class DecorationOptionResponse(BaseModel):
    id: str
    location: str
    method: str
    is_available: bool
    additional_cost: int

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    id: str
    name: str
    slug: str
    style_number: str
    collection: str
    base_price: int
    compare_at_price: Optional[int] = None
    is_featured: bool
    is_customizable: bool
    crown_type: Optional[str] = None
    closure_type: Optional[str] = None
    material: Optional[str] = None
    is_trucker: bool
    primary_image: Optional[str] = None
    category_id: Optional[str] = None

    class Config:
        from_attributes = True


class ProductDetailResponse(BaseModel):
    id: str
    name: str
    slug: str
    style_number: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    collection: str
    production_type: str
    base_price: int
    compare_at_price: Optional[int] = None
    panel_count: Optional[int] = None
    crown_type: Optional[str] = None
    closure_type: Optional[str] = None
    visor_type: Optional[str] = None
    material: Optional[str] = None
    sweatband: Optional[str] = None
    profile: Optional[str] = None
    is_trucker: bool
    is_perforated: bool
    is_active: bool
    is_featured: bool
    is_customizable: bool
    min_order_qty: int
    category_id: Optional[str] = None
    images: list[ProductImageResponse] = []
    colorways: list[ProductColorwayResponse] = []
    variants: list[ProductVariantResponse] = []
    decoration_options: list[DecorationOptionResponse] = []

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    slug: str
    style_number: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    collection: str
    production_type: str = "domestic"
    base_price: int
    compare_at_price: Optional[int] = None
    panel_count: Optional[int] = None
    crown_type: Optional[str] = None
    closure_type: Optional[str] = None
    visor_type: Optional[str] = None
    material: Optional[str] = None
    sweatband: Optional[str] = None
    profile: Optional[str] = None
    is_trucker: bool = False
    is_perforated: bool = False
    is_customizable: bool = True
    min_order_qty: int = 1
    category_id: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    base_price: Optional[int] = None
    compare_at_price: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_customizable: Optional[bool] = None
    min_order_qty: Optional[int] = None
    category_id: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
