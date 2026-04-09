"""Admin customer management routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.store_user import StoreUser
from ..models.store_order import Order
from ..models.address import Address
from ..models.store_pricing import PricingTier
from ..utils.store_dependencies import require_store_role
from ..services.email_service import send_application_approved, send_application_rejected

router = APIRouter(prefix="/admin/customers", tags=["Admin Customers"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CustomerListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    company_name: Optional[str] = None
    role: str
    status: str
    application_status: Optional[str] = None
    pricing_tier_id: Optional[str] = None
    salesperson_id: Optional[str] = None
    order_count: int = 0
    total_spent: int = 0  # cents
    created_at: Optional[datetime] = None


class CustomerDetailResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    website: Optional[str] = None
    role: str
    status: str
    application_status: Optional[str] = None
    application_date: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    application_notes: Optional[str] = None
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    annual_volume: Optional[str] = None
    course_name: Optional[str] = None
    course_location: Optional[str] = None
    proshop_contact: Optional[str] = None
    ups_account_number: Optional[str] = None
    fedex_account_number: Optional[str] = None
    pricing_tier_id: Optional[str] = None
    salesperson_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    order_count: int = 0
    total_spent: int = 0
    addresses: list[dict] = []
    recent_orders: list[dict] = []

    class Config:
        from_attributes = True


class CustomerUpdate(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None
    pricing_tier_id: Optional[str] = None
    salesperson_id: Optional[str] = None
    application_notes: Optional[str] = None


class ApplicationReview(BaseModel):
    decision: str  # approved or rejected
    notes: Optional[str] = None
    pricing_tier_id: Optional[str] = None


class ApplicationListItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    company_name: Optional[str] = None
    role: str
    application_status: str
    application_date: Optional[datetime] = None
    business_type: Optional[str] = None
    course_name: Optional[str] = None


class PricingTierResponse(BaseModel):
    id: str
    name: str
    tier_type: str
    discount_pct: float
    is_default: bool

    class Config:
        from_attributes = True


class SalespersonResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary")
async def customer_summary(
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Get customer counts grouped by role."""
    counts = (
        db.query(StoreUser.role, func.count(StoreUser.id))
        .filter(StoreUser.role.in_(["customer", "wholesale", "golf"]))
        .group_by(StoreUser.role)
        .all()
    )
    result = {"customer": 0, "wholesale": 0, "golf": 0}
    for role, count in counts:
        result[role] = count
    result["total"] = sum(result.values())
    return result


