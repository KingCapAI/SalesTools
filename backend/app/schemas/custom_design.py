from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

from .design import HatStyle, Material, HatStructure, ClosureType, ApprovalStatus, DesignVersionResponse, DesignChatResponse, DesignQuoteSummaryResponse


class DecorationLocation(str, Enum):
    FRONT = "front"
    LEFT = "left"
    RIGHT = "right"
    BACK = "back"
    VISOR = "visor"


class DecorationMethod(str, Enum):
    EMBROIDERY = "embroidery"
    SCREEN_PRINT = "screen_print"
    PATCH = "patch"
    THREE_D_PUFF = "3d_puff"
    LASER_CUT = "laser_cut"
    HEAT_TRANSFER = "heat_transfer"
    SUBLIMATION = "sublimation"


class DecorationSize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    CUSTOM = "custom"


class LocationLogoCreate(BaseModel):
    """Input for a single location's logo specification."""
    location: DecorationLocation
    logo_path: str  # Path to uploaded logo file
    logo_filename: str
    decoration_method: DecorationMethod
    size: DecorationSize
    size_details: Optional[str] = None  # e.g., "3x2 inches"


class LocationLogoResponse(BaseModel):
    """Response for a single location's logo specification."""
    id: str
    design_id: str
    location: str
    logo_path: str
    logo_filename: str
    decoration_method: str
    size: str
    size_details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CustomDesignCreate(BaseModel):
    """Create a custom design with per-location logo specifications."""
    customer_name: str
    brand_name: str
    design_name: Optional[str] = None
    hat_style: HatStyle
    material: Material
    structure: HatStructure  # Mandatory for Mockup Builder
    closure: ClosureType  # Mandatory for Mockup Builder
    crown_color: Optional[str] = "black"  # Color of the hat crown
    visor_color: Optional[str] = "black"  # Color of the visor
    reference_hat_path: Optional[str] = None  # Path to reference hat image
    location_logos: List[LocationLogoCreate]

    @field_validator('location_logos')
    @classmethod
    def validate_location_logos(cls, v):
        if len(v) == 0:
            raise ValueError('At least one location logo is required')
        # Check for duplicate locations
        locations = [logo.location for logo in v]
        if len(locations) != len(set(locations)):
            raise ValueError('Each location can only have one logo')
        return v


class CustomDesignUpdate(BaseModel):
    """Update a custom design."""
    design_name: Optional[str] = None
    approval_status: Optional[ApprovalStatus] = None
    shared_with_team: Optional[bool] = None


class CustomDesignResponse(BaseModel):
    """Full response for a custom design."""
    id: str
    customer_name: str
    brand_name: str
    design_name: Optional[str] = None
    design_number: int
    current_version: int
    hat_style: str
    material: str
    structure: Optional[str] = None
    closure: Optional[str] = None
    crown_color: Optional[str] = None
    visor_color: Optional[str] = None
    design_type: str
    reference_hat_path: Optional[str] = None
    status: str
    approval_status: str
    shared_with_team: bool
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    location_logos: List[LocationLogoResponse] = []
    versions: List[DesignVersionResponse] = []
    chats: List[DesignChatResponse] = []
    quote_summary: Optional[DesignQuoteSummaryResponse] = None

    class Config:
        from_attributes = True


class CustomDesignListResponse(BaseModel):
    """List response for custom designs."""
    id: str
    customer_name: str
    brand_name: str
    design_name: Optional[str] = None
    design_number: int
    current_version: int
    hat_style: str
    material: str
    structure: Optional[str] = None
    closure: Optional[str] = None
    crown_color: Optional[str] = None
    visor_color: Optional[str] = None
    design_type: str
    reference_hat_path: Optional[str] = None
    status: str
    approval_status: str
    shared_with_team: bool
    created_at: datetime
    updated_at: datetime
    latest_image_path: Optional[str] = None
    location_logos: List[LocationLogoResponse] = []
    quote_summary: Optional[DesignQuoteSummaryResponse] = None

    class Config:
        from_attributes = True


class LocationLogoUploadResponse(BaseModel):
    """Response for uploading a location logo."""
    logo_path: str
    logo_filename: str


class ReferenceHatUploadResponse(BaseModel):
    """Response for uploading a reference hat image."""
    reference_hat_path: str
    filename: str
