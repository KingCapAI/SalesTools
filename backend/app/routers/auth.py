"""Authentication routes for Microsoft OAuth."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import get_settings
from ..services.auth_service import (
    get_microsoft_oauth_url,
    exchange_microsoft_code,
    get_or_create_user,
    create_user_token,
)
from ..utils.dependencies import require_auth
from ..schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.get("/microsoft")
async def microsoft_login():
    """Redirect to Microsoft OAuth."""
    url = await get_microsoft_oauth_url()
    return RedirectResponse(url=url)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle Microsoft OAuth callback."""
    try:
        user_info = await exchange_microsoft_code(code)

        user = get_or_create_user(
            db=db,
            provider=user_info["provider"],
            provider_account_id=user_info["provider_account_id"],
            email=user_info["email"],
            name=user_info["name"],
            image=user_info.get("image"),
        )

        token = create_user_token(user)

        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/callback?token={token}"
        )

    except Exception as e:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?message={str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user=Depends(require_auth)):
    """Get current authenticated user info."""
    return user


@router.post("/logout")
async def logout(user=Depends(require_auth)):
    """Logout user (client should discard token)."""
    return {"message": "Logged out successfully"}
