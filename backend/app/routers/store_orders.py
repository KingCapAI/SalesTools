"""Store order management routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.store_order import Order, OrderItem, OrderStatusHistory, Invoice
from ..models.store_cart import CartItem
from ..models.store_user import StoreUser
from ..models.store_product import Product
from ..models.mockup import MockupApproval
from ..utils.store_dependencies import require_store_auth, require_store_role
from ..services.email_service import (
    send_order_status_update,
    send_sewout_ready,
    send_sewout_response_alert,
    send_mockup_ready,
    send_mockup_response_alert,
    send_new_order_alert,
    send_refund_processed,
)
from ..services.ebizcharge_service import process_refund, void_transaction

router = APIRouter(prefix="/store/orders", tags=["Store Orders"])


class OrderResponse(BaseModel):
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
    estimated_ship_date: Optional[datetime] = None
    actual_ship_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    quantity: int
    unit_price: int
    total_price: int
    customization: Optional[str] = None
    front_decoration: Optional[str] = None
    left_decoration: Optional[str] = None
    right_decoration: Optional[str] = None
    back_decoration: Optional[str] = None
    visor_decoration: Optional[str] = None
    product_name: Optional[str] = None
    product_style: Optional[str] = None

    class Config:
        from_attributes = True


class SewOutApprovalResponse(BaseModel):
    id: str
    version: int
    status: str
    mockup_image_url: str
    admin_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    items: list[OrderItemResponse] = []
    status_history: list[dict] = []
    sew_out_approvals: list[SewOutApprovalResponse] = []


class OrderStatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None


class CreateOrderFromCart(BaseModel):
    shipping_address_id: Optional[str] = None
    billing_address_id: Optional[str] = None
    shipping_method: Optional[str] = None
    customer_notes: Optional[str] = None


class SewOutUpload(BaseModel):
    image_url: str
    admin_notes: Optional[str] = None


class SewOutResponse(BaseModel):
    response: str  # "approved" or "revision"
    customer_notes: Optional[str] = None


def _get_staff_emails(db: Session, roles: list[str]) -> list[str]:
    """Get email addresses for staff members with given roles."""
    staff = db.query(StoreUser).filter(
        StoreUser.role.in_(roles),
        StoreUser.status == "active",
    ).all()
    return [s.email for s in staff]


# Valid order status transitions
ORDER_STATUS_TRANSITIONS = {
    "pending": ("pending_approval", "confirmed", "cancelled"),
    "pending_approval": ("confirmed", "revision_needed", "cancelled"),
    "revision_needed": ("pending_approval", "cancelled"),
    "confirmed": ("mockup_pending", "in_production", "cancelled"),
    "mockup_pending": ("mockup_approved", "cancelled"),
    "mockup_approved": ("in_production", "cancelled"),
    "in_production": ("sew_out_review", "quality_check", "cancelled"),
    "sew_out_review": ("sew_out_approved", "in_production", "cancelled"),
    "sew_out_approved": ("quality_check", "cancelled"),
    "quality_check": ("shipped", "in_production"),
    "shipped": ("delivered",),
    "delivered": (),
    "cancelled": ("pending",),
    "refunded": (),
}


def _generate_order_number(db: Session) -> str:
    """Generate a unique order number."""
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


@router.get("", response_model=list[OrderResponse])
async def list_orders(
    status_filter: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """List orders for current user."""
    query = db.query(Order).filter(Order.store_user_id == user.id)

    if status_filter:
        query = query.filter(Order.status == status_filter)

    orders = (
        query.order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return orders


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: str,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Get order details."""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.status_history),
            joinedload(Order.mockup_approvals),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify ownership (admin/salesperson can see any order)
    if user.role not in ("admin", "salesperson", "purchasing_manager") and order.store_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    # Build response
    items = []
    for item in order.items:
        items.append(OrderItemResponse(
            id=item.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            customization=item.customization,
            front_decoration=item.front_decoration,
            left_decoration=item.left_decoration,
            right_decoration=item.right_decoration,
            back_decoration=item.back_decoration,
            visor_decoration=item.visor_decoration,
            product_name=item.product.name if item.product else None,
            product_style=item.product.style_number if item.product else None,
        ))

    history = [
        {
            "status": h.status,
            "note": h.note,
            "changed_by": h.changed_by,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        }
        for h in (order.status_history or [])
    ]

    # Build sew-out approvals (sorted by version desc)
    sew_outs = [
        SewOutApprovalResponse(
            id=a.id,
            version=a.version,
            status=a.status,
            mockup_image_url=a.mockup_image_url,
            admin_notes=a.admin_notes,
            customer_notes=a.customer_notes,
            created_at=a.created_at,
            responded_at=a.responded_at,
        )
        for a in sorted(
            (a for a in (order.mockup_approvals or []) if a.approval_type == "sew_out"),
            key=lambda a: a.version,
            reverse=True,
        )
    ]

    return OrderDetailResponse(
        **OrderResponse.model_validate(order).model_dump(),
        items=items,
        status_history=history,
        sew_out_approvals=sew_outs,
    )


