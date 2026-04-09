"""Schemas for store (e-commerce) authentication."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class StoreUserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    phone: Optional[str] = None


class StoreUserLogin(BaseModel):
    email: EmailStr
    password: str


class StoreUserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    website: Optional[str] = None
    role: str
    status: str
    application_status: Optional[str] = None
    pricing_tier_id: Optional[str] = None
    email_verified_at: Optional[datetime] = None
    ups_account_number: Optional[str] = None
    fedex_account_number: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StoreTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: StoreUserResponse


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class StoreUserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    website: Optional[str] = None
    ups_account_number: Optional[str] = None
    fedex_account_number: Optional[str] = None


class WholesaleApplication(BaseModel):
    company_name: str
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    annual_volume: Optional[str] = None
    resale_certificate: Optional[str] = None  # file path after upload
    tax_exemption: Optional[str] = None  # file path after upload
    website: Optional[str] = None
    notes: Optional[str] = None


class GolfApplication(BaseModel):
    company_name: Optional[str] = None
    course_name: str
    course_location: str
    proshop_contact: Optional[str] = None
    resale_certificate: Optional[str] = None  # file path after upload
    tax_exemption: Optional[str] = None  # file path after upload
    notes: Optional[str] = None


class ApplicationReview(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    notes: Optional[str] = None
    pricing_tier_id: Optional[str] = None
