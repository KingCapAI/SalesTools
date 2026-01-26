"""User management routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Team
from ..schemas.user import UserResponse, UserUpdate, TeamResponse
from ..utils.dependencies import require_auth

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(user=Depends(require_auth)):
    """Get current user's profile."""
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """Update current user's profile."""
    if user_data.name is not None:
        user.name = user_data.name

    db.commit()
    db.refresh(user)
    return user


@router.get("/teams", response_model=List[TeamResponse])
async def list_teams(
    db: Session = Depends(get_db),
    user=Depends(require_auth),
):
    """List all teams (admin only in production)."""
    teams = db.query(Team).all()
    return teams
