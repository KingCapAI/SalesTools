"""Purchasing Manager routes — order and sample approval workflow."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.store_order import Order, OrderItem, OrderStatusHistory
from ..models.store_user import StoreUser
from ..models.sample_request import SampleRequest, SampleActivity
from ..utils.store_dependencies import require_store_role
from ..services.email_service import (
    send_order_approved,
    send_order_rejected,
    send_sample_approved_alert,
    send_sample_rejected_alert,
)


router = APIRouter(prefix="/purchasing", tags=["Purchasing Manager"])

# All endpoints require admin or purchasing_manager role
_require_pm = require_store_role("admin", "purchasing_manager")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    notes: Optional[str] = None


class RejectionRequest(BaseModel):
    reason: str
    notes: Optional[str] = None


class DashboardStats(BaseModel):
    pending_order_approvals: int
    pending_sample_approvals: int
    recent_orders: list[dict]
    recent_samples: list[dict]


class OrderListItem(BaseModel):
    id: str
    order_number: str
    status: str
    payment_status: str
    subtotal: int
    shipping_cost: int
    tax_amount: int
    discount_amount: int
    total: int
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    customer_notes: Optional[str] = None
    created_at: datetime
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None

    class Config:
        from_attributes = True


class OrderDetailResponse(BaseModel):
    id: str
    order_number: str
    status: str
    payment_status: str
    subtotal: int
    shipping_cost: int
    tax_amount: int
    discount_amount: int
    total: int
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    estimated_ship_date: Optional[datetime] = None
    actual_ship_date: Optional[datetime] = None
    created_at: datetime
    items: list[dict] = []
    status_history: list[dict] = []
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    salesperson_name: Optional[str] = None

    class Config:
        from_attributes = True


class SampleListItem(BaseModel):
    id: str
    sample_number: str
    status: str
    current_version: int
    notes: Optional[str] = None
    created_at: datetime
    requested_by_name: Optional[str] = None
    customer_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_display_name(user: Optional[StoreUser]) -> Optional[str]:
    """Return a display name for a StoreUser, or None."""
    if user is None:
        return None
    parts = [user.first_name or "", user.last_name or ""]
    full = " ".join(p for p in parts if p).strip()
    return full or user.email


# ---------------------------------------------------------------------------
# 1. GET /dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """Dashboard stats for the Purchasing Manager."""

    # Pending order approvals
    pending_order_approvals = (
        db.query(Order)
        .filter(Order.status == "pending_approval")
        .count()
    )

    # Pending sample approvals
    pending_sample_approvals = (
        db.query(SampleRequest)
        .filter(SampleRequest.status == "submitted")
        .count()
    )

    # Recent orders (confirmed and beyond) — last 10
    recent_orders_q = (
        db.query(Order)
        .options(joinedload(Order.store_user))
        .filter(Order.status.notin_(["pending", "pending_approval", "revision_needed", "cancelled"]))
        .order_by(Order.created_at.desc())
        .limit(10)
        .all()
    )
    recent_orders = [
        {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status,
            "total": o.total,
            "customer_name": _user_display_name(o.store_user),
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in recent_orders_q
    ]

    # Recent samples — last 10
    recent_samples_q = (
        db.query(SampleRequest)
        .options(
            joinedload(SampleRequest.requested_by),
            joinedload(SampleRequest.customer),
        )
        .order_by(SampleRequest.created_at.desc())
        .limit(10)
        .all()
    )
    recent_samples = [
        {
            "id": s.id,
            "sample_number": s.sample_number,
            "status": s.status,
            "requested_by_name": _user_display_name(s.requested_by),
            "customer_name": _user_display_name(s.customer),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in recent_samples_q
    ]

    return DashboardStats(
        pending_order_approvals=pending_order_approvals,
        pending_sample_approvals=pending_sample_approvals,
        recent_orders=recent_orders,
        recent_samples=recent_samples,
    )


# ---------------------------------------------------------------------------
# 2. GET /orders
# ---------------------------------------------------------------------------

@router.get("/orders", response_model=list[OrderListItem])
async def list_orders(
    status_filter: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """List all orders visible to the Purchasing Manager."""
    query = db.query(Order).options(joinedload(Order.store_user))

    if status_filter:
        query = query.filter(Order.status == status_filter)

    orders = (
        query.order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        OrderListItem(
            id=o.id,
            order_number=o.order_number,
            status=o.status,
            payment_status=o.payment_status,
            subtotal=o.subtotal,
            shipping_cost=o.shipping_cost,
            tax_amount=o.tax_amount,
            discount_amount=o.discount_amount,
            total=o.total,
            shipping_method=o.shipping_method,
            tracking_number=o.tracking_number,
            customer_notes=o.customer_notes,
            created_at=o.created_at,
            customer_name=_user_display_name(o.store_user),
            customer_email=o.store_user.email if o.store_user else None,
        )
        for o in orders
    ]


# ---------------------------------------------------------------------------
# 3. GET /orders/{order_id}
# ---------------------------------------------------------------------------

@router.get("/orders/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: str,
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """Get full order detail (no ownership check — PM can view any order)."""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.status_history),
            joinedload(Order.store_user),
            joinedload(Order.salesperson),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = [
        {
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name if item.product else None,
            "product_style": item.product.style_number if item.product else None,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total_price": item.total_price,
            "customization": item.customization,
            "front_decoration": item.front_decoration,
            "left_decoration": item.left_decoration,
            "right_decoration": item.right_decoration,
            "back_decoration": item.back_decoration,
            "visor_decoration": item.visor_decoration,
        }
        for item in (order.items or [])
    ]

    history = [
        {
            "status": h.status,
            "note": h.note,
            "changed_by": h.changed_by,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in (order.status_history or [])
    ]

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        subtotal=order.subtotal,
        shipping_cost=order.shipping_cost,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        total=order.total,
        shipping_method=order.shipping_method,
        tracking_number=order.tracking_number,
        tracking_url=order.tracking_url,
        customer_notes=order.customer_notes,
        internal_notes=order.internal_notes,
        estimated_ship_date=order.estimated_ship_date,
        actual_ship_date=order.actual_ship_date,
        created_at=order.created_at,
        items=items,
        status_history=history,
        customer_name=_user_display_name(order.store_user),
        customer_email=order.store_user.email if order.store_user else None,
        salesperson_name=_user_display_name(order.salesperson),
    )


# ---------------------------------------------------------------------------
# 4. POST /orders/{order_id}/approve
# ---------------------------------------------------------------------------

@router.post("/orders/{order_id}/approve")
async def approve_order(
    order_id: str,
    data: ApprovalRequest,
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """Approve a salesperson-submitted order.

    Transitions pending_approval -> confirmed.  Payment is NOT collected here;
    the PM will push the order to Business Central as a Sales Order and trigger
    a payment link from BC's EBizCharge integration, which emails the customer.
    """
    order = (
        db.query(Order)
        .options(
            joinedload(Order.store_user),
            joinedload(Order.salesperson),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Order status is '{order.status}', expected 'pending_approval'",
        )

    # Transition to confirmed — payment_status stays "unpaid" until BC
    # collects payment via EBizCharge payment link
    order.status = "confirmed"

    history = OrderStatusHistory(
        order_id=order.id,
        status="confirmed",
        note=data.notes or "Approved by purchasing manager — awaiting BC sync and payment",
        changed_by=pm.id,
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    # Notify the salesperson that their order was approved
    salesperson = order.salesperson or order.store_user
    if salesperson and salesperson.email:
        send_order_approved(
            to_email=salesperson.email,
            order_number=order.order_number,
        )

    # NOTE: No customer email here. The customer will receive a payment link
    # email directly from EBizCharge when the PM triggers it from Business Central.

    return {
        "message": "Order approved",
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
    }


# ---------------------------------------------------------------------------
# 5. POST /orders/{order_id}/reject
# ---------------------------------------------------------------------------

@router.post("/orders/{order_id}/reject")
async def reject_order(
    order_id: str,
    data: RejectionRequest,
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """Reject a salesperson-submitted order (pending_approval -> revision_needed)."""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.store_user),
            joinedload(Order.salesperson),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Order status is '{order.status}', expected 'pending_approval'",
        )

    # Transition to revision_needed
    order.status = "revision_needed"

    # Add status history entry
    note = f"Rejected: {data.reason}"
    if data.notes:
        note += f" | Notes: {data.notes}"

    history = OrderStatusHistory(
        order_id=order.id,
        status="revision_needed",
        note=note,
        changed_by=pm.id,
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    # Send rejection email to salesperson
    salesperson = order.salesperson or order.store_user
    if salesperson and salesperson.email:
        send_order_rejected(
            to_email=salesperson.email,
            order_number=order.order_number,
            reason=data.reason,
        )

    return {
        "message": "Order sent back for revision",
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "reason": data.reason,
    }


# ---------------------------------------------------------------------------
# 6. GET /samples
# ---------------------------------------------------------------------------

@router.get("/samples", response_model=list[SampleListItem])
async def list_samples(
    status_filter: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """List sample requests visible to the Purchasing Manager."""
    query = db.query(SampleRequest).options(
        joinedload(SampleRequest.requested_by),
        joinedload(SampleRequest.customer),
    )

    if status_filter:
        query = query.filter(SampleRequest.status == status_filter)

    samples = (
        query.order_by(SampleRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        SampleListItem(
            id=s.id,
            sample_number=s.sample_number,
            status=s.status,
            current_version=s.current_version,
            notes=s.notes,
            created_at=s.created_at,
            requested_by_name=_user_display_name(s.requested_by),
            customer_name=_user_display_name(s.customer),
        )
        for s in samples
    ]


# ---------------------------------------------------------------------------
# 7. POST /samples/{sample_id}/approve
# ---------------------------------------------------------------------------

@router.post("/samples/{sample_id}/approve")
async def approve_sample(
    sample_id: str,
    data: ApprovalRequest,
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """Approve a submitted sample request (submitted -> approved)."""
    sample = (
        db.query(SampleRequest)
        .options(joinedload(SampleRequest.requested_by))
        .filter(SampleRequest.id == sample_id)
        .first()
    )
    if not sample:
        raise HTTPException(status_code=404, detail="Sample request not found")

    if sample.status != "submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Sample status is '{sample.status}', expected 'submitted'",
        )

    # Transition to approved
    sample.status = "approved"

    # Add activity log entry
    activity = SampleActivity(
        sample_request_id=sample.id,
        user_id=pm.id,
        action="status_change",
        description=data.notes or "Sample request approved by purchasing manager",
    )
    db.add(activity)
    db.commit()
    db.refresh(sample)

    # Send approval alert to the salesperson who requested it
    salesperson = sample.requested_by
    if salesperson and salesperson.email:
        send_sample_approved_alert(
            to_email=salesperson.email,
            sample_number=sample.sample_number,
        )

    return {
        "message": "Sample request approved",
        "sample_id": sample.id,
        "sample_number": sample.sample_number,
        "status": sample.status,
    }


# ---------------------------------------------------------------------------
# 8. POST /samples/{sample_id}/reject
# ---------------------------------------------------------------------------

@router.post("/samples/{sample_id}/reject")
async def reject_sample(
    sample_id: str,
    data: RejectionRequest,
    pm: StoreUser = Depends(_require_pm),
    db: Session = Depends(get_db),
):
    """Reject a submitted sample request (submitted -> rejected)."""
    sample = (
        db.query(SampleRequest)
        .options(joinedload(SampleRequest.requested_by))
        .filter(SampleRequest.id == sample_id)
        .first()
    )
    if not sample:
        raise HTTPException(status_code=404, detail="Sample request not found")

    if sample.status != "submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Sample status is '{sample.status}', expected 'submitted'",
        )

    # Transition to rejected
    sample.status = "rejected"

    # Add activity log entry
    description = f"Sample request rejected: {data.reason}"
    if data.notes:
        description += f" | Notes: {data.notes}"

    activity = SampleActivity(
        sample_request_id=sample.id,
        user_id=pm.id,
        action="status_change",
        description=description,
    )
    db.add(activity)
    db.commit()
    db.refresh(sample)

    # Send rejection alert to the salesperson who requested it
    salesperson = sample.requested_by
    if salesperson and salesperson.email:
        send_sample_rejected_alert(
            to_email=salesperson.email,
            sample_number=sample.sample_number,
            reason=data.reason,
        )

    return {
        "message": "Sample request rejected",
        "sample_id": sample.id,
        "sample_number": sample.sample_number,
        "status": sample.status,
        "reason": data.reason,
    }