@router.post("/from-cart", response_model=OrderResponse, status_code=201)
async def create_order_from_cart(
    data: CreateOrderFromCart,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Create an order from the current cart (direct payment, no Stripe for now)."""
    cart_items = (
        db.query(CartItem)
        .filter(CartItem.store_user_id == user.id)
        .options(joinedload(CartItem.product))
        .all()
    )

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Calculate totals
    subtotal = sum(item.unit_price * item.quantity for item in cart_items)
    shipping_cost = 0  # TODO: calculate based on method
    tax_amount = 0  # TODO: calculate based on address
    total = subtotal + shipping_cost + tax_amount

    # Create order
    order = Order(
        order_number=_generate_order_number(db),
        store_user_id=user.id,
        status="pending",
        payment_status="unpaid",
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax_amount=tax_amount,
        discount_amount=0,
        total=total,
        shipping_address_id=data.shipping_address_id,
        billing_address_id=data.billing_address_id,
        shipping_method=data.shipping_method,
        customer_notes=data.customer_notes,
    )
    db.add(order)
    db.flush()  # Get order.id

    # Create order items from cart
    for cart_item in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            variant_id=cart_item.variant_id,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            total_price=cart_item.unit_price * cart_item.quantity,
            customization=cart_item.customization,
        )
        db.add(order_item)

    # Add status history
    history = OrderStatusHistory(
        order_id=order.id,
        status="pending",
        note="Order created",
        changed_by=user.id,
    )
    db.add(history)

    # Clear cart
    for cart_item in cart_items:
        db.delete(cart_item)

    db.commit()
    db.refresh(order)
    return order


# === Admin order management ===

@router.get("/admin/all", response_model=list[OrderResponse])
async def admin_list_orders(
    status_filter: Optional[str] = None,
    customer_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin=Depends(require_store_role("admin", "salesperson", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """List all orders (admin/salesperson/purchasing manager)."""
    query = db.query(Order)

    if status_filter:
        query = query.filter(Order.status == status_filter)
    if customer_id:
        query = query.filter(Order.store_user_id == customer_id)

    return (
        query.order_by(Order.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    admin=Depends(require_store_role("admin", "salesperson", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Update order status (admin/salesperson/purchasing manager) with transition validation."""
    order = (
        db.query(Order)
        .options(joinedload(Order.store_user))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Validate status transition
    allowed = ORDER_STATUS_TRANSITIONS.get(order.status, ())
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{order.status}' to '{data.status}'. Allowed: {list(allowed)}",
        )

    order.status = data.status
    if data.tracking_number:
        order.tracking_number = data.tracking_number
    if data.tracking_url:
        order.tracking_url = data.tracking_url

    # Add history entry
    history = OrderStatusHistory(
        order_id=order.id,
        status=data.status,
        note=data.note,
        changed_by=admin.id,
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    # Send status update email
    if order.store_user and order.store_user.email:
        send_order_status_update(
            to_email=order.store_user.email,
            order_number=order.order_number,
            new_status=data.status,
            tracking_number=data.tracking_number,
            tracking_url=data.tracking_url,
        )

    return order


# === Sew-out / Factory Sample Approval ===

@router.post("/{order_id}/sew-out")
async def upload_sew_out(
    order_id: str,
    data: SewOutUpload,
    admin=Depends(require_store_role("admin", "salesperson", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Upload sew-out/factory sample photo for customer approval."""
    from sqlalchemy import func as sqlfunc
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ("in_production", "sew_out_review"):
        raise HTTPException(
            status_code=400,
            detail=f"Order must be in 'in_production' or 'sew_out_review' status (currently '{order.status}')",
        )

    # Supersede previous pending sew-out approvals
    existing = (
        db.query(MockupApproval)
        .filter(
            MockupApproval.order_id == order_id,
            MockupApproval.approval_type == "sew_out",
            MockupApproval.status == "pending",
        )
        .all()
    )
    for prev in existing:
        prev.status = "superseded"

    # Determine version number
    max_version = (
        db.query(sqlfunc.max(MockupApproval.version))
        .filter(
            MockupApproval.order_id == order_id,
            MockupApproval.approval_type == "sew_out",
        )
        .scalar()
    ) or 0

    approval = MockupApproval(
        order_id=order_id,
        store_user_id=order.store_user_id,
        mockup_image_url=data.image_url,
        version=max_version + 1,
        approval_type="sew_out",
        status="pending",
        admin_notes=data.admin_notes,
    )
    db.add(approval)

    # Transition order to sew_out_review
    if order.status == "in_production":
        order.status = "sew_out_review"
        history = OrderStatusHistory(
            order_id=order.id,
            status="sew_out_review",
            note="Sew-out photos uploaded for customer review",
            changed_by=admin.id,
        )
        db.add(history)

    db.commit()
    db.refresh(approval)

    # Notify customer that sew-out photos are ready
    customer = db.query(StoreUser).filter(StoreUser.id == order.store_user_id).first()
    if customer and customer.email:
        send_sewout_ready(
            to_email=customer.email,
            first_name=customer.first_name,
            order_number=order.order_number,
        )

    return {
        "id": approval.id,
        "version": approval.version,
        "status": approval.status,
        "mockup_image_url": approval.mockup_image_url,
        "message": "Sew-out uploaded for customer review",
    }


@router.post("/{order_id}/sew-out-response")
async def respond_to_sew_out(
    order_id: str,
    data: SewOutResponse,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Customer or salesperson responds to sew-out photos (approve or request revision)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Allow: order owner, assigned salesperson, or admin
    if user.role not in ("admin", "salesperson", "purchasing_manager") and order.store_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")

    if order.status != "sew_out_review":
        raise HTTPException(status_code=400, detail="Order is not awaiting sew-out review")

    if data.response not in ("approved", "revision"):
        raise HTTPException(status_code=400, detail="Response must be 'approved' or 'revision'")

    # Find the latest pending sew-out approval
    approval = (
        db.query(MockupApproval)
        .filter(
            MockupApproval.order_id == order_id,
            MockupApproval.approval_type == "sew_out",
            MockupApproval.status == "pending",
        )
        .order_by(MockupApproval.version.desc())
        .first()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="No pending sew-out approval found")

    approval.status = data.response  # "approved" or "revision"
    approval.customer_notes = data.customer_notes
    approval.responded_at = datetime.utcnow()

    if data.response == "approved":
        order.status = "sew_out_approved"
        note = "Customer approved sew-out — proceeding to full production"
    else:
        order.status = "in_production"  # Back to production for revision
        note = f"Customer requested sew-out revision: {data.customer_notes or 'No notes'}"

    history = OrderStatusHistory(
        order_id=order.id,
        status=order.status,
        note=note,
        changed_by=user.id,
    )
    db.add(history)

    db.commit()

    # Notify staff about sew-out response
    staff_emails = _get_staff_emails(db, ["admin", "salesperson", "purchasing_manager"])
    # Also add assigned salesperson if exists
    if order.salesperson_id:
        sp = db.query(StoreUser).filter(StoreUser.id == order.salesperson_id).first()
        if sp and sp.email not in staff_emails:
            staff_emails.append(sp.email)

    for email in staff_emails:
        send_sewout_response_alert(
            to_email=email,
            order_number=order.order_number,
            approved=(data.response == "approved"),
            feedback=data.customer_notes,
        )

    return {
        "message": note,
        "order_status": order.status,
        "sew_out_status": approval.status,
    }


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

class RefundRequest(BaseModel):
    amount_cents: Optional[int] = None  # None = full refund
    reason: Optional[str] = None


@router.post("/{order_id}/refund")
async def refund_order(
    order_id: str,
    data: RefundRequest,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Process a refund for an order via EBizCharge."""
    order = (
        db.query(Order)
        .options(joinedload(Order.store_user))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.payment_status not in ("paid", "partially_refunded"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund order with payment status '{order.payment_status}'",
        )

    if not order.ebiz_transaction_id:
        raise HTTPException(
            status_code=400,
            detail="No EBizCharge transaction found for this order",
        )

    refund_amount = data.amount_cents if data.amount_cents else order.total
    is_full_refund = refund_amount >= order.total

    try:
        result = process_refund(
            transaction_id=order.ebiz_transaction_id,
            amount_cents=refund_amount,
            reason=data.reason,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Refund failed: {e}")

    if result["status"] != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Refund was not approved: {result.get('raw', {}).get('error', 'unknown')}",
        )

    # Update order
    order.ebiz_refund_transaction_id = result["refund_transaction_id"]
    if is_full_refund:
        order.payment_status = "refunded"
        order.status = "refunded"
    else:
        order.payment_status = "partially_refunded"

    history = OrderStatusHistory(
        order_id=order.id,
        status=order.status,
        note=f"Refund of ${refund_amount / 100:.2f} processed"
        + (f" — {data.reason}" if data.reason else ""),
        changed_by=admin.id,
    )
    db.add(history)
    db.commit()

    # Notify customer and staff
    if order.store_user and order.store_user.email:
        send_refund_processed(
            to_email=order.store_user.email,
            return_number=order.order_number,
            amount_cents=refund_amount,
        )

    staff_emails = _get_staff_emails(db, ["admin", "purchasing_manager"])
    for email in staff_emails:
        send_refund_processed(
            to_email=email,
            return_number=order.order_number,
            amount_cents=refund_amount,
        )

    return {
        "message": f"Refund of ${refund_amount / 100:.2f} processed successfully",
        "refund_transaction_id": result["refund_transaction_id"],
        "payment_status": order.payment_status,
        "order_status": order.status,
    }
