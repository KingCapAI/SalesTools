"""Sample request routes: versioned, multi-line-item, audited sample system."""

import os
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..models.sample_request import (
    SampleRequest, SampleLineItem, SampleVersion, SamplePhoto, SampleActivity,
)
from ..models.store_product import Product, ProductVariant
from ..models.store_user import StoreUser
from ..models.address import Address
from ..models.design_request import DesignRequest
from ..models.store_quote import Quote
from ..utils.store_dependencies import require_store_role, get_current_store_user

router = APIRouter(tags=["Sample Requests"])

# Storage imports
from ..services.storage_service import save_file_bytes, generate_unique_filename


# ---------------------------------------------------------------------------
# Status workflow
# ---------------------------------------------------------------------------

VALID_STATUSES = (
    "draft", "submitted", "under_review", "approved", "in_production",
    "sample_complete", "customer_review", "changes_requested",
    "customer_approved", "converting", "production_ordered", "rejected",
)

# Maps current status → allowed next statuses
STATUS_TRANSITIONS = {
    "draft": ("submitted",),
    "submitted": ("under_review", "rejected"),
    "under_review": ("approved", "rejected"),
    "approved": ("in_production",),
    "in_production": ("sample_complete",),
    "sample_complete": ("customer_review",),
    "customer_review": ("customer_approved", "changes_requested"),
    "changes_requested": ("in_production",),
    "customer_approved": ("converting",),
    "converting": ("production_ordered",),
    "production_ordered": (),
    "rejected": (),
}

