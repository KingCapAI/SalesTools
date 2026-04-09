"""Sales portal routes - salesperson dashboard, order creation, quotes."""

import json
import secrets
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime, timedelta

from ..database import get_db
from ..models.store_user import StoreUser
from ..models.store_order import Order, OrderItem, OrderStatusHistory
from ..models.store_product import Product, ProductVariant
from ..models.store_quote import Quote, QuoteLineItem
from ..models.store_pricing import PricingTier
from ..models.address import Address
from ..utils.store_dependencies import require_store_role
from ..services.store_auth_service import hash_password
from ..services.email_service import send_customer_account_created, send_quote_to_customer

router = APIRouter(prefix="/sales", tags=["Sales Portal"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SalesDashboardResponse(BaseModel):
    my_orders: int
    my_revenue: int  # cents
    my_customers: int
    open_quotes: int
    recent_orders: list[dict] = []


class SalesCustomerItem(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    company_name: Optional[str] = None
    role: str
    order_count: int = 0
    total_spent: int = 0
    last_order_date: Optional[datetime] = None
    pricing_tier_id: Optional[str] = None
    pricing_tier_name: Optional[str] = None

    class Config:
        from_attributes = True


class SalesOrderItem(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    hat_color: Optional[str] = None
    quantity: int
    unit_price: int  # cents
    customization: Optional[str] = None
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None
    visor_decoration: Optional[str] = None
    # Per-location logo paths
    front_logo_path: Optional[str] = None
    left_logo_path: Optional[str] = None
    right_logo_path: Optional[str] = None
    back_logo_path: Optional[str] = None
    visor_logo_path: Optional[str] = None
    # Per-location thread colors
    front_thread_colors: Optional[str] = None
    left_thread_colors: Optional[str] = None
    right_thread_colors: Optional[str] = None
    back_thread_colors: Optional[str] = None
    visor_thread_colors: Optional[str] = None
    decoration_notes: Optional[str] = None
    # Per-location decoration sizes
    front_decoration_size: Optional[str] = None
    left_decoration_size: Optional[str] = None
    right_decoration_size: Optional[str] = None
    back_decoration_size: Optional[str] = None
    visor_decoration_size: Optional[str] = None
    # Production details
    item_production_type: Optional[str] = None  # blank, domestic, overseas
    # Overseas extras
    design_addons: Optional[list] = None  # list of strings or dicts with name/details/artwork
    overseas_accessories: Optional[list[str]] = None
    overseas_shipping_method: Optional[str] = None
    # Domestic extras
    rush_speed: Optional[str] = None
    include_rope: Optional[bool] = None
    # Reference photo
    reference_photo_path: Optional[str] = None
    art_id: Optional[str] = None


class SalesOrderCreate(BaseModel):
    customer_id: str
    shipping_address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    shipping_method: Optional[str] = None
    carrier: Optional[str] = None
    in_hand_date: Optional[str] = None  # ISO date string e.g. "2026-04-15"
    internal_notes: Optional[str] = None
    items: list[SalesOrderItem]
    # New: discount, cross-links, status
    discount_amount: Optional[int] = 0
    source_quote_id: Optional[str] = None
    source_sample_request_id: Optional[str] = None
    linked_design_request_id: Optional[str] = None
    status: Optional[str] = "confirmed"  # "draft" or "confirmed"


class SalesOrderResponse(BaseModel):
    id: str
    order_number: str
    customer_name: str
    customer_email: str
    status: str
    payment_status: str
    total: int
    created_at: datetime

    class Config:
        from_attributes = True


class SalesCustomerCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    customer_type: str  # "customer", "wholesale", "golf"
    # Wholesale fields
    tax_id: Optional[str] = None
    business_type: Optional[str] = None
    annual_volume: Optional[str] = None
    # Golf fields
    course_name: Optional[str] = None
    course_location: Optional[str] = None
    proshop_contact: Optional[str] = None


class QuoteLineItemData(BaseModel):
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    description: str = ""
    hat_color: Optional[str] = None
    quantity: int = 1
    unit_price: int = 0  # cents
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None
    visor_decoration: Optional[str] = None
    # Per-location logo paths
    front_logo_path: Optional[str] = None
    left_logo_path: Optional[str] = None
    right_logo_path: Optional[str] = None
    back_logo_path: Optional[str] = None
    visor_logo_path: Optional[str] = None
    # Per-location thread colors
    front_thread_colors: Optional[str] = None
    left_thread_colors: Optional[str] = None
    right_thread_colors: Optional[str] = None
    back_thread_colors: Optional[str] = None
    visor_thread_colors: Optional[str] = None
    decoration_notes: Optional[str] = None
    # Per-location decoration sizes
    front_decoration_size: Optional[str] = None
    left_decoration_size: Optional[str] = None
    right_decoration_size: Optional[str] = None
    back_decoration_size: Optional[str] = None
    visor_decoration_size: Optional[str] = None
    # Production details
    production_type: Optional[str] = None  # blank, domestic, overseas
    # Overseas extras
    design_addons: Optional[list] = None  # list of strings or dicts with name/details/artwork
    overseas_accessories: Optional[list[str]] = None
    overseas_shipping_method: Optional[str] = None
    # Domestic extras
    rush_speed: Optional[str] = None
    include_rope: Optional[bool] = None
    # Reference photo
    reference_photo_path: Optional[str] = None
    art_id: Optional[str] = None
    notes: Optional[str] = None


class QuoteCreate(BaseModel):
    customer_id: str
    items: Optional[str] = None  # Legacy JSON string (backward compat)
    line_items: Optional[list[QuoteLineItemData]] = None  # New structured line items
    notes: Optional[str] = None
    valid_until: Optional[datetime | date] = None
    subtotal: int = 0
    discount_amount: int = 0
    shipping_estimate: int = 0
    linked_sample_request_id: Optional[str] = None
    linked_design_request_id: Optional[str] = None


class QuoteUpdate(BaseModel):
    items: Optional[str] = None
    line_items: Optional[list[QuoteLineItemData]] = None
    notes: Optional[str] = None
    valid_until: Optional[datetime | date] = None
    subtotal: Optional[int] = None
    discount_amount: Optional[int] = None
    shipping_estimate: Optional[int] = None
    status: Optional[str] = None
    linked_sample_request_id: Optional[str] = None
    linked_design_request_id: Optional[str] = None


class QuoteLineItemResponse(BaseModel):
    id: str
    line_number: int
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    description: str
    hat_color: Optional[str] = None
    quantity: int
    unit_price: int
    total_price: int
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None
    visor_decoration: Optional[str] = None
    # Per-location logo paths
    front_logo_path: Optional[str] = None
    left_logo_path: Optional[str] = None
    right_logo_path: Optional[str] = None
    back_logo_path: Optional[str] = None
    visor_logo_path: Optional[str] = None
    # Per-location thread colors
    front_thread_colors: Optional[str] = None
    left_thread_colors: Optional[str] = None
    right_thread_colors: Optional[str] = None
    back_thread_colors: Optional[str] = None
    visor_thread_colors: Optional[str] = None
    # Per-location decoration sizes
    front_decoration_size: Optional[str] = None
    left_decoration_size: Optional[str] = None
    right_decoration_size: Optional[str] = None
    back_decoration_size: Optional[str] = None
    visor_decoration_size: Optional[str] = None
    decoration_notes: Optional[str] = None
    # Production details
    production_type: Optional[str] = None
    design_addons: Optional[str] = None  # JSON string
    overseas_accessories: Optional[str] = None  # JSON string
    overseas_shipping_method: Optional[str] = None
    rush_speed: Optional[str] = None
    include_rope: Optional[bool] = None
    reference_photo_path: Optional[str] = None
    art_id: Optional[str] = None
    notes: Optional[str] = None
    product_name: Optional[str] = None
    product_style: Optional[str] = None


class QuoteResponse(BaseModel):
    id: str
    quote_number: str
    customer_name: str
    customer_email: str
    status: str
    subtotal: int
    discount_amount: int
    shipping_estimate: int
    total: int
    notes: Optional[str] = None
    items: Optional[str] = None  # Legacy JSON
    line_items: list[QuoteLineItemResponse] = []
    valid_until: Optional[datetime] = None
    linked_sample_request_id: Optional[str] = None
    linked_design_request_id: Optional[str] = None
    linked_sample_request_number: Optional[str] = None
    linked_design_request_number: Optional[str] = None
    converted_order_id: Optional[str] = None
    converted_order_number: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_order_number(db: Session) -> str:
    year = datetime.utcnow().year
    last_order = (
        db.query(Order)
        .filter(Order.order_number.like(f"KC-{year}-%"))
        .order_by(Order.created_at.desc())
        .first()
    )
    if last_order:
        last_num = int(last_order.order_number.split("-")[-1])
        return f"KC-{year}-{last_num + 1:05d}"
    return f"KC-{year}-00001"


def _build_quote_response(quote: Quote, customer: StoreUser, db: Session) -> QuoteResponse:
    """Build a QuoteResponse with structured line items and cross-links."""
    line_items_resp = []
    for li in (quote.line_items or []):
        line_items_resp.append(QuoteLineItemResponse(
            id=li.id,
            line_number=li.line_number,
            product_id=li.product_id,
            variant_id=li.variant_id,
            description=li.description,
            hat_color=li.hat_color,
            quantity=li.quantity,
            unit_price=li.unit_price,
            total_price=li.total_price,
            front_decoration=li.front_decoration,
            left_decoration=li.left_decoration,
            right_decoration=li.right_decoration,
            back_decoration=li.back_decoration,
            visor_decoration=li.visor_decoration,
            front_logo_path=li.front_logo_path,
            left_logo_path=li.left_logo_path,
            right_logo_path=li.right_logo_path,
            back_logo_path=li.back_logo_path,
            visor_logo_path=li.visor_logo_path,
            front_thread_colors=li.front_thread_colors,
            left_thread_colors=li.left_thread_colors,
            right_thread_colors=li.right_thread_colors,
            back_thread_colors=li.back_thread_colors,
            visor_thread_colors=li.visor_thread_colors,
            front_decoration_size=li.front_decoration_size,
            left_decoration_size=li.left_decoration_size,
            right_decoration_size=li.right_decoration_size,
            back_decoration_size=li.back_decoration_size,
            visor_decoration_size=li.visor_decoration_size,
            decoration_notes=li.decoration_notes,
            production_type=li.production_type,
            design_addons=li.design_addons,
            overseas_accessories=li.overseas_accessories,
            overseas_shipping_method=li.overseas_shipping_method,
            rush_speed=li.rush_speed,
            include_rope=li.include_rope,
            reference_photo_path=li.reference_photo_path,
            art_id=li.art_id,
            notes=li.notes,
            product_name=li.product.name if li.product else None,
            product_style=li.product.style_number if li.product else None,
        ))

    # Cross-link summary data
    linked_sr_number = None
    if quote.linked_sample_request_id and quote.linked_sample_request:
        linked_sr_number = quote.linked_sample_request.sample_number
    linked_dr_number = None
    if quote.linked_design_request_id and quote.linked_design_request:
        linked_dr_number = quote.linked_design_request.request_number
    converted_order_number = None
    if quote.converted_order_id and quote.converted_order:
        converted_order_number = quote.converted_order.order_number

    return QuoteResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        customer_name=f"{customer.first_name} {customer.last_name}".strip() or customer.email,
        customer_email=customer.email,
        status=quote.status,
        subtotal=quote.subtotal,
        discount_amount=quote.discount_amount,
        shipping_estimate=quote.shipping_estimate,
        total=quote.total,
        notes=quote.notes,
        items=quote.items,
        line_items=line_items_resp,
        valid_until=quote.valid_until,
        linked_sample_request_id=quote.linked_sample_request_id,
        linked_design_request_id=quote.linked_design_request_id,
        linked_sample_request_number=linked_sr_number,
        linked_design_request_number=linked_dr_number,
        converted_order_id=quote.converted_order_id,
        converted_order_number=converted_order_number,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
    )


def _create_quote_line_items(db: Session, quote_id: str, items_data: list[QuoteLineItemData]):
    """Create QuoteLineItem records from request data."""
    for idx, item in enumerate(items_data, start=1):
        li = QuoteLineItem(
            quote_id=quote_id,
            line_number=idx,
            product_id=item.product_id,
            variant_id=item.variant_id,
            description=item.description,
            hat_color=item.hat_color,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.unit_price * item.quantity,
            front_decoration=item.front_decoration,
            left_decoration=item.left_decoration,
            right_decoration=item.right_decoration,
            back_decoration=item.back_decoration,
            visor_decoration=item.visor_decoration,
            front_logo_path=item.front_logo_path,
            left_logo_path=item.left_logo_path,
            right_logo_path=item.right_logo_path,
            back_logo_path=item.back_logo_path,
            visor_logo_path=item.visor_logo_path,
            front_thread_colors=item.front_thread_colors,
            left_thread_colors=item.left_thread_colors,
            right_thread_colors=item.right_thread_colors,
            back_thread_colors=item.back_thread_colors,
            visor_thread_colors=item.visor_thread_colors,
            decoration_notes=item.decoration_notes,
            front_decoration_size=item.front_decoration_size,
            left_decoration_size=item.left_decoration_size,
            right_decoration_size=item.right_decoration_size,
            back_decoration_size=item.back_decoration_size,
            visor_decoration_size=item.visor_decoration_size,
            production_type=item.production_type,
            design_addons=json.dumps(item.design_addons) if item.design_addons else None,
            overseas_accessories=json.dumps(item.overseas_accessories) if item.overseas_accessories else None,
            overseas_shipping_method=item.overseas_shipping_method,
            rush_speed=item.rush_speed,
            include_rope=item.include_rope,
            reference_photo_path=item.reference_photo_path,
            art_id=item.art_id,
            notes=item.notes,
        )
        db.add(li)


def _generate_quote_number(db: Session) -> str:
    year = datetime.utcnow().year
    last_quote = (
        db.query(Quote)
        .filter(Quote.quote_number.like(f"KCQ-{year}-%"))
        .order_by(Quote.created_at.desc())
        .first()
    )
    if last_quote:
        last_num = int(last_quote.quote_number.split("-")[-1])
        return f"KCQ-{year}-{last_num + 1:05d}"
    return f"KCQ-{year}-00001"


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=SalesDashboardResponse)
async def sales_dashboard(
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Salesperson dashboard stats."""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # My orders this month
    order_stats = (
        db.query(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .filter(
            Order.salesperson_id == user.id,
            Order.created_at >= thirty_days_ago,
            Order.status != "cancelled",
        )
        .first()
    )

    # My customers
    my_customers = (
        db.query(func.count(StoreUser.id))
        .filter(StoreUser.salesperson_id == user.id)
        .scalar()
    ) or 0

    # Open quotes
    open_quotes = (
        db.query(func.count(Quote.id))
        .filter(
            Quote.salesperson_id == user.id,
            Quote.status.in_(["draft", "sent", "viewed"]),
        )
        .scalar()
    ) or 0

    # Recent orders
    recent = (
        db.query(Order, StoreUser.first_name, StoreUser.last_name, StoreUser.email)
        .join(StoreUser, StoreUser.id == Order.store_user_id)
        .filter(Order.salesperson_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )

    return SalesDashboardResponse(
        my_orders=order_stats[0] or 0,
        my_revenue=order_stats[1] or 0,
        my_customers=my_customers,
        open_quotes=open_quotes,
        recent_orders=[
            {
                "id": o.id,
                "order_number": o.order_number,
                "customer_name": f"{fn} {ln}".strip() or email,
                "total": o.total,
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o, fn, ln, email in recent
        ],
    )


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@router.get("/customers", response_model=list[SalesCustomerItem])
async def list_my_customers(
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """List salesperson's assigned customers."""
    query = (
        db.query(
            StoreUser,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total), 0).label("total_spent"),
            func.max(Order.created_at).label("last_order_date"),
        )
        .outerjoin(Order, (Order.store_user_id == StoreUser.id) & (Order.status != "cancelled"))
        .group_by(StoreUser.id)
    )

    # Salespersons only see their assigned customers; admins see all
    if user.role == "salesperson":
        query = query.filter(StoreUser.salesperson_id == user.id)
    else:
        query = query.filter(StoreUser.role.in_(["customer", "wholesale", "golf"]))

    if role_filter and role_filter in ("customer", "wholesale", "golf"):
        query = query.filter(StoreUser.role == role_filter)

    if search:
        query = query.filter(
            StoreUser.email.ilike(f"%{search}%")
            | StoreUser.first_name.ilike(f"%{search}%")
            | StoreUser.last_name.ilike(f"%{search}%")
            | StoreUser.company_name.ilike(f"%{search}%")
        )

    rows = query.order_by(StoreUser.company_name, StoreUser.first_name).offset(offset).limit(limit).all()

    # Build a set of tier IDs we need to look up
    tier_ids = {u.pricing_tier_id for u, _, _, _ in rows if u.pricing_tier_id}
    tier_map = {}
    if tier_ids:
        tiers = db.query(PricingTier).filter(PricingTier.id.in_(tier_ids)).all()
        tier_map = {t.id: t.name for t in tiers}

    return [
        SalesCustomerItem(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            company_name=u.company_name,
            role=u.role,
            order_count=oc,
            total_spent=ts,
            last_order_date=lod,
            pricing_tier_id=u.pricing_tier_id,
            pricing_tier_name=tier_map.get(u.pricing_tier_id) if u.pricing_tier_id else None,
        )
        for u, oc, ts, lod in rows
    ]


@router.get("/customers/{customer_id}")
async def get_customer_detail(
    customer_id: str,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Get customer detail for salesperson view."""
    customer = db.query(StoreUser).filter(StoreUser.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Verify assignment (admin can see any)
    if user.role == "salesperson" and customer.salesperson_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assigned customer")

    orders = (
        db.query(Order)
        .filter(Order.store_user_id == customer_id)
        .order_by(Order.created_at.desc())
        .limit(20)
        .all()
    )

    addresses = (
        db.query(Address)
        .filter(Address.store_user_id == customer_id)
        .order_by(Address.is_default.desc())
        .all()
    )

    return {
        "id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
        "company_name": customer.company_name,
        "role": customer.role,
        "pricing_tier_id": customer.pricing_tier_id,
        "tax_id": customer.tax_id,
        "business_type": customer.business_type,
        "annual_volume": customer.annual_volume,
        "course_name": customer.course_name,
        "course_location": customer.course_location,
        "proshop_contact": customer.proshop_contact,
        "orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "status": o.status,
                "total": o.total,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "addresses": [
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
                "zip": a.postal_code,
                "postal_code": a.postal_code,
                "country": a.country,
                "phone": a.phone,
                "is_default": a.is_default,
            }
            for a in addresses
        ],
    }


@router.post("/customers", status_code=201)
async def create_customer(
    data: SalesCustomerCreate,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Create a new customer profile. Auto-assigns the creating salesperson."""
    # Validate customer type
    if data.customer_type not in ("customer", "wholesale", "golf"):
        raise HTTPException(status_code=400, detail="customer_type must be 'customer', 'wholesale', or 'golf'")

    # Check duplicate email
    existing = db.query(StoreUser).filter(StoreUser.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="A customer with this email already exists")

    # Generate temporary password
    temp_password = secrets.token_urlsafe(12)

    # Find matching pricing tier
    tier_type_map = {"customer": "dtc", "wholesale": "wholesale", "golf": "golf"}
    pricing_tier = db.query(PricingTier).filter(
        PricingTier.tier_type == tier_type_map[data.customer_type]
    ).first()

    now = datetime.utcnow()

    new_customer = StoreUser(
        email=data.email.lower(),
        password_hash=hash_password(temp_password),
        name=f"{data.first_name} {data.last_name}",
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        company_name=data.company_name,
        role=data.customer_type,
        status="active",
        salesperson_id=user.id,
        pricing_tier_id=pricing_tier.id if pricing_tier else None,
        # For wholesale/golf: auto-approve
        application_status="approved" if data.customer_type in ("wholesale", "golf") else None,
        approved_by=user.id if data.customer_type in ("wholesale", "golf") else None,
        approved_at=now if data.customer_type in ("wholesale", "golf") else None,
        # Wholesale fields
        tax_id=data.tax_id,
        business_type=data.business_type,
        annual_volume=data.annual_volume,
        # Golf fields
        course_name=data.course_name,
        course_location=data.course_location,
        proshop_contact=data.proshop_contact,
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    # Send welcome email with temporary password
    try:
        send_customer_account_created(
            to_email=new_customer.email,
            first_name=new_customer.first_name,
            temp_password=temp_password,
            created_by=f"{user.first_name} {user.last_name}",
        )
    except Exception:
        pass  # Don't fail the request if email fails

    return {
        "id": new_customer.id,
        "email": new_customer.email,
        "first_name": new_customer.first_name,
        "last_name": new_customer.last_name,
        "role": new_customer.role,
        "company_name": new_customer.company_name,
        "message": "Customer created successfully",
    }


# ---------------------------------------------------------------------------
# Customer Addresses (sales)
# ---------------------------------------------------------------------------

class SalesAddressCreate(BaseModel):
    label: Optional[str] = None
    first_name: str
    last_name: str
    company: Optional[str] = None
    line1: str
    line2: Optional[str] = None
    city: str
    state: str
    zip: str
    country: str = "US"
    phone: Optional[str] = None
    is_default: bool = False


@router.post("/customers/{customer_id}/addresses", status_code=201)
async def create_customer_address(
    customer_id: str,
    data: SalesAddressCreate,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Create a new address on a customer's profile (salesperson action)."""
    customer = db.query(StoreUser).filter(StoreUser.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # If this is set as default, unset other defaults
    if data.is_default:
        db.query(Address).filter(
            Address.store_user_id == customer_id,
            Address.is_default == True,
        ).update({"is_default": False})

    address = Address(
        store_user_id=customer_id,
        label=data.label,
        first_name=data.first_name,
        last_name=data.last_name,
        company=data.company,
        line1=data.line1,
        line2=data.line2,
        city=data.city,
        state=data.state,
        postal_code=data.zip,
        country=data.country,
        phone=data.phone,
        is_default=data.is_default,
    )
    db.add(address)
    db.commit()
    db.refresh(address)

    return {
        "id": address.id,
        "label": address.label,
        "first_name": address.first_name,
        "last_name": address.last_name,
        "company": address.company,
        "line1": address.line1,
        "line2": address.line2,
        "city": address.city,
        "state": address.state,
        "zip": address.postal_code,
        "postal_code": address.postal_code,
        "country": address.country,
        "phone": address.phone,
        "is_default": address.is_default,
    }


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@router.get("/orders", response_model=list[SalesOrderResponse])
async def list_my_orders(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """List salesperson's orders."""
    query = (
        db.query(Order, StoreUser.first_name, StoreUser.last_name, StoreUser.email)
        .join(StoreUser, StoreUser.id == Order.store_user_id)
        .filter(Order.salesperson_id == user.id)
    )

    if status_filter:
        query = query.filter(Order.status == status_filter)

    if search:
        term = f"%{search}%"
        query = query.filter(
            (Order.order_number.ilike(term))
            | (StoreUser.first_name.ilike(term))
            | (StoreUser.last_name.ilike(term))
            | (StoreUser.email.ilike(term))
            | (StoreUser.company_name.ilike(term))
        )

    rows = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    return [
        SalesOrderResponse(
            id=o.id,
            order_number=o.order_number,
            customer_name=f"{fn} {ln}".strip() or email,
            customer_email=email,
            status=o.status,
            payment_status=o.payment_status,
            total=o.total,
            created_at=o.created_at,
        )
        for o, fn, ln, email in rows
    ]


@router.get("/shipping-options")
async def get_shipping_options(
    user=Depends(require_store_role("salesperson", "admin")),
):
    """Return available order-level shipping carriers and methods."""
    return {
        "carriers": [
            "UPS",
            "FedEx",
            "USPS",
            "DHL",
            "Freight",
            "Customer Account",
            "Other",
        ],
        "methods": [
            "Ground",
            "3-Day Select",
            "2nd Day Air",
            "Next Day Air",
            "Priority Mail",
            "Priority Mail Express",
            "Freight / LTL",
            "Customer Pickup",
            "Other",
        ],
    }


@router.post("/orders", response_model=SalesOrderResponse, status_code=201)
async def create_order_for_customer(
    data: SalesOrderCreate,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Create an order on behalf of a customer."""
    # Verify customer exists
    customer = db.query(StoreUser).filter(StoreUser.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if not data.items:
        raise HTTPException(status_code=400, detail="Order must have at least one item")

    # Calculate totals
    subtotal = sum(item.unit_price * item.quantity for item in data.items)
    discount = data.discount_amount or 0
    total = max(subtotal - discount, 0)

    # Validate status
    order_status = data.status if data.status in ("draft", "confirmed") else "confirmed"

    order = Order(
        order_number=_generate_order_number(db),
        store_user_id=data.customer_id,
        salesperson_id=user.id,
        status=order_status,
        payment_status="unpaid",
        subtotal=subtotal,
        shipping_cost=0,
        tax_amount=0,
        discount_amount=discount,
        total=total,
        shipping_address_id=data.shipping_address_id,
        billing_address_id=data.billing_address_id,
        shipping_method=data.shipping_method,
        carrier=data.carrier,
        in_hand_date=datetime.fromisoformat(data.in_hand_date) if data.in_hand_date else None,
        internal_notes=data.internal_notes,
        source_quote_id=data.source_quote_id,
        source_sample_request_id=data.source_sample_request_id,
        linked_design_request_id=data.linked_design_request_id,
    )
    db.add(order)
    db.flush()

    # Create order items
    for item in data.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            hat_color=item.hat_color,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.unit_price * item.quantity,
            customization=item.customization,
            front_decoration=item.front_decoration,
            left_decoration=item.left_decoration,
            right_decoration=item.right_decoration,
            back_decoration=item.back_decoration,
            visor_decoration=item.visor_decoration,
            front_logo_path=item.front_logo_path,
            left_logo_path=item.left_logo_path,
            right_logo_path=item.right_logo_path,
            back_logo_path=item.back_logo_path,
            visor_logo_path=item.visor_logo_path,
            front_thread_colors=item.front_thread_colors,
            left_thread_colors=item.left_thread_colors,
            right_thread_colors=item.right_thread_colors,
            back_thread_colors=item.back_thread_colors,
            visor_thread_colors=item.visor_thread_colors,
            decoration_notes=item.decoration_notes,
            front_decoration_size=item.front_decoration_size,
            left_decoration_size=item.left_decoration_size,
            right_decoration_size=item.right_decoration_size,
            back_decoration_size=item.back_decoration_size,
            visor_decoration_size=item.visor_decoration_size,
            item_production_type=item.item_production_type,
            design_addons=json.dumps(item.design_addons) if item.design_addons else None,
            overseas_accessories=json.dumps(item.overseas_accessories) if item.overseas_accessories else None,
            overseas_shipping_method=item.overseas_shipping_method,
            rush_speed=item.rush_speed,
            include_rope=item.include_rope,
            reference_photo_path=item.reference_photo_path,
            art_id=item.art_id,
        )
        db.add(order_item)

    # Status history
    history = OrderStatusHistory(
        order_id=order.id,
        status=order_status,
        note=f"Order created by salesperson {user.first_name} {user.last_name}",
        changed_by=user.id,
    )
    db.add(history)

    db.commit()
    db.refresh(order)

    return SalesOrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer_name=f"{customer.first_name} {customer.last_name}".strip() or customer.email,
        customer_email=customer.email,
        status=order.status,
        payment_status=order.payment_status,
        total=order.total,
        created_at=order.created_at,
    )


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------

@router.get("/quotes", response_model=list[QuoteResponse])
async def list_my_quotes(
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """List salesperson's quotes."""
    query = (
        db.query(Quote)
        .join(StoreUser, StoreUser.id == Quote.store_user_id)
        .filter(Quote.salesperson_id == user.id)
    )

    if status_filter:
        query = query.filter(Quote.status == status_filter)

    if search:
        term = f"%{search}%"
        query = query.filter(
            (Quote.quote_number.ilike(term))
            | (StoreUser.first_name.ilike(term))
            | (StoreUser.last_name.ilike(term))
            | (StoreUser.email.ilike(term))
            | (StoreUser.company_name.ilike(term))
        )

    quotes = query.order_by(Quote.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for q in quotes:
        customer = db.query(StoreUser).filter(StoreUser.id == q.store_user_id).first()
        results.append(_build_quote_response(q, customer, db))
    return results


@router.post("/quotes", response_model=QuoteResponse, status_code=201)
async def create_quote(
    data: QuoteCreate,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Create a quote for a customer."""
    customer = db.query(StoreUser).filter(StoreUser.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    total = data.subtotal - data.discount_amount + data.shipping_estimate

    # Normalize date to datetime for SQLAlchemy DateTime column
    valid_until = data.valid_until
    if isinstance(valid_until, date) and not isinstance(valid_until, datetime):
        valid_until = datetime(valid_until.year, valid_until.month, valid_until.day, 23, 59, 59)

    quote = Quote(
        quote_number=_generate_quote_number(db),
        store_user_id=data.customer_id,
        salesperson_id=user.id,
        status="draft",
        items=data.items,  # Legacy field
        notes=data.notes,
        valid_until=valid_until,
        subtotal=data.subtotal,
        discount_amount=data.discount_amount,
        shipping_estimate=data.shipping_estimate,
        total=total,
        linked_sample_request_id=data.linked_sample_request_id,
        linked_design_request_id=data.linked_design_request_id,
    )
    db.add(quote)
    db.flush()

    # Create structured line items if provided
    if data.line_items:
        _create_quote_line_items(db, quote.id, data.line_items)

    db.commit()
    db.refresh(quote)

    return _build_quote_response(quote, customer, db)


@router.put("/quotes/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str,
    data: QuoteUpdate,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Update a quote."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    if user.role == "salesperson" and quote.salesperson_id != user.id:
        raise HTTPException(status_code=403, detail="Not your quote")

    # Update scalar fields (exclude line_items which needs special handling)
    update_data = data.model_dump(exclude_unset=True, exclude={"line_items"})
    for key, value in update_data.items():
        # Normalize date to datetime for valid_until
        if key == "valid_until" and isinstance(value, date) and not isinstance(value, datetime):
            value = datetime(value.year, value.month, value.day, 23, 59, 59)
        setattr(quote, key, value)

    # Replace structured line items if provided
    if data.line_items is not None:
        # Delete existing line items
        db.query(QuoteLineItem).filter(QuoteLineItem.quote_id == quote.id).delete()
        _create_quote_line_items(db, quote.id, data.line_items)

    # Recalculate total
    quote.total = quote.subtotal - quote.discount_amount + quote.shipping_estimate

    db.commit()
    db.refresh(quote)

    customer = db.query(StoreUser).filter(StoreUser.id == quote.store_user_id).first()
    return _build_quote_response(quote, customer, db)


@router.post("/quotes/{quote_id}/send")
async def send_quote(
    quote_id: str,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Send quote email to customer and mark as sent."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    customer = db.query(StoreUser).filter(StoreUser.id == quote.store_user_id).first()
    if not customer:
        raise HTTPException(status_code=400, detail="Customer not found for this quote")

    quote.status = "sent"
    db.commit()

    # Build accept URL pointing to customer portal
    from ..config import get_settings
    settings = get_settings()
    accept_url = f"{settings.store_frontend_url}/portal/quotes/{quote.id}"

    valid_until_str = ""
    if quote.valid_until:
        valid_until_str = quote.valid_until.strftime("%B %d, %Y")
    else:
        valid_until_str = "No expiration"

    send_quote_to_customer(
        to_email=customer.email,
        first_name=customer.first_name or "there",
        quote_number=quote.quote_number,
        total_cents=quote.total,
        valid_until=valid_until_str,
        accept_url=accept_url,
    )

    return {"message": f"Quote sent to {customer.email}"}


@router.post("/quotes/{quote_id}/convert")
async def convert_quote_to_order(
    quote_id: str,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Convert a quote into an order with proper line items."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote.converted_order_id:
        raise HTTPException(status_code=400, detail="Quote already converted")

    order = Order(
        order_number=_generate_order_number(db),
        store_user_id=quote.store_user_id,
        salesperson_id=user.id,
        status="confirmed",
        payment_status="unpaid",
        subtotal=quote.subtotal,
        shipping_cost=quote.shipping_estimate,
        tax_amount=0,
        discount_amount=quote.discount_amount,
        total=quote.total,
        internal_notes=f"Converted from quote {quote.quote_number}",
        source_quote_id=quote.id,
        order_type="quote_conversion",
    )
    db.add(order)
    db.flush()

    # Create OrderItems from structured QuoteLineItems
    quote_line_items = (
        db.query(QuoteLineItem)
        .filter(QuoteLineItem.quote_id == quote.id)
        .order_by(QuoteLineItem.line_number)
        .all()
    )

    if quote_line_items:
        # Use structured line items
        for qli in quote_line_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=qli.product_id or "",
                variant_id=qli.variant_id,
                quantity=qli.quantity,
                unit_price=qli.unit_price,
                total_price=qli.total_price,
                front_decoration=qli.front_decoration,
                left_decoration=qli.left_decoration,
                right_decoration=qli.right_decoration,
                back_decoration=qli.back_decoration,
                visor_decoration=qli.visor_decoration,
                art_id=qli.art_id,
            )
            db.add(order_item)
    elif quote.items:
        # Fall back to legacy JSON items
        import json
        try:
            legacy_items = json.loads(quote.items)
            if isinstance(legacy_items, list):
                for item in legacy_items:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item.get("product_id", ""),
                        variant_id=item.get("variant_id"),
                        quantity=item.get("quantity", 1),
                        unit_price=item.get("unit_price", 0),
                        total_price=item.get("unit_price", 0) * item.get("quantity", 1),
                        customization=json.dumps(item) if item.get("customization") else None,
                    )
                    db.add(order_item)
        except (json.JSONDecodeError, TypeError):
            pass  # Legacy data couldn't be parsed; order created without items

    # Status history
    history = OrderStatusHistory(
        order_id=order.id,
        status="confirmed",
        note=f"Converted from quote {quote.quote_number}",
        changed_by=user.id,
    )
    db.add(history)

    # Mark quote as converted
    quote.status = "converted"
    quote.converted_order_id = order.id

    db.commit()
    db.refresh(order)

    return {
        "message": "Quote converted to order",
        "order_id": order.id,
        "order_number": order.order_number,
    }


@router.post("/quotes/{quote_id}/undo-convert")
async def undo_quote_conversion(
    quote_id: str,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Undo a quote-to-order conversion. Deletes the order and restores the quote."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote.status != "converted" or not quote.converted_order_id:
        raise HTTPException(status_code=400, detail="Quote has not been converted")

    # Check that the order hasn't progressed past editable statuses
    order = db.query(Order).filter(Order.id == quote.converted_order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Linked order not found")

    if order.status not in ("pending", "confirmed", "pending_approval", "revision_needed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot undo — order is already in '{order.status}' status",
        )

    # Delete order items, status history, then the order
    db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
    db.query(OrderStatusHistory).filter(OrderStatusHistory.order_id == order.id).delete()
    db.delete(order)

    # Restore quote
    quote.status = "accepted"
    quote.converted_order_id = None

    db.commit()

    return {"message": f"Conversion undone. Quote {quote.quote_number} restored."}


# ---------------------------------------------------------------------------
# Sales Order Detail
# ---------------------------------------------------------------------------

@router.get("/orders/{order_id}")
async def get_sales_order_detail(
    order_id: str,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Get full order detail for salesperson view."""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.status_history),
            joinedload(Order.mockup_approvals),
            joinedload(Order.attachments),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.role == "salesperson" and order.salesperson_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    customer = db.query(StoreUser).filter(StoreUser.id == order.store_user_id).first()

    # Build items
    items = []
    for item in (order.items or []):
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "variant_id": item.variant_id,
            "hat_color": item.hat_color,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total_price": item.total_price,
            "customization": item.customization,
            "front_decoration": item.front_decoration,
            "left_decoration": item.left_decoration,
            "right_decoration": item.right_decoration,
            "back_decoration": item.back_decoration,
            "visor_decoration": item.visor_decoration,
            "front_logo_path": item.front_logo_path,
            "left_logo_path": item.left_logo_path,
            "right_logo_path": item.right_logo_path,
            "back_logo_path": item.back_logo_path,
            "visor_logo_path": item.visor_logo_path,
            "front_thread_colors": item.front_thread_colors,
            "left_thread_colors": item.left_thread_colors,
            "right_thread_colors": item.right_thread_colors,
            "back_thread_colors": item.back_thread_colors,
            "visor_thread_colors": item.visor_thread_colors,
            "front_decoration_size": item.front_decoration_size,
            "left_decoration_size": item.left_decoration_size,
            "right_decoration_size": item.right_decoration_size,
            "back_decoration_size": item.back_decoration_size,
            "visor_decoration_size": item.visor_decoration_size,
            "decoration_notes": item.decoration_notes,
            "item_production_type": item.item_production_type,
            "design_addons": json.loads(item.design_addons) if item.design_addons else None,
            "overseas_accessories": json.loads(item.overseas_accessories) if item.overseas_accessories else None,
            "overseas_shipping_method": item.overseas_shipping_method,
            "rush_speed": item.rush_speed,
            "include_rope": item.include_rope,
            "reference_photo_path": item.reference_photo_path,
            "art_id": item.art_id,
            "design_request_id": item.design_request_id,
            "product_name": item.product.name if item.product else None,
            "product_style": item.product.style_number if item.product else None,
        })

    # Split mockup approvals by type
    mockups = []
    sew_outs = []
    for ma in (order.mockup_approvals or []):
        entry = {
            "id": ma.id,
            "mockup_image_url": ma.mockup_image_url,
            "version": ma.version,
            "status": ma.status,
            "customer_notes": ma.customer_notes,
            "admin_notes": ma.admin_notes,
            "responded_at": ma.responded_at.isoformat() if ma.responded_at else None,
            "created_at": ma.created_at.isoformat() if ma.created_at else None,
        }
        if getattr(ma, 'approval_type', 'mockup') == "sew_out":
            sew_outs.append(entry)
        else:
            mockups.append(entry)

    # Status history
    history = [
        {
            "status": h.status,
            "note": h.note,
            "changed_by": h.changed_by,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in (order.status_history or [])
    ]

    # Source links
    source_quote = None
    if order.source_quote_id:
        sq = db.query(Quote).filter(Quote.id == order.source_quote_id).first()
        if sq:
            source_quote = {"id": sq.id, "quote_number": sq.quote_number, "status": sq.status}

    source_sample = None
    if order.source_sample_request_id:
        from ..models.sample_request import SampleRequest
        ss = db.query(SampleRequest).filter(SampleRequest.id == order.source_sample_request_id).first()
        if ss:
            source_sample = {"id": ss.id, "sample_number": ss.sample_number, "status": ss.status}

    linked_design = None
    if order.linked_design_request_id:
        from ..models.mockup import DesignRequest
        dr = db.query(DesignRequest).filter(DesignRequest.id == order.linked_design_request_id).first()
        if dr:
            linked_design = {"id": dr.id, "design_number": getattr(dr, 'design_number', None), "status": dr.status}

    return {
        "id": order.id,
        "order_number": order.order_number,
        "order_type": getattr(order, 'order_type', 'standard'),
        "status": order.status,
        "payment_status": order.payment_status,
        "customer": {
            "id": customer.id,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email,
            "company_name": customer.company_name,
        } if customer else None,
        "salesperson_id": order.salesperson_id,
        "subtotal": order.subtotal,
        "shipping_cost": order.shipping_cost,
        "tax_amount": order.tax_amount,
        "discount_amount": order.discount_amount,
        "total": order.total,
        "shipping_method": order.shipping_method,
        "carrier": order.carrier,
        "in_hand_date": order.in_hand_date.isoformat() if order.in_hand_date else None,
        "tracking_number": order.tracking_number,
        "tracking_url": order.tracking_url,
        "production_type": order.production_type,
        "estimated_ship_date": order.estimated_ship_date.isoformat() if order.estimated_ship_date else None,
        "actual_ship_date": order.actual_ship_date.isoformat() if order.actual_ship_date else None,
        "customer_notes": order.customer_notes,
        "internal_notes": order.internal_notes,
        "items": items,
        "mockup_approvals": mockups,
        "sew_out_approvals": sew_outs,
        "status_history": history,
        "source_quote": source_quote,
        "source_quote_id": order.source_quote_id,
        "source_sample_request": source_sample,
        "source_sample_request_id": order.source_sample_request_id,
        "linked_design_request": linked_design,
        "linked_design_request_id": order.linked_design_request_id,
        "bc_sales_order_id": order.bc_sales_order_id,
        "bc_sync_status": order.bc_sync_status,
        "attachments": [
            {
                "id": att.id,
                "file_path": att.file_path,
                "file_name": att.file_name,
                "file_type": att.file_type,
                "notes": att.notes,
                "uploaded_by_id": att.uploaded_by_id,
                "created_at": att.created_at.isoformat() if att.created_at else None,
            }
            for att in (order.attachments or [])
        ],
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Pricing Lookup
# ---------------------------------------------------------------------------


@router.get("/pricing/lookup")
async def pricing_lookup(
    customer_id: str = Query(...),
    product_id: str = Query(...),
    quantity: int = Query(..., ge=1),
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Look up the unit price for a product based on customer tier and quantity."""
    from ..models.store_pricing import PricingRule

    customer = db.query(StoreUser).filter(StoreUser.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    tier = None
    tier_name = "None"
    if customer.pricing_tier_id:
        tier = db.query(PricingTier).filter(PricingTier.id == customer.pricing_tier_id).first()
        if tier:
            tier_name = tier.name

    # Pricing fallback chain:
    # 1) Product-specific rule for this tier + quantity range
    # 2) Tier-level rule (no product) for this quantity range
    # 3) Tier discount_pct applied to product base_price
    # 4) Product base_price
    if tier:
        # 1) Product-specific rule
        product_rule = (
            db.query(PricingRule)
            .filter(
                PricingRule.pricing_tier_id == tier.id,
                PricingRule.product_id == product_id,
                PricingRule.min_qty <= quantity,
            )
            .filter(
                (PricingRule.max_qty >= quantity) | (PricingRule.max_qty.is_(None))
            )
            .order_by(PricingRule.min_qty.desc())
            .first()
        )
        if product_rule:
            return {
                "unit_price": product_rule.price_per_unit,
                "source": "tier_rule",
                "tier_name": tier_name,
                "description": f"{tier_name} — Volume break ({product_rule.min_qty}{'–' + str(product_rule.max_qty) if product_rule.max_qty else '+'} units)",
            }

        # 2) Tier-level rule (no product scope)
        tier_rule = (
            db.query(PricingRule)
            .filter(
                PricingRule.pricing_tier_id == tier.id,
                PricingRule.product_id.is_(None),
                PricingRule.min_qty <= quantity,
            )
            .filter(
                (PricingRule.max_qty >= quantity) | (PricingRule.max_qty.is_(None))
            )
            .order_by(PricingRule.min_qty.desc())
            .first()
        )
        if tier_rule:
            return {
                "unit_price": tier_rule.price_per_unit,
                "source": "tier_rule",
                "tier_name": tier_name,
                "description": f"{tier_name} — Volume break ({tier_rule.min_qty}{'–' + str(tier_rule.max_qty) if tier_rule.max_qty else '+'} units)",
            }

        # 3) Tier discount percentage
        if tier.discount_pct and tier.discount_pct > 0:
            discounted = int(product.base_price * (1 - tier.discount_pct / 100))
            return {
                "unit_price": discounted,
                "source": "tier_discount",
                "tier_name": tier_name,
                "description": f"{tier_name} — {tier.discount_pct}% discount",
            }

    # 4) Fallback: product base price
    return {
        "unit_price": product.base_price,
        "source": "base_price",
        "tier_name": tier_name,
        "description": "Base price",
    }


@router.get("/products/search")
async def search_products(
    q: str = Query("", min_length=0),
    limit: int = Query(20, le=50),
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Search products for use in quotes and orders."""
    query = db.query(Product).filter(Product.is_active == True)

    if q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            (Product.name.ilike(search_term))
            | (Product.style_number.ilike(search_term))
            | (Product.sku.ilike(search_term))
        )

    products = query.order_by(Product.name).limit(limit).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "style_number": p.style_number,
            "sku": p.sku,
            "base_price": p.base_price,
        }
        for p in products
    ]


# Editable statuses for orders
EDITABLE_ORDER_STATUSES = ("draft", "pending", "confirmed", "pending_approval", "revision_needed")


class OrderEditPayload(BaseModel):
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    shipping_method: Optional[str] = None
    carrier: Optional[str] = None
    in_hand_date: Optional[str] = None
    shipping_address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    discount_amount: Optional[int] = None
    source_quote_id: Optional[str] = None
    source_sample_request_id: Optional[str] = None
    linked_design_request_id: Optional[str] = None
    items: Optional[list[SalesOrderItem]] = None
    status: Optional[str] = None  # allow promoting draft → confirmed


@router.put("/orders/{order_id}")
async def update_sales_order(
    order_id: str,
    data: OrderEditPayload,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Update order fields. Only allowed for editable statuses."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.role == "salesperson" and order.salesperson_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status not in EDITABLE_ORDER_STATUSES:
        raise HTTPException(status_code=400, detail=f"Cannot edit order in '{order.status}' status")

    update_data = data.model_dump(exclude_unset=True)

    # Convert in_hand_date string to datetime
    if "in_hand_date" in update_data:
        ihd = update_data["in_hand_date"]
        update_data["in_hand_date"] = datetime.fromisoformat(ihd) if ihd else None

    # Handle line item replacement
    items_data = update_data.pop("items", None)
    if items_data is not None:
        # Delete existing items
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
        # Recreate
        for item_raw in items_data:
            item = SalesOrderItem(**item_raw)
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                hat_color=item.hat_color,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.unit_price * item.quantity,
                customization=item.customization,
                front_decoration=item.front_decoration,
                left_decoration=item.left_decoration,
                right_decoration=item.right_decoration,
                back_decoration=item.back_decoration,
                visor_decoration=item.visor_decoration,
                front_logo_path=item.front_logo_path,
                left_logo_path=item.left_logo_path,
                right_logo_path=item.right_logo_path,
                back_logo_path=item.back_logo_path,
                visor_logo_path=item.visor_logo_path,
                front_thread_colors=item.front_thread_colors,
                left_thread_colors=item.left_thread_colors,
                right_thread_colors=item.right_thread_colors,
                back_thread_colors=item.back_thread_colors,
                visor_thread_colors=item.visor_thread_colors,
                decoration_notes=item.decoration_notes,
                front_decoration_size=item.front_decoration_size,
                left_decoration_size=item.left_decoration_size,
                right_decoration_size=item.right_decoration_size,
                back_decoration_size=item.back_decoration_size,
                visor_decoration_size=item.visor_decoration_size,
                item_production_type=item.item_production_type,
                design_addons=json.dumps(item.design_addons) if item.design_addons else None,
                overseas_accessories=json.dumps(item.overseas_accessories) if item.overseas_accessories else None,
                overseas_shipping_method=item.overseas_shipping_method,
                rush_speed=item.rush_speed,
                include_rope=item.include_rope,
                reference_photo_path=item.reference_photo_path,
                art_id=item.art_id,
            )
            db.add(order_item)
        # Recalculate totals
        subtotal = sum(SalesOrderItem(**i).unit_price * SalesOrderItem(**i).quantity for i in items_data)
        order.subtotal = subtotal
        discount = update_data.get("discount_amount", order.discount_amount) or 0
        order.total = max(subtotal - discount, 0)

    # Handle status change
    new_status = update_data.pop("status", None)
    if new_status and new_status in ("draft", "confirmed"):
        if order.status != new_status:
            order.status = new_status
            db.add(OrderStatusHistory(
                order_id=order.id,
                status=new_status,
                note=f"Status changed to {new_status} by {user.first_name} {user.last_name}",
                changed_by=user.id,
            ))

    # Apply remaining scalar fields
    for key, value in update_data.items():
        setattr(order, key, value)

    # Recalculate total if discount changed but items didn't
    if "discount_amount" in update_data and items_data is None:
        order.total = max(order.subtotal - (order.discount_amount or 0), 0)

    db.commit()
    db.refresh(order)
    return {"message": "Order updated successfully"}


@router.post("/orders/{order_id}/attachments")
async def add_order_attachment(
    order_id: str,
    file: UploadFile = File(...),
    file_type: str = Form("other"),
    notes: Optional[str] = Form(None),
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Upload a file attachment to an order."""
    from ..models.order_attachment import OrderAttachment
    from ..services.storage_service import save_upload_file

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.role == "salesperson" and order.salesperson_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if file_type not in ("dst", "production_art", "logo", "reference", "other"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    try:
        saved_path, mime_type, file_size = await save_upload_file(
            file=file,
            subdir="order_attachments",
            max_size_mb=50,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    attachment = OrderAttachment(
        order_id=order.id,
        file_path=saved_path,
        file_name=file.filename or "unknown",
        file_type=file_type,
        uploaded_by_id=user.id,
        notes=notes,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return {
        "id": attachment.id,
        "file_path": attachment.file_path,
        "file_name": attachment.file_name,
        "file_type": attachment.file_type,
        "notes": attachment.notes,
        "created_at": attachment.created_at.isoformat() if attachment.created_at else None,
    }


@router.delete("/orders/{order_id}/attachments/{attachment_id}")
async def delete_order_attachment(
    order_id: str,
    attachment_id: str,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Delete an attachment from an order."""
    from ..models.order_attachment import OrderAttachment

    attachment = (
        db.query(OrderAttachment)
        .filter(OrderAttachment.id == attachment_id, OrderAttachment.order_id == order_id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    db.delete(attachment)
    db.commit()

    return {"message": "Attachment deleted"}


# ---------------------------------------------------------------------------
# Approval Workflow
# ---------------------------------------------------------------------------


class ApprovalRejectPayload(BaseModel):
    notes: Optional[str] = None


@router.post("/orders/{order_id}/submit-for-approval")
async def submit_order_for_approval(
    order_id: str,
    user=Depends(require_store_role("salesperson", "admin")),
    db: Session = Depends(get_db),
):
    """Salesperson submits an order for purchasing manager approval."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.role == "salesperson" and order.salesperson_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status not in ("pending", "revision_needed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit for approval from '{order.status}' status. Must be 'pending' or 'revision_needed'.",
        )

    order.status = "pending_approval"
    history = OrderStatusHistory(
        order_id=order.id,
        status="pending_approval",
        note="Submitted for purchasing manager approval",
        changed_by=f"{user.first_name} {user.last_name}",
    )
    db.add(history)
    db.commit()

    return {"message": "Order submitted for approval", "status": "pending_approval"}


@router.post("/orders/{order_id}/approve")
async def approve_order(
    order_id: str,
    user=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Purchasing manager approves an order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve order in '{order.status}' status. Must be 'pending_approval'.",
        )

    order.status = "confirmed"
    history = OrderStatusHistory(
        order_id=order.id,
        status="confirmed",
        note="Approved by purchasing manager",
        changed_by=f"{user.first_name} {user.last_name}",
    )
    db.add(history)
    db.commit()

    return {"message": "Order approved", "status": "confirmed"}


@router.post("/orders/{order_id}/reject")
async def reject_order(
    order_id: str,
    data: ApprovalRejectPayload,
    user=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Purchasing manager rejects an order with notes."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject order in '{order.status}' status. Must be 'pending_approval'.",
        )

    order.status = "revision_needed"
    note = "Revision requested by purchasing manager"
    if data.notes:
        note += f": {data.notes}"
    history = OrderStatusHistory(
        order_id=order.id,
        status="revision_needed",
        note=note,
        changed_by=f"{user.first_name} {user.last_name}",
    )
    db.add(history)
    db.commit()

    return {"message": "Order sent back for revision", "status": "revision_needed"}


# ---------------------------------------------------------------------------
# Pending Approvals List (for admin dashboard)
# ---------------------------------------------------------------------------


@router.get("/approvals/pending")
async def list_pending_approvals(
    user=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """List all orders and samples pending approval."""
    pending_orders = (
        db.query(Order)
        .filter(Order.status == "pending_approval")
        .order_by(Order.created_at.desc())
        .all()
    )

    result_orders = []
    for o in pending_orders:
        salesperson = db.query(StoreUser).filter(StoreUser.id == o.salesperson_id).first() if o.salesperson_id else None
        customer = db.query(StoreUser).filter(StoreUser.id == o.store_user_id).first()
        result_orders.append({
            "id": o.id,
            "order_number": o.order_number,
            "order_type": getattr(o, 'order_type', 'standard'),
            "customer_name": f"{customer.first_name} {customer.last_name}" if customer else "Unknown",
            "customer_company": customer.company_name if customer else None,
            "total": o.total,
            "salesperson_name": f"{salesperson.first_name} {salesperson.last_name}" if salesperson else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })

    return {"orders": result_orders}


# ---------------------------------------------------------------------------
# Generic Logo Upload
# ---------------------------------------------------------------------------

@router.post("/upload-logo")
async def upload_item_logo(
    file: UploadFile = File(...),
    location: str = Query("front"),
    entity_type: str = Query("general"),
    user=Depends(require_store_role("salesperson", "admin")),
):
    """Generic logo/DST upload for any item configuration form."""
    from ..services.storage_service import save_upload_file

    valid_locations = ("front", "left", "right", "back", "visor", "reference")
    if location not in valid_locations and not location.startswith("addon_"):
        raise HTTPException(status_code=400, detail=f"Invalid location. Must be one of: {', '.join(valid_locations)} or addon_<name>")

    try:
        saved_path, mime_type, file_size = await save_upload_file(
            file=file,
            subdir=f"item_logos/{entity_type}",
            max_size_mb=25,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "logo_path": saved_path,
        "filename": file.filename or "unknown",
        "location": location,
    }
