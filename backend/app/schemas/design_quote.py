"""Pydantic schemas for design quotes."""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any
from datetime import datetime


class DesignQuoteCreate(BaseModel):
    """Create a quote for a design."""
    quote_type: Literal["domestic", "overseas"]
    quantity: int = Field(..., ge=24)

    # Decoration fields (common)
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None

    # Domestic-specific
    style_number: Optional[str] = None
    shipping_speed: Optional[str] = "Standard (5-7 Production Days)"
    include_rope: Optional[bool] = False
    num_dst_files: Optional[int] = 1

    # Overseas-specific
    hat_type: Optional[str] = None
    visor_decoration: Optional[str] = None
    design_addons: Optional[List[str]] = None
    accessories: Optional[List[str]] = None
    shipping_method: Optional[str] = "FOB CA"


class DesignQuoteUpdate(BaseModel):
    """Update an existing quote."""
    quantity: Optional[int] = Field(None, ge=24)
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None

    # Domestic-specific
    style_number: Optional[str] = None
    shipping_speed: Optional[str] = None
    include_rope: Optional[bool] = None
    num_dst_files: Optional[int] = None

    # Overseas-specific
    hat_type: Optional[str] = None
    visor_decoration: Optional[str] = None
    design_addons: Optional[List[str]] = None
    accessories: Optional[List[str]] = None
    shipping_method: Optional[str] = None


class DesignQuoteResponse(BaseModel):
    """Full quote response including cached calculations."""
    id: str
    design_id: str
    quote_type: str
    quantity: int

    # Decorations
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None

    # Domestic fields
    style_number: Optional[str] = None
    shipping_speed: Optional[str] = None
    include_rope: Optional[bool] = None
    num_dst_files: Optional[int] = None

    # Overseas fields
    hat_type: Optional[str] = None
    visor_decoration: Optional[str] = None
    design_addons: Optional[List[str]] = None
    accessories: Optional[List[str]] = None
    shipping_method: Optional[str] = None

    # Calculated results (stored in cents, returned as dollars)
    cached_price_breaks: Optional[List[Any]] = None
    cached_total: Optional[float] = None
    cached_per_piece: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DesignQuoteSummary(BaseModel):
    """Minimal quote info for dashboard display."""
    id: str
    quote_type: str
    quantity: int
    cached_total: Optional[float] = None
    cached_per_piece: Optional[float] = None
    updated_at: datetime

    class Config:
        from_attributes = True