# Statuses that allow rejection from any state
REJECTABLE_STATUSES = (
    "submitted", "under_review", "approved", "in_production",
    "sample_complete", "customer_review", "changes_requested",
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LineItemCreate(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    hat_color: Optional[str] = None
    sample_type: str = "blank"
    quantity: int = 1
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None
    visor_decoration: Optional[str] = None
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
    art_id: Optional[str] = None
    # Production details
    production_type: Optional[str] = None  # blank, domestic, overseas
    # Overseas extras
    design_addons: Optional[list] = None  # list of strings or dicts
    overseas_accessories: Optional[list[str]] = None
    overseas_shipping_method: Optional[str] = None
    # Domestic extras
    rush_speed: Optional[str] = None
    include_rope: Optional[bool] = None
    # Reference photo
    reference_photo_path: Optional[str] = None


class LineItemUpdate(BaseModel):
    product_id: Optional[str] = None
    variant_id: Optional[str] = None
    hat_color: Optional[str] = None
    sample_type: Optional[str] = None
    quantity: Optional[int] = None
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None
    visor_decoration: Optional[str] = None
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
    art_id: Optional[str] = None
    art_version: Optional[int] = None
    # Production details
    production_type: Optional[str] = None
    design_addons: Optional[list] = None
    overseas_accessories: Optional[list[str]] = None
    overseas_shipping_method: Optional[str] = None
    rush_speed: Optional[str] = None
    include_rope: Optional[bool] = None
    reference_photo_path: Optional[str] = None


class SampleCreateRequest(BaseModel):
    customer_id: str
    notes: Optional[str] = None
    shipping_address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    shipping_account_number: Optional[str] = None
    shipping_account_company: Optional[str] = None
    shipping_account_zip: Optional[str] = None
    line_items: List[LineItemCreate]
    submit: bool = False  # True = submit immediately, False = save as draft
    linked_design_request_id: Optional[str] = None
    linked_quote_id: Optional[str] = None
    discount_amount: Optional[int] = 0


class SampleUpdateRequest(BaseModel):
    notes: Optional[str] = None
    shipping_address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    shipping_account_number: Optional[str] = None
    shipping_account_company: Optional[str] = None
    shipping_account_zip: Optional[str] = None
    discount_amount: Optional[int] = None
    line_items: Optional[List[LineItemCreate]] = None
    linked_design_request_id: Optional[str] = None
    linked_quote_id: Optional[str] = None
    submit: Optional[bool] = None  # True = submit after save


class AdminStatusUpdate(BaseModel):
    status: str
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    internal_notes: Optional[str] = None
    factory_reference_number: Optional[str] = None


class AdminAssignRequest(BaseModel):
    assignee_id: str


class VersionCreateRequest(BaseModel):
    change_summary: Optional[str] = None


class LineResponseItem(BaseModel):
    line_item_id: str
    status: str  # approved / rejected / revision_requested
    feedback: Optional[str] = None


class CustomerResponseRequest(BaseModel):
    response: str  # approved / changes_requested
    feedback_text: Optional[str] = None
    line_responses: Optional[List[LineResponseItem]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_sample_number(db: Session) -> str:
    """Generate next sample number: KCS-{YEAR}-{SEQ:05d}"""
    year = datetime.utcnow().year
    prefix = f"KCS-{year}-"
    last = (
        db.query(SampleRequest)
        .filter(SampleRequest.sample_number.like(f"{prefix}%"))
        .order_by(desc(SampleRequest.sample_number))
        .first()
    )
    if last:
        seq = int(last.sample_number.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


def _calculate_sample_charge(db: Session, line_items: list, customer_id: str) -> int:
    """Calculate sample charge based on production type.

    Wholesale pricing:
    - Blanks: first 2 free, additional at wholesale tier price (looked up per product)
    - Domestic: $50 per sample (5000 cents)
    - Overseas: $200 first (20000 cents), $50 each additional (5000 cents)

    Returns charge in cents.
    """
    from ..models.store_pricing import PricingRule

    blank_items = [li for li in line_items if getattr(li, 'sample_type', 'blank') == 'blank' or getattr(li, 'production_type', None) == 'blank']
    domestic_items = [li for li in line_items if getattr(li, 'sample_type', '') == 'domestic_custom' or getattr(li, 'production_type', None) == 'domestic']
    overseas_items = [li for li in line_items if getattr(li, 'sample_type', '') == 'overseas_custom' or getattr(li, 'production_type', None) == 'overseas']

    charge = 0

    # Blanks: first 2 free, additional at wholesale tier price
    blank_count = sum(li.quantity for li in blank_items)
    if blank_count > 2:
        additional = blank_count - 2
        # Look up wholesale price for each product
        for li in blank_items:
            rule = (
                db.query(PricingRule)
                .filter(
                    PricingRule.product_id == li.product_id,
                    PricingRule.is_active == True,
                )
                .order_by(PricingRule.min_quantity.asc())
                .first()
            )
            if rule:
                charge += rule.unit_price * min(li.quantity, additional)
                additional -= min(li.quantity, additional)
                if additional <= 0:
                    break
            else:
                # Fallback: $10 per blank if no pricing rule found
                charge += 1000 * min(li.quantity, additional)
                additional -= min(li.quantity, additional)
                if additional <= 0:
                    break

    # Domestic: $50 each
    domestic_count = sum(li.quantity for li in domestic_items)
    charge += domestic_count * 5000

    # Overseas: $200 first, $50 each additional
    overseas_count = sum(li.quantity for li in overseas_items)
    if overseas_count > 0:
        charge += 20000  # first
        if overseas_count > 1:
            charge += (overseas_count - 1) * 5000  # additional

    return charge


def _log_activity(db: Session, sample_id: str, user_id: Optional[str], action: str, description: str, details: Optional[dict] = None):
    """Create an audit log entry."""
    activity = SampleActivity(
        sample_request_id=sample_id,
        user_id=user_id,
        action=action,
        description=description,
        details=json.dumps(details) if details else None,
    )
    db.add(activity)


def _user_name(user: Optional[StoreUser]) -> Optional[str]:
    if not user:
        return None
    return f"{user.first_name} {user.last_name}".strip() or user.email


def _build_line_item_response(li: SampleLineItem, db: Session) -> dict:
    product = db.query(Product).filter(Product.id == li.product_id).first()
    return {
        "id": li.id,
        "line_number": li.line_number,
        "product_id": li.product_id,
        "product_name": product.name if product else None,
        "style_number": product.style_number if product else None,
        "variant_id": li.variant_id,
        "hat_color": li.hat_color,
        "sample_type": li.sample_type,
        "quantity": li.quantity,
        "front_decoration": li.front_decoration,
        "left_decoration": li.left_decoration,
        "right_decoration": li.right_decoration,
        "back_decoration": li.back_decoration,
        "visor_decoration": li.visor_decoration,
        "front_logo_path": li.front_logo_path,
        "left_logo_path": li.left_logo_path,
        "right_logo_path": li.right_logo_path,
        "back_logo_path": li.back_logo_path,
        "visor_logo_path": li.visor_logo_path,
        "front_thread_colors": li.front_thread_colors,
        "left_thread_colors": li.left_thread_colors,
        "right_thread_colors": li.right_thread_colors,
        "back_thread_colors": li.back_thread_colors,
        "visor_thread_colors": li.visor_thread_colors,
        "front_decoration_size": li.front_decoration_size,
        "left_decoration_size": li.left_decoration_size,
        "right_decoration_size": li.right_decoration_size,
        "back_decoration_size": li.back_decoration_size,
        "visor_decoration_size": li.visor_decoration_size,
        "decoration_notes": li.decoration_notes,
        "production_type": li.production_type,
        "design_addons": json.loads(li.design_addons) if li.design_addons else None,
        "overseas_accessories": json.loads(li.overseas_accessories) if li.overseas_accessories else None,
        "overseas_shipping_method": li.overseas_shipping_method,
        "reference_photo_path": li.reference_photo_path,
        "art_id": li.art_id,
        "art_version": li.art_version,
        "line_status": li.line_status,
        "customer_feedback": li.customer_feedback,
        "created_at": li.created_at.isoformat() if li.created_at else None,
        "updated_at": li.updated_at.isoformat() if li.updated_at else None,
    }


def _build_version_response(v: SampleVersion, db: Session) -> dict:
    created_by = db.query(StoreUser).filter(StoreUser.id == v.created_by_id).first() if v.created_by_id else None
    responded_by = db.query(StoreUser).filter(StoreUser.id == v.responded_by_id).first() if v.responded_by_id else None
    photos = db.query(SamplePhoto).filter(SamplePhoto.sample_version_id == v.id).all()
    return {
        "id": v.id,
        "version_number": v.version_number,
        "created_by_id": v.created_by_id,
        "created_by_name": _user_name(created_by),
        "change_summary": v.change_summary,
        "customer_response": v.customer_response,
        "customer_feedback": v.customer_feedback,
        "responded_at": v.responded_at.isoformat() if v.responded_at else None,
        "responded_by_id": v.responded_by_id,
        "responded_by_name": _user_name(responded_by),
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "photos": [
            {
                "id": p.id,
                "photo_path": p.photo_path,
                "caption": p.caption,
                "sample_line_item_id": p.sample_line_item_id,
                "uploaded_by_id": p.uploaded_by_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in photos
        ],
    }


def _build_activity_response(a: SampleActivity, db: Session) -> dict:
    user = db.query(StoreUser).filter(StoreUser.id == a.user_id).first() if a.user_id else None
    return {
        "id": a.id,
        "user_id": a.user_id,
        "user_name": _user_name(user),
        "action": a.action,
        "description": a.description,
        "details": json.loads(a.details) if a.details else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _build_sample_response(sr: SampleRequest, db: Session, include_children: bool = True) -> dict:
    """Build full sample response with nested line items, versions, and activity."""
    requester = db.query(StoreUser).filter(StoreUser.id == sr.requested_by_id).first()
    customer = db.query(StoreUser).filter(StoreUser.id == sr.customer_id).first() if sr.customer_id else None
    assignee = db.query(StoreUser).filter(StoreUser.id == sr.purchasing_assignee_id).first() if sr.purchasing_assignee_id else None

    # Build address info
    shipping_addr = None
    if sr.shipping_address_id:
        addr = db.query(Address).filter(Address.id == sr.shipping_address_id).first()
        if addr:
            shipping_addr = {
                "id": addr.id, "label": addr.label, "line1": addr.line1,
                "line2": addr.line2, "city": addr.city, "state": addr.state,
                "postal_code": addr.postal_code, "country": addr.country,
            }
    billing_addr = None
    if sr.billing_address_id:
        addr = db.query(Address).filter(Address.id == sr.billing_address_id).first()
        if addr:
            billing_addr = {
                "id": addr.id, "label": addr.label, "line1": addr.line1,
                "line2": addr.line2, "city": addr.city, "state": addr.state,
                "postal_code": addr.postal_code, "country": addr.country,
            }

    result = {
        "id": sr.id,
        "sample_number": sr.sample_number,
        "requested_by_id": sr.requested_by_id,
        "requested_by_name": _user_name(requester),
        "customer_id": sr.customer_id,
        "customer_name": _user_name(customer),
        "status": sr.status,
        "current_version": sr.current_version,
        "factory_reference_number": sr.factory_reference_number,
        "bc_sales_order_number": sr.bc_sales_order_number,
        "bc_purchase_order_number": sr.bc_purchase_order_number,
        "purchasing_assignee_id": sr.purchasing_assignee_id,
        "purchasing_assignee_name": _user_name(assignee),
        "shipping_address": shipping_addr,
        "billing_address": billing_addr,
        "shipping_account_number": sr.shipping_account_number,
        "shipping_account_company": sr.shipping_account_company,
        "shipping_account_zip": sr.shipping_account_zip,
        "tracking_number": sr.tracking_number,
        "tracking_url": sr.tracking_url,
        "charge_amount": sr.charge_amount,
        "discount_amount": sr.discount_amount,
        "notes": sr.notes,
        "internal_notes": sr.internal_notes,
        "created_at": sr.created_at.isoformat() if sr.created_at else None,
        "updated_at": sr.updated_at.isoformat() if sr.updated_at else None,
    }

    if include_children:
        line_items = (
            db.query(SampleLineItem)
            .filter(SampleLineItem.sample_request_id == sr.id)
            .order_by(SampleLineItem.line_number)
            .all()
        )
        versions = (
            db.query(SampleVersion)
            .filter(SampleVersion.sample_request_id == sr.id)
            .order_by(SampleVersion.version_number)
            .all()
        )
        activities = (
            db.query(SampleActivity)
            .filter(SampleActivity.sample_request_id == sr.id)
            .order_by(SampleActivity.created_at.desc())
            .all()
        )
        result["line_items"] = [_build_line_item_response(li, db) for li in line_items]
        result["versions"] = [_build_version_response(v, db) for v in versions]
        result["activities"] = [_build_activity_response(a, db) for a in activities]
        result["line_item_count"] = len(line_items)

        # Linked design requests
        linked_designs = (
            db.query(DesignRequest)
            .filter(DesignRequest.linked_sample_request_id == sr.id)
            .order_by(DesignRequest.created_at.desc())
            .all()
        )
        result["linked_design_requests"] = [
            {
                "id": dr.id,
                "request_number": dr.request_number,
                "title": dr.title,
                "status": dr.status,
                "design_type": dr.design_type,
                "art_id": dr.art_id,
                "created_at": dr.created_at.isoformat() if dr.created_at else None,
            }
            for dr in linked_designs
        ]
    else:
        # For list endpoints, just include count
        result["line_item_count"] = (
            db.query(func.count(SampleLineItem.id))
            .filter(SampleLineItem.sample_request_id == sr.id)
            .scalar() or 0
        )

    return result


def _build_sample_list_item(sr: SampleRequest, db: Session) -> dict:
    """Lightweight response for list endpoints."""
    requester = db.query(StoreUser).filter(StoreUser.id == sr.requested_by_id).first()
    customer = db.query(StoreUser).filter(StoreUser.id == sr.customer_id).first() if sr.customer_id else None
    line_count = (
        db.query(func.count(SampleLineItem.id))
        .filter(SampleLineItem.sample_request_id == sr.id)
        .scalar() or 0
    )
    return {
        "id": sr.id,
        "sample_number": sr.sample_number,
        "status": sr.status,
        "current_version": sr.current_version,
        "line_item_count": line_count,
        "factory_reference_number": sr.factory_reference_number,
        "customer_id": sr.customer_id,
        "customer_name": _user_name(customer),
        "requested_by_id": sr.requested_by_id,
        "requested_by_name": _user_name(requester),
        "charge_amount": sr.charge_amount,
        "created_at": sr.created_at.isoformat() if sr.created_at else None,
    }


def _validate_status_transition(current: str, target: str):
    """Validate that a status transition is allowed."""
    if target == "rejected" and current in REJECTABLE_STATUSES:
        return
    allowed = STATUS_TRANSITIONS.get(current, ())
    if target not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current}' to '{target}'. Allowed: {', '.join(allowed)}",
        )


# ---------------------------------------------------------------------------
# File upload endpoints
# ---------------------------------------------------------------------------

@router.post("/sales/samples/upload-logo")
async def upload_sample_logo(
    file: UploadFile = File(...),
    location: str = Query(..., description="Decoration location: front, left, right, back, visor"),
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
):
    """Upload a logo file for a sample request decoration location."""
    if location not in ("front", "left", "right", "back", "visor"):
        raise HTTPException(status_code=400, detail="Invalid location")

    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".svg", ".ai", ".eps", ".webp", ".pdf"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    unique_name = generate_unique_filename(f"upload{ext}")
    content = await file.read()
    relative_path = await save_file_bytes(content, "samples", unique_name, file.content_type or "application/octet-stream")

    return {
        "logo_path": relative_path,
        "filename": file.filename,
        "location": location,
    }


@router.post("/admin/samples/{sample_id}/upload-photo")
async def upload_sample_photo(
    sample_id: str,
    file: UploadFile = File(...),
    version_id: str = Query(...),
    line_item_id: Optional[str] = Query(None),
    caption: Optional[str] = Query(None),
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Upload a factory photo for a specific sample version."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    version = db.query(SampleVersion).filter(
        SampleVersion.id == version_id,
        SampleVersion.sample_request_id == sample_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".heic"):
        raise HTTPException(status_code=400, detail="Unsupported photo type")

    unique_name = generate_unique_filename(f"upload{ext}")
    content = await file.read()
    relative_path = await save_file_bytes(content, "sample_photos", unique_name, file.content_type or "image/png")

    photo = SamplePhoto(
        sample_version_id=version_id,
        sample_line_item_id=line_item_id,
        photo_path=relative_path,
        caption=caption,
        uploaded_by_id=admin.id,
    )
    db.add(photo)

    _log_activity(db, sample_id, admin.id, "photo_upload",
                  f"Photo uploaded for version {version.version_number}")
    db.commit()
    db.refresh(photo)

    return {
        "id": photo.id,
        "photo_path": photo.photo_path,
        "caption": photo.caption,
        "version_id": version_id,
        "line_item_id": line_item_id,
    }


# ---------------------------------------------------------------------------
# Salesperson endpoints
# ---------------------------------------------------------------------------

@router.get("/sales/samples")
async def list_sales_samples(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """List sample requests for the current salesperson."""
    query = db.query(SampleRequest).filter(SampleRequest.requested_by_id == user.id)

    if status:
        query = query.filter(SampleRequest.status == status)
    if customer_id:
        query = query.filter(SampleRequest.customer_id == customer_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            SampleRequest.sample_number.ilike(search_term)
            | SampleRequest.factory_reference_number.ilike(search_term)
        )

    samples = (
        query.order_by(SampleRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_build_sample_list_item(sr, db) for sr in samples]


@router.post("/sales/samples", status_code=201)
async def create_sales_sample(
    data: SampleCreateRequest,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Create a sample request with multiple line items."""
    # Validate customer
    customer = db.query(StoreUser).filter(StoreUser.id == data.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if user.role == "salesperson" and customer.salesperson_id != user.id:
        raise HTTPException(status_code=403, detail="Not your assigned customer")

    # Validate line items
    if not data.line_items:
        raise HTTPException(status_code=400, detail="At least one line item is required")

    valid_types = ("blank", "domestic_custom", "overseas_custom")
    total_qty = 0
    for li in data.line_items:
        product = db.query(Product).filter(Product.id == li.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {li.product_id}")
        if li.sample_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid sample_type: {li.sample_type}")
        total_qty += li.quantity

    # Generate number and calculate charge
    sample_number = _generate_sample_number(db)
    charge_amount = _calculate_sample_charge(db, data.line_items, data.customer_id)
    discount = data.discount_amount or 0

    initial_status = "submitted" if data.submit else "draft"

    sample = SampleRequest(
        sample_number=sample_number,
        requested_by_id=user.id,
        customer_id=data.customer_id,
        status=initial_status,
        current_version=1 if data.submit else 0,
        shipping_address_id=data.shipping_address_id,
        billing_address_id=data.billing_address_id,
        shipping_account_number=data.shipping_account_number,
        shipping_account_company=data.shipping_account_company,
        shipping_account_zip=data.shipping_account_zip,
        notes=data.notes,
        charge_amount=charge_amount,
        discount_amount=discount,
    )
    db.add(sample)
    db.flush()  # Get sample.id

    # Create line items
    for idx, li_data in enumerate(data.line_items, start=1):
        line_item = SampleLineItem(
            sample_request_id=sample.id,
            line_number=idx,
            product_id=li_data.product_id,
            variant_id=li_data.variant_id,
            hat_color=li_data.hat_color,
            sample_type=li_data.sample_type,
            quantity=li_data.quantity,
            front_decoration=li_data.front_decoration,
            left_decoration=li_data.left_decoration,
            right_decoration=li_data.right_decoration,
            back_decoration=li_data.back_decoration,
            visor_decoration=li_data.visor_decoration,
            front_logo_path=li_data.front_logo_path,
            left_logo_path=li_data.left_logo_path,
            right_logo_path=li_data.right_logo_path,
            back_logo_path=li_data.back_logo_path,
            visor_logo_path=li_data.visor_logo_path,
            front_thread_colors=li_data.front_thread_colors,
            left_thread_colors=li_data.left_thread_colors,
            right_thread_colors=li_data.right_thread_colors,
            back_thread_colors=li_data.back_thread_colors,
            visor_thread_colors=li_data.visor_thread_colors,
            front_decoration_size=li_data.front_decoration_size,
            left_decoration_size=li_data.left_decoration_size,
            right_decoration_size=li_data.right_decoration_size,
            back_decoration_size=li_data.back_decoration_size,
            visor_decoration_size=li_data.visor_decoration_size,
            decoration_notes=li_data.decoration_notes,
            art_id=li_data.art_id,
            production_type=li_data.production_type,
            design_addons=json.dumps(li_data.design_addons) if li_data.design_addons else None,
            overseas_accessories=json.dumps(li_data.overseas_accessories) if li_data.overseas_accessories else None,
            overseas_shipping_method=li_data.overseas_shipping_method,
            rush_speed=li_data.rush_speed,
            reference_photo_path=li_data.reference_photo_path,
        )
        db.add(line_item)

    # Create initial version if submitting
    if data.submit:
        version = SampleVersion(
            sample_request_id=sample.id,
            version_number=1,
            created_by_id=user.id,
            change_summary="Initial submission",
        )
        db.add(version)

    # Cross-link to design request if provided
    if data.linked_design_request_id:
        design_req = db.query(DesignRequest).filter(
            DesignRequest.id == data.linked_design_request_id
        ).first()
        if design_req:
            design_req.linked_sample_request_id = sample.id

    # Cross-link to quote if provided
    if data.linked_quote_id:
        quote = db.query(Quote).filter(Quote.id == data.linked_quote_id).first()
        if quote:
            quote.linked_sample_request_id = sample.id

    _log_activity(db, sample.id, user.id, "created",
                  f"Sample request {sample_number} created with {len(data.line_items)} item(s)")
    if data.submit:
        _log_activity(db, sample.id, user.id, "submitted",
                      f"Sample submitted for review")

    db.commit()
    db.refresh(sample)

    return _build_sample_response(sample, db)


@router.get("/sales/samples/{sample_id}")
async def get_sales_sample(
    sample_id: str,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Get full sample detail including line items, versions, and activity."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")

    return _build_sample_response(sample, db)


@router.put("/sales/samples/{sample_id}")
async def update_sales_sample(
    sample_id: str,
    data: SampleUpdateRequest,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Update a draft or submitted sample."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")
    if sample.status not in ("draft", "submitted"):
        raise HTTPException(status_code=400, detail="Can only edit draft or submitted samples")

    if data.notes is not None:
        sample.notes = data.notes
    if data.shipping_address_id is not None:
        sample.shipping_address_id = data.shipping_address_id
    if data.billing_address_id is not None:
        sample.billing_address_id = data.billing_address_id
    if data.shipping_account_number is not None:
        sample.shipping_account_number = data.shipping_account_number
    if data.shipping_account_company is not None:
        sample.shipping_account_company = data.shipping_account_company
    if data.shipping_account_zip is not None:
        sample.shipping_account_zip = data.shipping_account_zip
    if data.discount_amount is not None:
        sample.discount_amount = data.discount_amount

    # Replace line items if provided
    if data.line_items is not None:
        db.query(SampleLineItem).filter(SampleLineItem.sample_request_id == sample.id).delete()
        for idx, li_data in enumerate(data.line_items, start=1):
            line_item = SampleLineItem(
                sample_request_id=sample.id,
                line_number=idx,
                product_id=li_data.product_id,
                variant_id=li_data.variant_id,
                hat_color=li_data.hat_color,
                sample_type=li_data.sample_type,
                quantity=li_data.quantity,
                front_decoration=li_data.front_decoration,
                left_decoration=li_data.left_decoration,
                right_decoration=li_data.right_decoration,
                back_decoration=li_data.back_decoration,
                visor_decoration=li_data.visor_decoration,
                front_logo_path=li_data.front_logo_path,
                left_logo_path=li_data.left_logo_path,
                right_logo_path=li_data.right_logo_path,
                back_logo_path=li_data.back_logo_path,
                visor_logo_path=li_data.visor_logo_path,
                front_thread_colors=li_data.front_thread_colors,
                left_thread_colors=li_data.left_thread_colors,
                right_thread_colors=li_data.right_thread_colors,
                back_thread_colors=li_data.back_thread_colors,
                visor_thread_colors=li_data.visor_thread_colors,
                front_decoration_size=li_data.front_decoration_size,
                left_decoration_size=li_data.left_decoration_size,
                right_decoration_size=li_data.right_decoration_size,
                back_decoration_size=li_data.back_decoration_size,
                visor_decoration_size=li_data.visor_decoration_size,
                decoration_notes=li_data.decoration_notes,
                art_id=li_data.art_id,
                production_type=li_data.production_type,
                design_addons=json.dumps(li_data.design_addons) if li_data.design_addons else None,
                overseas_accessories=json.dumps(li_data.overseas_accessories) if li_data.overseas_accessories else None,
                overseas_shipping_method=li_data.overseas_shipping_method,
                rush_speed=li_data.rush_speed,
                reference_photo_path=li_data.reference_photo_path,
            )
            db.add(line_item)
        # Recalculate charge
        sample.charge_amount = _calculate_sample_charge(db, data.line_items, sample.customer_id)

    # Cross-links
    if data.linked_design_request_id is not None:
        design_req = db.query(DesignRequest).filter(
            DesignRequest.id == data.linked_design_request_id
        ).first()
        if design_req:
            design_req.linked_sample_request_id = sample.id

    if data.linked_quote_id is not None:
        quote = db.query(Quote).filter(Quote.id == data.linked_quote_id).first()
        if quote:
            quote.linked_sample_request_id = sample.id

    # Handle submit
    if data.submit:
        if sample.status == "draft":
            sample.status = "submitted"
            if sample.current_version == 0:
                sample.current_version = 1
                version = SampleVersion(
                    sample_request_id=sample.id,
                    version_number=1,
                    created_by_id=user.id,
                    change_summary="Initial submission",
                )
                db.add(version)
            _log_activity(db, sample.id, user.id, "submitted", "Sample submitted for purchasing review")

    _log_activity(db, sample.id, user.id, "updated", "Sample details updated")
    db.commit()
    db.refresh(sample)

    return _build_sample_response(sample, db)


@router.post("/sales/samples/{sample_id}/submit")
async def submit_sales_sample(
    sample_id: str,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Submit a draft sample for purchasing review."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")

    _validate_status_transition(sample.status, "submitted")

    # Ensure at least one line item
    li_count = db.query(func.count(SampleLineItem.id)).filter(
        SampleLineItem.sample_request_id == sample.id
    ).scalar()
    if not li_count:
        raise HTTPException(status_code=400, detail="Add at least one line item before submitting")

    sample.status = "submitted"
    if sample.current_version == 0:
        sample.current_version = 1
        version = SampleVersion(
            sample_request_id=sample.id,
            version_number=1,
            created_by_id=user.id,
            change_summary="Initial submission",
        )
        db.add(version)

    _log_activity(db, sample.id, user.id, "submitted", "Sample submitted for purchasing review")
    db.commit()
    db.refresh(sample)

    return _build_sample_response(sample, db)


# ---------------------------------------------------------------------------
# Line item CRUD (salesperson)
# ---------------------------------------------------------------------------

@router.post("/sales/samples/{sample_id}/line-items", status_code=201)
async def add_line_item(
    sample_id: str,
    data: LineItemCreate,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Add a line item to a draft or submitted sample."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")
    if sample.status not in ("draft", "submitted"):
        raise HTTPException(status_code=400, detail="Can only add items to draft or submitted samples")

    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    valid_types = ("blank", "domestic_custom", "overseas_custom")
    if data.sample_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid sample_type: {data.sample_type}")

    # Get next line number
    max_line = (
        db.query(func.max(SampleLineItem.line_number))
        .filter(SampleLineItem.sample_request_id == sample.id)
        .scalar() or 0
    )

    line_item = SampleLineItem(
        sample_request_id=sample.id,
        line_number=max_line + 1,
        product_id=data.product_id,
        variant_id=data.variant_id,
        hat_color=data.hat_color,
        sample_type=data.sample_type,
        quantity=data.quantity,
        front_decoration=data.front_decoration,
        left_decoration=data.left_decoration,
        right_decoration=data.right_decoration,
        back_decoration=data.back_decoration,
        visor_decoration=data.visor_decoration,
        front_logo_path=data.front_logo_path,
        left_logo_path=data.left_logo_path,
        right_logo_path=data.right_logo_path,
        back_logo_path=data.back_logo_path,
        visor_logo_path=data.visor_logo_path,
        decoration_notes=data.decoration_notes,
        art_id=data.art_id,
    )
    db.add(line_item)

    _log_activity(db, sample.id, user.id, "line_item_added",
                  f"Line item #{max_line + 1} added: {product.name}")
    db.commit()
    db.refresh(line_item)

    return _build_line_item_response(line_item, db)


@router.put("/sales/samples/{sample_id}/line-items/{line_item_id}")
async def update_line_item(
    sample_id: str,
    line_item_id: str,
    data: LineItemUpdate,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Update a line item on a draft or submitted sample."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")
    if sample.status not in ("draft", "submitted"):
        raise HTTPException(status_code=400, detail="Can only edit items on draft or submitted samples")

    li = db.query(SampleLineItem).filter(
        SampleLineItem.id == line_item_id,
        SampleLineItem.sample_request_id == sample_id,
    ).first()
    if not li:
        raise HTTPException(status_code=404, detail="Line item not found")

    update_fields = data.model_dump(exclude_unset=True)
    if "product_id" in update_fields:
        product = db.query(Product).filter(Product.id == update_fields["product_id"]).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

    for field, value in update_fields.items():
        setattr(li, field, value)

    _log_activity(db, sample.id, user.id, "line_item_updated",
                  f"Line item #{li.line_number} updated")
    db.commit()
    db.refresh(li)

    return _build_line_item_response(li, db)


@router.delete("/sales/samples/{sample_id}/line-items/{line_item_id}")
async def delete_line_item(
    sample_id: str,
    line_item_id: str,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Remove a line item from a draft or submitted sample."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")
    if sample.status not in ("draft", "submitted"):
        raise HTTPException(status_code=400, detail="Can only remove items from draft or submitted samples")

    li = db.query(SampleLineItem).filter(
        SampleLineItem.id == line_item_id,
        SampleLineItem.sample_request_id == sample_id,
    ).first()
    if not li:
        raise HTTPException(status_code=404, detail="Line item not found")

    line_num = li.line_number
    db.delete(li)

    _log_activity(db, sample.id, user.id, "line_item_removed",
                  f"Line item #{line_num} removed")
    db.commit()

    return {"detail": "Line item removed"}


# ---------------------------------------------------------------------------
# Salesperson: record customer response (on behalf)
# ---------------------------------------------------------------------------

@router.post("/sales/samples/{sample_id}/customer-response")
async def record_customer_response(
    sample_id: str,
    data: CustomerResponseRequest,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Record customer feedback (salesperson enters on behalf of customer)."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")
    if sample.status != "customer_review":
        raise HTTPException(status_code=400, detail="Sample must be in 'customer_review' status")

    if data.response not in ("approved", "changes_requested"):
        raise HTTPException(status_code=400, detail="Response must be 'approved' or 'changes_requested'")

    # Update current version with response
    current_ver = db.query(SampleVersion).filter(
        SampleVersion.sample_request_id == sample.id,
        SampleVersion.version_number == sample.current_version,
    ).first()
    if current_ver:
        current_ver.customer_response = data.response
        current_ver.customer_feedback = data.feedback_text
        current_ver.responded_at = datetime.utcnow()
        current_ver.responded_by_id = user.id

    # Update per-line-item statuses if provided
    if data.line_responses:
        for lr in data.line_responses:
            li = db.query(SampleLineItem).filter(
                SampleLineItem.id == lr.line_item_id,
                SampleLineItem.sample_request_id == sample.id,
            ).first()
            if li:
                li.line_status = lr.status
                li.customer_feedback = lr.feedback

    # Update sample status
    new_status = "customer_approved" if data.response == "approved" else "changes_requested"
    sample.status = new_status

    _log_activity(db, sample.id, user.id, "customer_response",
                  f"Customer response recorded: {data.response}",
                  {"feedback": data.feedback_text, "recorded_by": "salesperson"})
    db.commit()
    db.refresh(sample)

    return _build_sample_response(sample, db)


# ---------------------------------------------------------------------------
# Sample → Production Order conversion
# ---------------------------------------------------------------------------

@router.post("/sales/samples/{sample_id}/convert-to-order")
async def convert_sample_to_order(
    sample_id: str,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Convert an approved sample request into a production order."""
    from ..models.store_order import Order, OrderItem, OrderStatusHistory

    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    if user.role == "salesperson" and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample request")

    if sample.status not in ("customer_approved", "converting"):
        raise HTTPException(
            status_code=400,
            detail=f"Sample must be in 'customer_approved' or 'converting' status (currently '{sample.status}')",
        )

    # Generate order number
    year = datetime.utcnow().year
    last_order = (
        db.query(Order)
        .filter(Order.order_number.like(f"KC-{year}-%"))
        .order_by(Order.created_at.desc())
        .first()
    )
    if last_order:
        last_num = int(last_order.order_number.split("-")[-1])
        order_number = f"KC-{year}-{last_num + 1:05d}"
    else:
        order_number = f"KC-{year}-00001"

    # Create production order
    order = Order(
        order_number=order_number,
        store_user_id=sample.customer_id or sample.requested_by_id,
        salesperson_id=user.id,
        status="confirmed",
        payment_status="unpaid",
        subtotal=0,
        shipping_cost=0,
        tax_amount=0,
        discount_amount=0,
        total=0,
        order_type="sample_production",
        source_sample_request_id=sample.id,
        internal_notes=f"Production order from sample {sample.sample_number}",
    )
    db.add(order)
    db.flush()

    # Create OrderItems from SampleLineItems
    line_items = (
        db.query(SampleLineItem)
        .filter(SampleLineItem.sample_request_id == sample.id)
        .order_by(SampleLineItem.line_number)
        .all()
    )

    subtotal = 0
    for sli in line_items:
        # Skip rejected lines
        if sli.line_status == "rejected":
            continue

        order_item = OrderItem(
            order_id=order.id,
            product_id=sli.product_id,
            variant_id=sli.variant_id,
            quantity=sli.quantity,
            unit_price=0,  # To be filled by salesperson
            total_price=0,
            front_decoration=sli.front_decoration,
            left_decoration=sli.left_decoration,
            right_decoration=sli.right_decoration,
            back_decoration=sli.back_decoration,
            visor_decoration=sli.visor_decoration,
            art_id=sli.art_id,
        )
        db.add(order_item)

    # Status history
    history = OrderStatusHistory(
        order_id=order.id,
        status="confirmed",
        note=f"Production order created from sample {sample.sample_number}",
        changed_by=user.id,
    )
    db.add(history)

    # Update sample status
    sample.status = "production_ordered"

    _log_activity(db, sample.id, user.id, "converted_to_order",
                  f"Converted to production order {order_number}",
                  {"order_id": order.id, "order_number": order_number})

    db.commit()
    db.refresh(order)

    return {
        "message": f"Production order {order_number} created from sample {sample.sample_number}",
        "order_id": order.id,
        "order_number": order_number,
        "sample_number": sample.sample_number,
    }


@router.post("/sales/samples/{sample_id}/undo-convert")
async def undo_sample_conversion(
    sample_id: str,
    user=Depends(require_store_role("salesperson", "purchasing_manager", "admin")),
    db: Session = Depends(get_db),
):
    """Undo a sample-to-order conversion. Deletes the order and restores the sample."""
    from ..models.store_order import Order, OrderItem, OrderStatusHistory

    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    if sample.status != "production_ordered":
        raise HTTPException(status_code=400, detail="Sample has not been converted to an order")

    # Find the linked order
    order = (
        db.query(Order)
        .filter(Order.source_sample_request_id == sample.id)
        .first()
    )
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

    # Restore sample
    sample.status = "customer_approved"

    _log_activity(db, sample.id, user.id, "conversion_undone",
                  f"Production order conversion undone — sample restored to customer_approved")

    db.commit()

    return {"message": f"Conversion undone. Sample {sample.sample_number} restored."}


# ---------------------------------------------------------------------------
# Admin / Purchasing endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/samples")
async def admin_list_samples(
    status: Optional[str] = None,
    sample_type: Optional[str] = None,
    assignee_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """List all sample requests (admin only)."""
    query = db.query(SampleRequest)

    if status:
        query = query.filter(SampleRequest.status == status)
    if assignee_id:
        query = query.filter(SampleRequest.purchasing_assignee_id == assignee_id)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            SampleRequest.sample_number.ilike(search_term)
            | SampleRequest.factory_reference_number.ilike(search_term)
        )

    samples = (
        query.order_by(SampleRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_build_sample_list_item(sr, db) for sr in samples]


@router.get("/admin/samples/{sample_id}")
async def admin_get_sample(
    sample_id: str,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Get full sample detail (admin, includes internal_notes)."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    return _build_sample_response(sample, db)


@router.put("/admin/samples/{sample_id}/status")
async def admin_update_sample_status(
    sample_id: str,
    data: AdminStatusUpdate,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Update sample status with workflow validation."""
    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data.status}")

    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    old_status = sample.status
    _validate_status_transition(old_status, data.status)

    sample.status = data.status
    if data.tracking_number is not None:
        sample.tracking_number = data.tracking_number
    if data.tracking_url is not None:
        sample.tracking_url = data.tracking_url
    if data.internal_notes is not None:
        sample.internal_notes = data.internal_notes
    if data.factory_reference_number is not None:
        sample.factory_reference_number = data.factory_reference_number

    _log_activity(db, sample.id, admin.id, "status_change",
                  f"Status changed from '{old_status}' to '{data.status}'",
                  {"from": old_status, "to": data.status})
    db.commit()
    db.refresh(sample)

    return _build_sample_response(sample, db)


@router.put("/admin/samples/{sample_id}/assign")
async def admin_assign_sample(
    sample_id: str,
    data: AdminAssignRequest,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Assign a purchasing person to a sample."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    assignee = db.query(StoreUser).filter(StoreUser.id == data.assignee_id).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")

    sample.purchasing_assignee_id = data.assignee_id

    _log_activity(db, sample.id, admin.id, "assigned",
                  f"Assigned to {_user_name(assignee)}")
    db.commit()
    db.refresh(sample)

    return _build_sample_response(sample, db)


@router.post("/admin/samples/{sample_id}/versions", status_code=201)
async def admin_create_version(
    sample_id: str,
    data: VersionCreateRequest,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Create a new version (e.g., after factory produces revised sample)."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    new_version_num = sample.current_version + 1
    version = SampleVersion(
        sample_request_id=sample.id,
        version_number=new_version_num,
        created_by_id=admin.id,
        change_summary=data.change_summary,
    )
    db.add(version)

    sample.current_version = new_version_num

    _log_activity(db, sample.id, admin.id, "version_created",
                  f"Version {new_version_num} created",
                  {"change_summary": data.change_summary})
    db.commit()
    db.refresh(version)

    return _build_version_response(version, db)


@router.post("/admin/samples/{sample_id}/versions/{version_id}/photos", status_code=201)
async def admin_upload_version_photos(
    sample_id: str,
    version_id: str,
    file: UploadFile = File(...),
    line_item_id: Optional[str] = Query(None),
    caption: Optional[str] = Query(None),
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Upload factory photos for a specific version."""
    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    version = db.query(SampleVersion).filter(
        SampleVersion.id == version_id,
        SampleVersion.sample_request_id == sample_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".heic"):
        raise HTTPException(status_code=400, detail="Unsupported photo type")

    unique_name = generate_unique_filename(f"upload{ext}")
    content = await file.read()
    relative_path = await save_file_bytes(content, "sample_photos", unique_name, file.content_type or "image/png")

    photo = SamplePhoto(
        sample_version_id=version_id,
        sample_line_item_id=line_item_id,
        photo_path=relative_path,
        caption=caption,
        uploaded_by_id=admin.id,
    )
    db.add(photo)

    _log_activity(db, sample.id, admin.id, "photo_upload",
                  f"Photo uploaded for version {version.version_number}")
    db.commit()
    db.refresh(photo)

    return {
        "id": photo.id,
        "photo_path": photo.photo_path,
        "caption": photo.caption,
        "version_id": version_id,
        "line_item_id": line_item_id,
    }


# ---------------------------------------------------------------------------
# Customer portal endpoints
# ---------------------------------------------------------------------------

@router.get("/store/samples")
async def list_store_samples(
    user=Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """List sample requests for the current customer."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    samples = (
        db.query(SampleRequest)
        .filter(
            (SampleRequest.customer_id == user.id)
            | (SampleRequest.requested_by_id == user.id)
        )
        .order_by(SampleRequest.created_at.desc())
        .all()
    )

    return [_build_sample_list_item(sr, db) for sr in samples]


@router.get("/store/samples/{sample_id}")
async def get_store_sample(
    sample_id: str,
    user=Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Get sample detail for the customer (excludes internal_notes)."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    if sample.customer_id != user.id and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample")

    resp = _build_sample_response(sample, db)
    resp.pop("internal_notes", None)
    return resp


@router.post("/store/samples/{sample_id}/versions/{version_id}/respond")
async def customer_respond_to_version(
    sample_id: str,
    version_id: str,
    data: CustomerResponseRequest,
    user=Depends(get_current_store_user),
    db: Session = Depends(get_db),
):
    """Customer approves or requests changes on a version."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sample = db.query(SampleRequest).filter(SampleRequest.id == sample_id).first()
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")

    if sample.customer_id != user.id and sample.requested_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not your sample")

    if sample.status != "customer_review":
        raise HTTPException(status_code=400, detail="Sample is not awaiting your review")

    version = db.query(SampleVersion).filter(
        SampleVersion.id == version_id,
        SampleVersion.sample_request_id == sample_id,
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    if data.response not in ("approved", "changes_requested"):
        raise HTTPException(status_code=400, detail="Response must be 'approved' or 'changes_requested'")

    version.customer_response = data.response
    version.customer_feedback = data.feedback_text
    version.responded_at = datetime.utcnow()
    version.responded_by_id = user.id

    # Update per-line-item statuses
    if data.line_responses:
        for lr in data.line_responses:
            li = db.query(SampleLineItem).filter(
                SampleLineItem.id == lr.line_item_id,
                SampleLineItem.sample_request_id == sample.id,
            ).first()
            if li:
                li.line_status = lr.status
                li.customer_feedback = lr.feedback

    new_status = "customer_approved" if data.response == "approved" else "changes_requested"
    sample.status = new_status

    _log_activity(db, sample.id, user.id, "customer_response",
                  f"Customer responded: {data.response}",
                  {"feedback": data.feedback_text, "recorded_by": "customer"})
    db.commit()
    db.refresh(sample)

    resp = _build_sample_response(sample, db)
    resp.pop("internal_notes", None)
    return resp
