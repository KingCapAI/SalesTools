"""Store checkout routes with inline EBizCharge payment.

Flow:
  1. Frontend renders EBizCharge PayForm JS iframe (card entry on our page)
  2. EBizCharge JS tokenizes the card → returns a one-time payment_token
  3. Frontend calls POST /api/store/checkout/pay with the token + shipping info
  4. Backend charges the token via EBizCharge API, confirms the order inline
  5. Response tells the frontend whether payment succeeded

No redirects — the customer never leaves our site.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.store_order import Order, OrderItem, OrderStatusHistory
from ..models.store_cart import CartItem
from ..models.store_user import StoreUser
from ..utils.store_dependencies import require_store_auth
from ..config import get_settings
from ..services.email_service import send_order_confirmation, send_new_order_alert
from ..services.ebizcharge_service import run_sale

router = APIRouter(prefix="/store/checkout", tags=["Store Checkout"])

settings = get_settings()


class PayRequest(BaseModel):
    payment_token: str
    shipping_name: str
    shipping_email: str
    shipping_address: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    customer_notes: Optional[str] = None


def _generate_order_number(db: Session) -> str:
    """Generate a unique order number like KC-2026-00001."""
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


def _get_staff_emails(db: Session, roles: list[str]) -> list[str]:
    staff = (
        db.query(StoreUser)
        .filter(StoreUser.role.in_(roles), StoreUser.status == "active")
        .all()
    )
    return [s.email for s in staff]


@router.get("/config")
async def get_checkout_config():
    """Return the public EBizCharge source key for the frontend PayForm JS.

    The frontend needs this to initialize the EBizCharge embedded card form.
    This is safe to expose — it can only create tokens, not charge cards.
    """
    return {
        "source_key": settings.ebizcharge_source_key,
        "environment": settings.ebizcharge_environment,
    }


@router.post("/pay")
async def pay(
    data: PayRequest,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Charge the payment token and create + confirm the order in one step.

    The frontend has already collected card details via the EBizCharge JS SDK
    and obtained a one-time payment_token. We charge that token here.
    """
    # Get cart items
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

    # Create the order
    order = Order(
        order_number=_generate_order_number(db),
        store_user_id=user.id,
        status="pending",
        payment_status="unpaid",
        subtotal=subtotal,
        shipping_cost=0,
        tax_amount=0,
        discount_amount=0,
        total=subtotal,
        customer_notes=data.customer_notes,
    )
    db.add(order)
    db.flush()

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

    # Add initial status history
    history = OrderStatusHistory(
        order_id=order.id,
        status="pending",
        note="Order created - processing payment",
        changed_by=user.id,
    )
    db.add(history)
    db.flush()

    # Build line items for EBizCharge receipt
    line_items = [
        {
            "name": item.product.name if item.product else "Custom Hat",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
        }
        for item in cart_items
    ]

    # Charge the payment token
    try:
        result = run_sale(
            payment_token=data.payment_token,
            amount_cents=subtotal,
            order_number=order.order_number,
            customer_email=data.shipping_email,
            customer_name=data.shipping_name,
            line_items=line_items,
        )
    except Exception as e:
        # Network / config error — order stays pending
        order.payment_status = "failed"
        db.add(OrderStatusHistory(
            order_id=order.id,
            status="pending",
            note=f"Payment gateway error: {e}",
            changed_by=user.id,
        ))
        db.commit()
        raise HTTPException(status_code=502, detail="Payment gateway unavailable")

    if result["status"] != "approved":
        # Card declined or error
        order.payment_status = "failed"
        db.add(OrderStatusHistory(
            order_id=order.id,
            status="pending",
            note=f"Payment declined: {result.get('error', 'unknown')}",
            changed_by=user.id,
        ))
        db.commit()
        raise HTTPException(
            status_code=402,
            detail=result.get("error") or "Payment was not approved. Please check your card details and try again.",
        )

    # Payment approved — confirm the order
    order.payment_status = "paid"
    order.status = "confirmed"
    order.ebiz_transaction_id = result["transaction_id"]
    order.ebiz_auth_code = result.get("auth_code", "")

    db.add(OrderStatusHistory(
        order_id=order.id,
        status="confirmed",
        note="Payment received via EBizCharge",
        changed_by=user.id,
    ))

    # Clear cart
    for cart_item in cart_items:
        db.delete(cart_item)

    db.commit()

    # Send order confirmation email
    email_items = [
        {
            "name": item.product.name if item.product else "Custom Hat",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
        }
        for item in cart_items
    ]
    send_order_confirmation(
        to_email=user.email,
        order_number=order.order_number,
        items=email_items,
        total_cents=order.total,
    )

    # Notify staff
    staff_emails = _get_staff_emails(
        db, ["admin", "salesperson", "purchasing_manager"]
    )
    for email in staff_emails:
        send_new_order_alert(
            to_email=email,
            order_number=order.order_number,
            customer_name=f"{user.first_name} {user.last_name}",
            total_cents=order.total,
        )

    return {
        "success": True,
        "order_id": order.id,
        "order_number": order.order_number,
        "transaction_id": result["transaction_id"],
    }


@router.get("/verify/{order_id}")
async def verify_order_payment(
    order_id: str,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Check the payment/order status (used by frontend success page)."""
    order = db.query(Order).filter(
        Order.id == order_id, Order.store_user_id == user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
    }
