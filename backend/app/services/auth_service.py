"""Authentication service for Microsoft OAuth handling."""

import httpx
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import User, Team
from ..utils.dependencies import create_access_token

settings = get_settings()


async def get_microsoft_oauth_url(state: Optional[str] = None) -> str:
    """Generate Microsoft OAuth authorization URL."""
    tenant = settings.microsoft_tenant_id or "common"
    params = {
        "client_id": settings.microsoft_client_id,
        "redirect_uri": f"{settings.backend_url}/api/auth/microsoft/callback",
        "response_type": "code",
        "scope": "openid email profile User.Read",
        "response_mode": "query",
    }
    if state:
        params["state"] = state

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{query}"


async def exchange_microsoft_code(code: str) -> Dict[str, Any]:
    """Exchange Microsoft authorization code for tokens and user info."""
    tenant = settings.microsoft_tenant_id or "common"

    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_response = await client.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": settings.microsoft_client_id,
                "client_secret": settings.microsoft_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.backend_url}/api/auth/microsoft/callback",
                "scope": "openid email profile User.Read",
            },
        )
        tokens = token_response.json()

        if "error" in tokens:
            raise ValueError(f"Token exchange failed: {tokens.get('error_description', tokens.get('error'))}")

        # Get user info from Microsoft Graph
        user_response = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_info = user_response.json()

        return {
            "provider": "microsoft",
            "provider_account_id": user_info.get("id"),
            "email": user_info.get("mail") or user_info.get("userPrincipalName"),
            "name": user_info.get("displayName"),
            "image": None,  # Microsoft Graph photo requires separate request
        }


def get_or_create_user(
    db: Session,
    provider: str,
    provider_account_id: str,
    email: str,
    name: str,
    image: Optional[str] = None,
) -> User:
    """Get existing user or create new one from OAuth data."""
    # Try to find existing user by provider account
    user = (
        db.query(User)
        .filter(
            User.provider == provider,
            User.provider_account_id == provider_account_id,
        )
        .first()
    )

    if user:
        # Update last login
        user.last_login_at = datetime.utcnow()
        if image and not user.image:
            user.image = image
        db.commit()
        return user

    # Try to find by email (user might exist from different provider)
    user = db.query(User).filter(User.email == email).first()

    if user:
        # User exists with different provider - could handle linking here
        # For now, update the provider info
        user.provider = provider
        user.provider_account_id = provider_account_id
        user.last_login_at = datetime.utcnow()
        if image:
            user.image = image
        db.commit()
        return user

    # Get default team (sales team)
    default_team = db.query(Team).filter(Team.name == "sales").first()

    # Create new user
    user = User(
        email=email,
        name=name,
        image=image,
        provider=provider,
        provider_account_id=provider_account_id,
        team_id=default_team.id if default_team else None,
        role="member",
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def create_user_token(user: User) -> str:
    """Create a JWT token for a user."""
    return create_access_token(user_id=user.id, email=user.email)
