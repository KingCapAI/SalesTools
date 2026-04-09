"""Store (e-commerce) authentication routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..schemas.store_auth import (
    StoreUserRegister,
    StoreUserLogin,
    StoreUserResponse,
    StoreTokenResponse,
    StoreUserUpdate,
    WholesaleApplication,
    GolfApplication,
    ApplicationReview,
    PasswordResetRequest,
    PasswordReset,
)
from ..services.store_auth_service import (
    register_store_user,
    authenticate_store_user,
    create_store_user_token,
    submit_wholesale_application,
    submit_golf_application,
    review_application,
    generate_email_verification_token,
    verify_email_verification_token,
    generate_password_reset_token_jwt,
    verify_password_reset_token_jwt,
    hash_password,
)
from ..utils.store_dependencies import require_store_auth, require_store_role
from ..models.store_user import StoreUser
from ..services.email_service import (
    send_welcome_email,
    send_wholesale_application_received,
    send_golf_application_received,
    send_email_verification,
    send_password_reset_email,
    send_password_changed,
    send_application_approved,
    send_application_rejected,
    send_new_application_alert,
)

settings = get_settings()

router = APIRouter(prefix="/store/auth", tags=["Store Authentication"])


def _get_staff_emails(db: Session, roles: list[str]) -> list[str]:
    """Get email addresses for staff members with given roles."""
    staff = db.query(StoreUser).filter(
        StoreUser.role.in_(roles),
        StoreUser.status == "active",
    ).all()
    return [s.email for s in staff]


def _notify_staff_new_application(db: Session, applicant: StoreUser, account_type: str):
    """Send notification to staff about a new application."""
    staff_emails = _get_staff_emails(db, ["admin", "salesperson", "purchasing_manager"])
    company = applicant.company_name or applicant.course_name or "N/A"
    for email in staff_emails:
        send_new_application_alert(
            to_email=email,
            customer_name=f"{applicant.first_name} {applicant.last_name}",
            company_name=company,
            account_type=account_type,
        )


@router.post("/register", status_code=201)
async def register(data: StoreUserRegister, db: Session = Depends(get_db)):
    """Register a new customer account."""
    try:
        user = register_store_user(
            db=db,
            email=data.email,
            password=data.password,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
        )

        # Generate verification token and send verification email
        token = generate_email_verification_token(user.id, user.email)
        verification_url = f"{settings.store_frontend_url}/verify-email?token={token}"
        send_email_verification(to_email=user.email, first_name=user.first_name, verification_url=verification_url)

        return {"message": "Account created. Please check your email to verify your account.", "email": user.email}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=StoreTokenResponse)
async def login(data: StoreUserLogin, db: Session = Depends(get_db)):
    """Login with email and password."""
    user = authenticate_store_user(db=db, email=data.email, password=data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.email_verified_at:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in. Check your inbox for the verification link.",
        )

    token = create_store_user_token(user)
    return StoreTokenResponse(
        access_token=token,
        user=StoreUserResponse.model_validate(user),
    )


@router.get("/me", response_model=StoreUserResponse)
async def get_me(user: StoreUser = Depends(require_store_auth)):
    """Get current authenticated store user."""
    return user


@router.put("/me", response_model=StoreUserResponse)
async def update_profile(
    data: StoreUserUpdate,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.post("/apply/wholesale", response_model=StoreUserResponse)
async def apply_wholesale(
    data: WholesaleApplication,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Submit a wholesale account application."""
    try:
        updated_user = submit_wholesale_application(
            db=db,
            user=user,
            company_name=data.company_name,
            tax_id=data.tax_id,
            business_type=data.business_type,
            annual_volume=data.annual_volume,
            resale_certificate=data.resale_certificate,
            notes=data.notes,
        )

        # Send wholesale application confirmation email
        send_wholesale_application_received(
            to_email=user.email,
            company_name=data.company_name,
        )

        # Notify staff about new application
        _notify_staff_new_application(db, user, "wholesale")

        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/apply/golf", response_model=StoreUserResponse)
