from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .brand import BrandList


class CustomerCreate(BaseModel):
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    id: str
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    notes: Optional[str] = None
    created_by_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    brands: List[BrandList] = []

    class Config:
        from_attributes = True


class CustomerList(BaseModel):
    id: str
    name: str
    contact_email: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
