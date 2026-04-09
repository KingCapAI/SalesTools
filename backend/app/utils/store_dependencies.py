"""Dependencies for store (e-commerce) authentication and authorization."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..config import get_settings
from ..models.store_user import StoreUser

security = HTTPBearer(auto_error=False)
settings = get_settings()


def decode_store_token(token: str) -> Optional[dict]:
    """Decode and validate a store user JWT token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        user_type = payload.get("user_type")
        if user_id is None or user_type != "store":
            return None
        return payload
    except JWTError:
        return None


async def get_current_store_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[StoreUser]:
    """Get current store user from JWT token (optional)."""
    if credentials is None:
        return None

    payload = decode_store_token(credentials.credentials)
    if payload is None:
        return None

    user = db.query(StoreUser).filter(StoreUser.id == payload["sub"]).first()
    return user


async def require_store_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> StoreUser:
    """Require store user authentication."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_store_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(StoreUser).filter(StoreUser.id == payload["sub"]).first()
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_store_role(*roles: str):
    """Dependency factory to require specific store user roles."""
    async def _require_role(
        user: StoreUser = Depends(require_store_auth),
    ) -> StoreUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(roles)}",
            )
        return user
    return _require_role