async def apply_golf(
    data: GolfApplication,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Submit a golf pro-shop account application."""
    try:
        updated_user = submit_golf_application(
            db=db,
            user=user,
            course_name=data.course_name,
            course_location=data.course_location,
            company_name=data.company_name,
            proshop_contact=data.proshop_contact,
            notes=data.notes,
        )

        # Send golf application confirmation email
        send_golf_application_received(
            to_email=user.email,
            course_name=data.course_name,
        )

        # Notify staff about new application
        _notify_staff_new_application(db, user, "golf")

        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Email verification & password reset endpoints ===

@router.get("/verify-email")
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify a user's email address via token link."""
    try:
        data = verify_email_verification_token(token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = db.query(StoreUser).filter(StoreUser.id == data["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email_verified_at:
        return {"message": "Email already verified. You can log in."}

    user.email_verified_at = datetime.utcnow()
    db.commit()

    # Send welcome email after verification
    send_welcome_email(to_email=user.email, first_name=user.first_name)

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/resend-verification")
async def resend_verification(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """Resend email verification link."""
    user = db.query(StoreUser).filter(StoreUser.email == data.email.lower().strip()).first()
    if not user:
        # Don't reveal if user exists
        return {"message": "If an account exists with this email, a verification link has been sent."}

    if user.email_verified_at:
        return {"message": "Email is already verified. You can log in."}

    token = generate_email_verification_token(user.id, user.email)
    verification_url = f"{settings.store_frontend_url}/verify-email?token={token}"
    send_email_verification(to_email=user.email, first_name=user.first_name, verification_url=verification_url)

    return {"message": "If an account exists with this email, a verification link has been sent."}


@router.post("/forgot-password")
async def forgot_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """Send a password reset link."""
    user = db.query(StoreUser).filter(StoreUser.email == data.email.lower().strip()).first()
    if not user:
        # Don't reveal if user exists
        return {"message": "If an account exists with this email, a password reset link has been sent."}

    token = generate_password_reset_token_jwt(user.id, user.email)
    reset_url = f"{settings.store_frontend_url}/reset-password?token={token}"
    send_password_reset_email(to_email=user.email, first_name=user.first_name, reset_url=reset_url)

    return {"message": "If an account exists with this email, a password reset link has been sent."}


@router.post("/reset-password")
async def reset_password(data: PasswordReset, db: Session = Depends(get_db)):
    """Reset password using a valid reset token."""
    try:
        token_data = verify_password_reset_token_jwt(data.token)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user = db.query(StoreUser).filter(StoreUser.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(data.new_password)
    # Also verify email if not already (they clicked a link in their email)
    if not user.email_verified_at:
        user.email_verified_at = datetime.utcnow()
    db.commit()

    send_password_changed(to_email=user.email, first_name=user.first_name)

    return {"message": "Password has been reset successfully. You can now log in with your new password."}


# === Admin endpoints ===

@router.get("/applications", response_model=list[StoreUserResponse])
async def list_applications(
    status_filter: str = "pending",
    user: StoreUser = Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """List pending wholesale/golf applications (admin only)."""
    query = db.query(StoreUser).filter(
        StoreUser.application_status == status_filter
    )
    return query.order_by(StoreUser.application_date.desc()).all()


@router.post("/applications/{user_id}/review", response_model=StoreUserResponse)
async def review_user_application(
    user_id: str,
    data: ApplicationReview,
    admin: StoreUser = Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Approve or reject a wholesale/golf application (admin only)."""
    applicant = db.query(StoreUser).filter(StoreUser.id == user_id).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        updated = review_application(
            db=db,
            user=applicant,
            decision=data.decision,
            reviewer_id=admin.id,
            notes=data.notes,
            pricing_tier_id=data.pricing_tier_id,
        )

        if data.decision == "approved":
            account_type = "golf" if applicant.course_name else "wholesale"
            # If email not verified, include verification URL in approval email
            verification_url = None
            if not applicant.email_verified_at:
                token = generate_email_verification_token(applicant.id, applicant.email)
                verification_url = f"{settings.store_frontend_url}/verify-email?token={token}"
            send_application_approved(
                to_email=applicant.email,
                first_name=applicant.first_name,
                account_type=account_type,
                verification_url=verification_url,
            )
        elif data.decision == "rejected":
            account_type = "golf" if applicant.course_name else "wholesale"
            send_application_rejected(
                to_email=applicant.email,
                first_name=applicant.first_name,
                account_type=account_type,
                reason=data.notes,
            )

        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
