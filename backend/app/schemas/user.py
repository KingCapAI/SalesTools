from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class TeamResponse(BaseModel):
    id: str
    name: str
    allowed_apps: List[str]

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    image: Optional[str] = None
    team_id: Optional[str] = None
    role: str = "member"
    provider: str
    provider_account_id: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    image: Optional[str] = None
    team_id: Optional[str] = None
    role: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    image: Optional[str] = None
    team_id: Optional[str] = None
    team: Optional[TeamResponse] = None
    role: str
    provider: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True
