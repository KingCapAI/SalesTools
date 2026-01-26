"""
Pydantic schemas for quote requests and responses.
"""

from typing import Optional
from pydantic import BaseModel, Field


class DomesticQuoteRequest(BaseModel):
    """Request schema for domestic quote calculation."""
    design_number: Optional[str] = Field(None, description="Optional design number for quote sheet")
    style_number: str = Field(..., description="Hat style number (e.g., '250', '360-T')")
    quantity: int = Field(..., ge=24, description="Order quantity (minimum 24)")
    front_decoration: Optional[str] = Field(None, description="Front decoration method")
    left_decoration: Optional[str] = Field(None, description="Left side decoration method")
    right_decoration: Optional[str] = Field(None, description="Right side decoration method")
    back_decoration: Optional[str] = Field(None, description="Back decoration method")
    shipping_speed: str = Field("Standard (5-7 Production Days)", description="Shipping speed")
    include_rope: bool = Field(False, description="Include rope add-on")
    num_dst_files: int = Field(1, ge=0, description="Number of DST files for digitizing")


class OverseasQuoteRequest(BaseModel):
    """Request schema for overseas quote calculation."""
    design_number: Optional[str] = Field(None, description="Optional design number for quote sheet")
    hat_type: str = Field(..., description="Hat type (Basic, Classic, Comfort, Sport)")
    quantity: int = Field(..., ge=144, description="Order quantity (minimum 144)")
    front_decoration: Optional[str] = Field(None, description="Front decoration method")
    left_decoration: Optional[str] = Field(None, description="Left side decoration method")
    right_decoration: Optional[str] = Field(None, description="Right side decoration method")
    back_decoration: Optional[str] = Field(None, description="Back decoration method")
    visor_decoration: Optional[str] = Field(None, description="Visor decoration method")
    design_addons: Optional[list[str]] = Field(None, description="List of design add-ons")
    accessories: Optional[list[str]] = Field(None, description="List of accessories")
    shipping_method: str = Field("FOB CA", description="Shipping method")


class PriceBreakItem(BaseModel):
    """Price breakdown for a quantity break."""
    quantity_break: int
    blank_price: float
    front_decoration_price: float = 0
    left_decoration_price: float = 0
    right_decoration_price: float = 0
    back_decoration_price: float = 0
    visor_decoration_price: float = 0
    rush_fee: float = 0
    rope_price: float = 0
    addons_price: float = 0
    accessories_price: float = 0
    hat_subtotal: float = 0
    shipping_price: float = 0
    per_piece_price: float
    digitizing_fee: float = 0
    subtotal: float = 0
    total: float


class DomesticQuoteResponse(BaseModel):
    """Response schema for domestic quote calculation."""
    quote_type: str = "domestic"
    style_number: str
    style_name: str
    collection: str
    quantity: int
    front_decoration: Optional[str]
    left_decoration: Optional[str]
    right_decoration: Optional[str]
    back_decoration: Optional[str]
    shipping_speed: str
    include_rope: bool
    price_breaks: list[dict]


class OverseasQuoteResponse(BaseModel):
    """Response schema for overseas quote calculation."""
    quote_type: str = "overseas"
    hat_type: str
    quantity: int
    front_decoration: Optional[str]
    left_decoration: Optional[str]
    right_decoration: Optional[str]
    back_decoration: Optional[str]
    visor_decoration: Optional[str]
    design_addons: Optional[list[str]]
    accessories: Optional[list[str]]
    shipping_method: str
    price_breaks: list[dict]


class QuoteOptionsResponse(BaseModel):
    """Response schema for available quote options."""
    domestic: dict
    overseas: dict


class QuoteSheetItem(BaseModel):
    """A single quote item in a quote sheet."""
    type: str = Field(..., description="Quote type: 'domestic' or 'overseas'")
    design_number: str = Field(..., description="Design identifier")
    request: dict = Field(..., description="The quote request parameters")


class QuoteSheetExportRequest(BaseModel):
    """Request schema for exporting a quote sheet."""
    quotes: list[QuoteSheetItem] = Field(..., description="List of quotes to export")
