"""Store returns routes — customer-facing and admin/PM return management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.return_request import ReturnRequest, ReturnLineItem
from ..models.store_order import Order, OrderItem
from ..models.store_user import StoreUser
from ..utils.store_dependencies import require_store_auth, require_store_role
from ..services.email_service import (
    send_return_request_received,
    send_return_request_alert,
    send_return_approved,
    send_return_rejected,
    send_refund_processed,
)
from ..services.ebizcharge_service import process_refund

router = APIRouter(prefix="/store/returns", tags=["Store Returns"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReturnItemRequest(BaseModel):
    order_item_id: str
    quantity: int
    reason: Optional[str] = None
    condition: Optional[str] = None  # new, opened, used, damaged


class CreateReturnRequest(BaseModel):
    order_id: str
    reason: str  # defective, wrong_item, not_as_described, changed_mind, other
    reason_details: Optional[str] = None
    customer_notes: Optional[str] = None
    items: list[ReturnItemRequest]


class UpdateReturnStatus(BaseModel):
    status: str  # approved, rejected, shipped_back, received, closed
    admin_notes: Optional[str] = None
    refund_method: Optional[str] = None  # original_payment, store_credit


class ReturnResponse(BaseModel):
    id: str
    return_number: str
    order_id: str
    order_number: Optional[str] = None
    status: str
    reason: str
    reason_details: Optional[str] = None
    refund_amount: Optional[int] = None
    refund_method: Optional[str] = None
    return_tracking_number: Optional[str] = None
    return_tracking_url: Optional[str] = None
    admin_notes: Optional[str] = None
    customer_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: list[dict] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_return_number(db: Session) -> str:
    year = datetime.utcnow().year
    last = (
        db.query(ReturnRequest)
        .filter(ReturnRequest.return_number.like(f"RMA-{year}-%"))
        .order_by(ReturnRequest.created_at.desc())
        .first()
    )
    if last:
        num = int(last.return_number.split("-")[-1])
        return f"RMA-{year}-{num + 1:05d}"
    return f"RMA-{year}-00001"


def _get_staff_emails(db: Session, roles: list[str]) -> list[str]:
    staff = (
        db.query(StoreUser)
        .filter(StoreUser.role.in_(roles), StoreUser.status == "active")
        .all()
    )
    return [s.email for s in staff]


def _return_to_response(ret: ReturnRequest) -> ReturnResponse:
    return ReturnResponse(
        id=ret.id,
        return_number=ret.return_number,
        order_id=ret.order_id,
        order_number=ret.order.order_number if ret.order else None,
        status=ret.status,
        reason=ret.reason,
        reason_details=ret.reason_details,
        refund_amount=ret.refund_amount,
        refund_method=ret.refund_method,
        return_tracking_number=ret.return_tracking_number,
        return_tracking_url=ret.return_tracking_url,
        admin_notes=ret.admin_notes,
        customer_notes=ret.customer_notes,
        created_at=ret.created_at,
        updated_at=ret.updated_at,
        items=[
            {
                "id": li.id,
                "order_item_id": li.order_item_id,
                "product_id": li.product_id,
                "product_name": li.product.name if li.product else None,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "total_refund": li.total_refund,
                "reason": li.reason,
                "condition": li.condition,
            }
            for li in (ret.line_items or [])
        ],
    )


# ---------------------------------------------------------------------------
# Customer-Facing Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=ReturnResponse)
async def create_return(
    data: CreateReturnRequest,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Customer initiates a return request."""
    # Verify the order belongs to this customer
    order = db.query(Order).filter(
        Order.id == data.order_id, Order.store_user_id == user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ("pending", "pending_approval", "cancelled"):
        raise HTTPException(status_code=400, detail="This order is not eligible for returns")

    # Create the return request
    ret = ReturnRequest(
        return_number=_generate_return_number(db),
        order_id=order.id,
        store_user_id=user.id,
        reason=data.reason,
        reason_details=data.reason_details,
        customer_notes=data.customer_notes,
    )
    db.add(ret)
    db.flush()

    # Add line items
    total_refund = 0
    for item_req in data.items:
        order_item = db.query(OrderItem).filter(
            OrderItem.id == item_req.order_item_id,
            OrderItem.order_id == order.id,
        ).first()
        if not order_item:
            raise HTTPException(
                status_code=400,
                detail=f"Order item {item_req.order_item_id} not found",
            )
        if item_req.quantity > order_item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Return quantity exceeds ordered quantity for item {item_req.order_item_id}",
            )

        item_refund = order_item.unit_price * item_req.quantity
        total_refund += item_refund

        line = ReturnLineItem(
            return_request_id=ret.id,
            order_item_id=order_item.id,
            product_id=order_item.product_id,
            variant_id=order_item.variant_id,
            quantity=item_req.quantity,
            unit_price=order_item.unit_price,
            total_refund=item_refund,
            reason=item_req.reason,
            condition=item_req.condition,
        )
        db.add(line)

    ret.refund_amount = total_refund
    db.commit()
    db.refresh(ret)

    # Send confirmation to customer
    send_return_request_received(
        to_email=user.email,
        first_name=user.first_name or "there",
        return_number=ret.return_number,
    )

    # Notify staff
    staff_emails = _get_staff_emails(db, ["admin", "purchasing_manager"])
    for email in staff_emails:
        send_return_request_alert(
            to_email=email,
            return_number=ret.return_number,
            customer_name=f"{user.first_name} {user.last_name}",
            reason=data.reason,
        )

    # Re-query with relationships
    ret = (
        db.query(ReturnRequest)
        .options(
            joinedload(ReturnRequest.order),
            joinedload(ReturnRequest.line_items).joinedload(ReturnLineItem.product),
        )
        .filter(ReturnRequest.id == ret.id)
        .first()
    )
    return _return_to_response(ret)


