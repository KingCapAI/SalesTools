from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BrandAssetResponse(BaseModel):
    id: str
    type: str
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    scraped_data: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BrandCreate(BaseModel):
    customer_id: str
    name: str
    website: Optional[str] = None


class BrandUpdate(BaseModel):
    name: Optional[str] = None
    website: Optional[str] = None


class BrandResponse(BaseModel):
    id: str
    customer_id: str
    name: str
    website: Optional[str] = None
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    brand_assets: List[BrandAssetResponse] = []

    class Config:
        from_attributes = True


class BrandList(BaseModel):
    id: str
    customer_id: str
    name: str
    website: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