@router.get("", response_model=list[CustomerListItem])
async def list_customers(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    has_salesperson: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """List customers with search and filters."""
    query = (
        db.query(
            StoreUser,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total), 0).label("total_spent"),
        )
        .outerjoin(Order, (Order.store_user_id == StoreUser.id) & (Order.status != "cancelled"))
        .group_by(StoreUser.id)
    )

    # Exclude admin/salesperson from customer list
    if role:
        query = query.filter(StoreUser.role == role)
    else:
        query = query.filter(StoreUser.role.in_(["customer", "wholesale", "golf"]))

    if status_filter:
        query = query.filter(StoreUser.status == status_filter)

    if search:
        query = query.filter(
            StoreUser.email.ilike(f"%{search}%")
            | StoreUser.first_name.ilike(f"%{search}%")
            | StoreUser.last_name.ilike(f"%{search}%")
            | StoreUser.company_name.ilike(f"%{search}%")
        )

    if has_salesperson is True:
        query = query.filter(StoreUser.salesperson_id.isnot(None))
    elif has_salesperson is False:
        query = query.filter(StoreUser.salesperson_id.is_(None))

    rows = (
        query.order_by(StoreUser.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        CustomerListItem(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            company_name=user.company_name,
            role=user.role,
            status=user.status,
            application_status=user.application_status,
            pricing_tier_id=user.pricing_tier_id,
            salesperson_id=user.salesperson_id,
            order_count=order_count,
            total_spent=total_spent,
            created_at=user.created_at,
        )
        for user, order_count, total_spent in rows
    ]


@router.get("/applications", response_model=list[ApplicationListItem])
async def list_applications(
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """List pending wholesale/golf applications."""
    users = (
        db.query(StoreUser)
        .filter(StoreUser.application_status == "pending")
        .order_by(StoreUser.application_date.asc())
        .all()
    )

    return [
        ApplicationListItem(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            company_name=u.company_name,
            role=u.role,
            application_status=u.application_status or "pending",
            application_date=u.application_date,
            business_type=u.business_type,
            course_name=u.course_name,
        )
        for u in users
    ]


@router.get("/pricing-tiers", response_model=list[PricingTierResponse])
async def list_pricing_tiers(
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """List all pricing tiers."""
    return db.query(PricingTier).order_by(PricingTier.name).all()


@router.get("/salespersons", response_model=list[SalespersonResponse])
async def list_salespersons(
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """List all users with salesperson role."""
    users = (
        db.query(StoreUser)
        .filter(StoreUser.role == "salesperson", StoreUser.status == "active")
        .order_by(StoreUser.first_name)
        .all()
    )
    return [
        SalespersonResponse(id=u.id, first_name=u.first_name, last_name=u.last_name, email=u.email)
        for u in users
    ]


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer(
    customer_id: str,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Get customer detail with orders and addresses."""
    user = db.query(StoreUser).filter(StoreUser.id == customer_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Order stats
    order_stats = (
        db.query(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .filter(Order.store_user_id == customer_id, Order.status != "cancelled")
        .first()
    )

    # Recent orders
    recent = (
        db.query(Order)
        .filter(Order.store_user_id == customer_id)
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    # Addresses
    addresses = (
        db.query(Address)
        .filter(Address.store_user_id == customer_id)
        .order_by(Address.is_default.desc())
        .all()
    )

    return CustomerDetailResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        phone=user.phone,
        company_name=user.company_name,
        website=user.website,
        role=user.role,
        status=user.status,
        application_status=user.application_status,
        application_date=user.application_date,
        approved_by=user.approved_by,
        approved_at=user.approved_at,
        application_notes=user.application_notes,
        tax_id=user.tax_id,
        business_type=user.business_type,
        annual_volume=user.annual_volume,
        course_name=user.course_name,
        course_location=user.course_location,
        proshop_contact=user.proshop_contact,
        ups_account_number=user.ups_account_number,
        fedex_account_number=user.fedex_account_number,
        pricing_tier_id=user.pricing_tier_id,
        salesperson_id=user.salesperson_id,
        created_at=user.created_at,
        updated_at=user.updated_at,
        order_count=order_stats[0] or 0,
        total_spent=order_stats[1] or 0,
        addresses=[
            {
                "id": a.id,
                "label": a.label,
                "first_name": a.first_name,
                "last_name": a.last_name,
                "company": a.company,
                "line1": a.line1,
                "line2": a.line2,
                "city": a.city,
                "state": a.state,
                "postal_code": a.postal_code,
                "country": a.country,
                "phone": a.phone,
                "is_default": a.is_default,
            }
            for a in addresses
        ],
        recent_orders=[
            {
                "id": o.id,
                "order_number": o.order_number,
                "status": o.status,
                "total": o.total,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in recent
        ],
    )


@router.put("/{customer_id}", response_model=CustomerDetailResponse)
async def update_customer(
    customer_id: str,
    data: CustomerUpdate,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Update customer (role, status, pricing tier, salesperson)."""
    user = db.query(StoreUser).filter(StoreUser.id == customer_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)

    # Re-fetch with full detail
    return await get_customer(customer_id, admin=admin, db=db)


@router.post("/{customer_id}/review")
async def review_application(
    customer_id: str,
    data: ApplicationReview,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Approve or reject a wholesale/golf application."""
    user = db.query(StoreUser).filter(StoreUser.id == customer_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")
    if user.application_status != "pending":
        raise HTTPException(status_code=400, detail="Application is not pending")

    account_type = "golf" if user.course_name else "wholesale"

    if data.decision == "approved":
        user.application_status = "approved"
        user.approved_by = admin.id
        user.approved_at = datetime.utcnow()
        user.role = account_type
        if data.pricing_tier_id:
            user.pricing_tier_id = data.pricing_tier_id
    elif data.decision == "rejected":
        user.application_status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    if data.notes:
        user.application_notes = data.notes

    db.commit()

    # Send approval/rejection email to customer
    if data.decision == "approved":
        verification_url = None
        if not user.email_verified_at:
            from ..services.store_auth_service import generate_email_verification_token
            from ..config import get_settings
            _settings = get_settings()
            token = generate_email_verification_token(user.id, user.email)
            verification_url = f"{_settings.store_frontend_url}/verify-email?token={token}"
        send_application_approved(
            to_email=user.email,
            first_name=user.first_name,
            account_type=account_type,
            verification_url=verification_url,
        )
    else:
        send_application_rejected(
            to_email=user.email,
            first_name=user.first_name,
            account_type=account_type,
            reason=data.notes,
        )

    return {"message": f"Application {data.decision}", "user_id": customer_id}
