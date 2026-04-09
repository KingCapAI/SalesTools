"""Authentication service for e-commerce store users (email/password)."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models.store_user import StoreUser

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def generate_random_password(length: int = 12) -> str:
    """Generate a random password for programmatic account creation."""
    return secrets.token_urlsafe(length)


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against stored hash."""
    try:
        salt, hashed = stored_hash.split(":")
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == hashed
    except (ValueError, AttributeError):
        return False


def register_store_user(
    db: Session,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    phone: Optional[str] = None,
) -> StoreUser:
    """Register a new store user with email/password."""
    # Check if email already exists
    existing = db.query(StoreUser).filter(StoreUser.email == email).first()
    if existing:
        raise ValueError("An account with this email already exists")

    user = StoreUser(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role="customer",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_store_user(
    db: Session,
    email: str,
    password: str,
) -> Optional[StoreUser]:
    """Authenticate a store user by email/password."""
    user = db.query(StoreUser).filter(
        StoreUser.email == email.lower().strip()
    ).first()

    if not user or not user.password_hash:
        return None

    if not verify_password(password, user.password_hash):
        return None

    if user.status != "active":
        return None

    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()

    return user


def create_store_user_token(user: StoreUser) -> str:
    """Create a JWT token for a store user (includes role in payload)."""
    from jose import jwt as jose_jwt

    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    to_encode = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "user_type": "store",  # Distinguish from HQ users
        "exp": expire,
    }
    return jose_jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def generate_password_reset_token() -> str:
    """Generate a secure password reset token."""
    return secrets.token_urlsafe(32)


def generate_email_verification_token(user_id: str, email: str) -> str:
    """Generate a JWT token for email verification (24hr expiry)."""
    from jose import jwt as jose_jwt
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {
        "sub": user_id,
        "email": email,
        "purpose": "email_verification",
        "exp": expire,
    }
    return jose_jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_email_verification_token(token: str) -> dict:
    """Verify an email verification token. Returns {user_id, email} or raises."""
    from jose import jwt as jose_jwt, JWTError
    try:
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "email_verification":
            raise ValueError("Invalid token purpose")
        return {"user_id": payload["sub"], "email": payload["email"]}
    except JWTError:
        raise ValueError("Invalid or expired verification token")


def generate_password_reset_token_jwt(user_id: str, email: str) -> str:
    """Generate a JWT token for password reset (1hr expiry)."""
    from jose import jwt as jose_jwt
    expire = datetime.utcnow() + timedelta(hours=1)
    to_encode = {
        "sub": user_id,
        "email": email,
        "purpose": "password_reset",
        "exp": expire,
    }
    return jose_jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_password_reset_token_jwt(token: str) -> dict:
    """Verify a password reset token. Returns {user_id, email} or raises."""
    from jose import jwt as jose_jwt, JWTError
    try:
        payload = jose_jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("purpose") != "password_reset":
            raise ValueError("Invalid token purpose")
        return {"user_id": payload["sub"], "email": payload["email"]}
    except JWTError:
        raise ValueError("Invalid or expired reset token")


def submit_wholesale_application(
    db: Session,
    user: StoreUser,
    company_name: str,
    tax_id: Optional[str] = None,
    business_type: Optional[str] = None,
    annual_volume: Optional[str] = None,
    resale_certificate: Optional[str] = None,
    notes: Optional[str] = None,
) -> StoreUser:
    """Submit a wholesale application for a store user."""
    if user.application_status == "approved":
        raise ValueError("You already have an approved application")
    if user.application_status == "pending":
        raise ValueError("You already have a pending application")

    user.company_name = company_name
    user.tax_id = tax_id
    user.business_type = business_type
    user.annual_volume = annual_volume
    user.resale_certificate_path = resale_certificate
    user.application_status = "pending"
    user.application_date = datetime.utcnow()
    user.application_notes = notes
    # Mark as wholesale-pending (still customer role until approved)
    db.commit()
    db.refresh(user)
    return user


def submit_golf_application(
    db: Session,
    user: StoreUser,
    course_name: str,
    course_location: str,
    company_name: Optional[str] = None,
    proshop_contact: Optional[str] = None,
    notes: Optional[str] = None,
) -> StoreUser:
    """Submit a golf pro-shop application for a store user."""
    if user.application_status == "approved":
        raise ValueError("You already have an approved application")
    if user.application_status == "pending":
        raise ValueError("You already have a pending application")

    user.company_name = company_name
    user.course_name = course_name
    user.course_location = course_location
    user.proshop_contact = proshop_contact
    user.application_status = "pending"
    user.application_date = datetime.utcnow()
    user.application_notes = notes
    db.commit()
    db.refresh(user)
    return user


def review_application(
    db: Session,
    user: StoreUser,
    decision: str,
    reviewer_id: str,
    notes: Optional[str] = None,
    pricing_tier_id: Optional[str] = None,
) -> StoreUser:
    """Admin reviews a wholesale/golf application."""
    if user.application_status != "pending":
        raise ValueError("No pending application to review")

    user.application_status = decision  # "approved" or "rejected"
    user.approved_by = reviewer_id
    user.approved_at = datetime.utcnow()

    if notes:
        user.application_notes = (user.application_notes or "") + f"\n[Review]: {notes}"

    if decision == "approved":
        # Determine role based on application type
        if user.course_name:
            user.role = "golf"
        else:
            user.role = "wholesale"

        if pricing_tier_id:
            user.pricing_tier_id = pricing_tier_id

    db.commit()
    db.refresh(user)
    return user