@router.get("", response_model=list[ReturnResponse])
async def list_my_returns(
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """List the current customer's return requests."""
    returns = (
        db.query(ReturnRequest)
        .options(
            joinedload(ReturnRequest.order),
            joinedload(ReturnRequest.line_items).joinedload(ReturnLineItem.product),
        )
        .filter(ReturnRequest.store_user_id == user.id)
        .order_by(ReturnRequest.created_at.desc())
        .all()
    )
    return [_return_to_response(r) for r in returns]


@router.get("/{return_id}", response_model=ReturnResponse)
async def get_my_return(
    return_id: str,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Get detail of a specific return request (customer-facing)."""
    ret = (
        db.query(ReturnRequest)
        .options(
            joinedload(ReturnRequest.order),
            joinedload(ReturnRequest.line_items).joinedload(ReturnLineItem.product),
        )
        .filter(ReturnRequest.id == return_id, ReturnRequest.store_user_id == user.id)
        .first()
    )
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")
    return _return_to_response(ret)


# ---------------------------------------------------------------------------
# Admin / PM Endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/all", response_model=list[ReturnResponse])
async def list_all_returns(
    status_filter: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """List all return requests (admin/PM)."""
    query = db.query(ReturnRequest).options(
        joinedload(ReturnRequest.order),
        joinedload(ReturnRequest.store_user),
        joinedload(ReturnRequest.line_items).joinedload(ReturnLineItem.product),
    )

    if status_filter:
        query = query.filter(ReturnRequest.status == status_filter)

    returns = (
        query.order_by(ReturnRequest.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_return_to_response(r) for r in returns]


@router.put("/{return_id}/status")
async def update_return_status(
    return_id: str,
    data: UpdateReturnStatus,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Approve, reject, or update status of a return request."""
    ret = (
        db.query(ReturnRequest)
        .options(joinedload(ReturnRequest.store_user))
        .filter(ReturnRequest.id == return_id)
        .first()
    )
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")

    old_status = ret.status
    new_status = data.status

    # Validate transitions
    valid_transitions = {
        "submitted": ["approved", "rejected"],
        "approved": ["shipped_back", "received", "closed"],
        "shipped_back": ["received"],
        "received": ["refund_processing", "closed"],
        "refund_processing": ["refunded", "closed"],
    }
    allowed = valid_transitions.get(old_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{old_status}' to '{new_status}'",
        )

    ret.status = new_status
    if data.admin_notes:
        ret.admin_notes = data.admin_notes
    if data.refund_method:
        ret.refund_method = data.refund_method

    if new_status == "approved":
        ret.approved_by = admin.id
        ret.approved_at = datetime.utcnow()
    elif new_status == "received":
        ret.received_at = datetime.utcnow()

    db.commit()

    # Send emails based on status change
    customer = ret.store_user
    if customer and customer.email:
        if new_status == "approved":
            send_return_approved(
                to_email=customer.email,
                first_name=customer.first_name or "there",
                return_number=ret.return_number,
            )
        elif new_status == "rejected":
            send_return_rejected(
                to_email=customer.email,
                first_name=customer.first_name or "there",
                return_number=ret.return_number,
                reason=data.admin_notes,
            )

    return {
        "message": f"Return status updated to '{new_status}'",
        "return_id": ret.id,
        "return_number": ret.return_number,
        "status": ret.status,
    }


@router.post("/{return_id}/refund")
async def process_return_refund(
    return_id: str,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Process the refund for an approved/received return via EBizCharge."""
    ret = (
        db.query(ReturnRequest)
        .options(
            joinedload(ReturnRequest.order),
            joinedload(ReturnRequest.store_user),
        )
        .filter(ReturnRequest.id == return_id)
        .first()
    )
    if not ret:
        raise HTTPException(status_code=404, detail="Return request not found")

    if ret.status not in ("received", "refund_processing"):
        raise HTTPException(
            status_code=400,
            detail=f"Return must be in 'received' or 'refund_processing' status to process refund",
        )

    order = ret.order
    if not order or not order.ebiz_transaction_id:
        raise HTTPException(
            status_code=400,
            detail="No EBizCharge transaction found on the original order",
        )

    refund_amount = ret.refund_amount or 0
    if refund_amount <= 0:
        raise HTTPException(status_code=400, detail="Refund amount must be greater than zero")

    # Process via EBizCharge
    ret.status = "refund_processing"
    db.commit()

    try:
        result = process_refund(
            transaction_id=order.ebiz_transaction_id,
            amount_cents=refund_amount,
            reason=f"Return {ret.return_number}: {ret.reason}",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Refund processing failed: {e}")

    if result["status"] != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Refund was not approved: {result.get('raw', {}).get('error', 'unknown')}",
        )

    # Update return and order
    ret.status = "refunded"
    ret.refunded_at = datetime.utcnow()

    # Update order payment status
    if refund_amount >= order.total:
        order.payment_status = "refunded"
    else:
        order.payment_status = "partially_refunded"

    order.ebiz_refund_transaction_id = result["refund_transaction_id"]
    db.commit()

    # Send refund confirmation
    customer = ret.store_user
    if customer and customer.email:
        send_refund_processed(
            to_email=customer.email,
            return_number=ret.return_number,
            amount_cents=refund_amount,
        )

    # Notify staff
    staff_emails = _get_staff_emails(db, ["admin", "purchasing_manager"])
    for email in staff_emails:
        send_refund_processed(
            to_email=email,
            return_number=ret.return_number,
            amount_cents=refund_amount,
        )

    return {
        "message": f"Refund of ${refund_amount / 100:.2f} processed",
        "return_id": ret.id,
        "return_number": ret.return_number,
        "refund_transaction_id": result["refund_transaction_id"],
        "status": ret.status,
    }
