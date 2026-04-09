"""Customer-facing quote endpoints — view, accept, reject quotes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.store_quote import Quote, QuoteLineItem
from ..models.store_user import StoreUser
from ..utils.store_dependencies import require_store_auth
from ..services.email_service import send_quote_response_alert

router = APIRouter(prefix="/store/quotes", tags=["Store Quotes"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class QuoteRespondRequest(BaseModel):
    action: str  # "accept" or "reject"
    reason: Optional[str] = None


class QuoteLineItemResponse(BaseModel):
    id: str
    line_number: int
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
    production_type: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class QuoteDetailResponse(BaseModel):
    id: str
    quote_number: str
    status: str
    subtotal: int
    discount_amount: int
    shipping_estimate: int
    total: int
    notes: Optional[str] = None
    valid_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    salesperson_name: Optional[str] = None
    line_items: list[QuoteLineItemResponse] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_response(quote: Quote) -> QuoteDetailResponse:
    salesperson_name = None
    if quote.salesperson:
        sp = quote.salesperson
        salesperson_name = f"{sp.first_name or ''} {sp.last_name or ''}".strip() or sp.email

    items = [
        QuoteLineItemResponse(
            id=li.id,
            line_number=li.line_number,
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
            production_type=li.production_type,
            notes=li.notes,
        )
        for li in (quote.line_items or [])
    ]

    return QuoteDetailResponse(
        id=quote.id,
        quote_number=quote.quote_number,
        status=quote.status,
        subtotal=quote.subtotal,
        discount_amount=quote.discount_amount,
        shipping_estimate=quote.shipping_estimate,
        total=quote.total,
        notes=quote.notes,
        valid_until=quote.valid_until,
        created_at=quote.created_at,
        salesperson_name=salesperson_name,
        line_items=items,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[QuoteDetailResponse])
async def list_my_quotes(
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """List quotes sent to the current customer."""
    quotes = (
        db.query(Quote)
        .options(
            joinedload(Quote.salesperson),
            joinedload(Quote.line_items),
        )
        .filter(
            Quote.store_user_id == user.id,
            Quote.status.in_(["sent", "viewed", "accepted", "rejected", "expired"]),
        )
        .order_by(Quote.created_at.desc())
        .all()
    )
    return [_build_response(q) for q in quotes]


@router.get("/{quote_id}", response_model=QuoteDetailResponse)
async def get_my_quote(
    quote_id: str,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Get detail of a specific quote (customer-facing)."""
    quote = (
        db.query(Quote)
        .options(
            joinedload(Quote.salesperson),
            joinedload(Quote.line_items),
        )
        .filter(Quote.id == quote_id, Quote.store_user_id == user.id)
        .first()
    )
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Mark as viewed if still in "sent" status
    if quote.status == "sent":
        quote.status = "viewed"
        db.commit()
        db.refresh(quote)

    return _build_response(quote)


@router.post("/{quote_id}/respond")
async def respond_to_quote(
    quote_id: str,
    data: QuoteRespondRequest,
    user: StoreUser = Depends(require_store_auth),
    db: Session = Depends(get_db),
):
    """Accept or reject a quote."""
    quote = (
        db.query(Quote)
        .options(joinedload(Quote.salesperson))
        .filter(Quote.id == quote_id, Quote.store_user_id == user.id)
        .first()
    )
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    if quote.status not in ("sent", "viewed"):
        raise HTTPException(
            status_code=400,
            detail=f"Quote is in '{quote.status}' status and cannot be responded to",
        )

    # Check expiration
    if quote.valid_until and quote.valid_until < datetime.utcnow():
        quote.status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail="This quote has expired")

    if data.action == "accept":
        quote.status = "accepted"
    elif data.action == "reject":
        quote.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'")

    db.commit()

    # Notify salesperson
    if quote.salesperson and quote.salesperson.email:
        send_quote_response_alert(
            to_email=quote.salesperson.email,
            quote_number=quote.quote_number,
            accepted=(data.action == "accept"),
            reason=data.reason,
        )

    return {
        "message": f"Quote {data.action}ed",
        "quote_id": quote.id,
        "quote_number": quote.quote_number,
        "status": quote.status,
    }
