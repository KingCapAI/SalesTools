from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class HatStyle(str, Enum):
    SIX_PANEL_HAT = "6-panel-hat"
    SIX_PANEL_TRUCKER = "6-panel-trucker"
    FIVE_PANEL_HAT = "5-panel-hat"
    FIVE_PANEL_TRUCKER = "5-panel-trucker"
    PERFORATED_SIX_PANEL = "perforated-6-panel"
    PERFORATED_FIVE_PANEL = "perforated-5-panel"


class Material(str, Enum):
    COTTON_TWILL = "cotton-twill"
    PERFORMANCE_POLYESTER = "performance-polyester"
    NYLON = "nylon"
    CANVAS = "canvas"


class StyleDirection(str, Enum):
    SIMPLE = "simple"
    MODERN = "modern"
    LUXURIOUS = "luxurious"
    SPORTY = "sporty"
    RUGGED = "rugged"
    RETRO = "retro"
    COLLEGIATE = "collegiate"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DesignVersionResponse(BaseModel):
    id: str
    design_id: str
    version_number: int
    prompt: str
    image_path: Optional[str] = None
    image_url: Optional[str] = None
    generation_status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DesignChatCreate(BaseModel):
    message: str


class DesignChatResponse(BaseModel):
    id: str
    design_id: str
    version_id: Optional[str] = None
    message: str
    is_user: bool
    user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DesignCreate(BaseModel):
    customer_name: str  # Text field for filtering/tracking
    brand_name: str  # Text field for filtering/tracking and Gemini prompt
    design_name: Optional[str] = None
    hat_style: HatStyle
    material: Material
    style_directions: List[StyleDirection]  # Up to 3 style directions
    custom_description: Optional[str] = None

    @field_validator('style_directions')
    @classmethod
    def validate_style_directions(cls, v):
        if len(v) == 0:
            raise ValueError('At least one style direction is required')
        if len(v) > 3:
            raise ValueError('Maximum 3 style directions allowed')
        return v


class DesignUpdate(BaseModel):
    design_name: Optional[str] = None
    approval_status: Optional[ApprovalStatus] = None
    shared_with_team: Optional[bool] = None


class RevisionCreate(BaseModel):
    revision_notes: str


class DesignResponse(BaseModel):
    id: str
    customer_name: str
    brand_name: str
    design_name: Optional[str] = None
    design_number: int
    current_version: int
    hat_style: str
    material: str
    style_directions: List[str]
    custom_description: Optional[str] = None
    status: str
    approval_status: str
    shared_with_team: bool
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    versions: List[DesignVersionResponse] = []
    chats: List[DesignChatResponse] = []

    class Config:
        from_attributes = True


class DesignListResponse(BaseModel):
    id: str
    customer_name: str
    brand_name: str
    design_name: Optional[str] = None
    design_number: int
    current_version: int
    hat_style: str
    material: str
    style_directions: List[str]
    status: str
    approval_status: str
    shared_with_team: bool
    created_at: datetime
    updated_at: datetime
    latest_image_path: Optional[str] = None

    class Config:
        from_attributes = True
