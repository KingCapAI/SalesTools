"""Admin analytics and reporting endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models.store_order import Order, OrderItem
from ..models.store_user import StoreUser
from ..models.store_product import Product
from ..models.address import Address
from ..utils.store_dependencies import require_store_role

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class OverviewResponse(BaseModel):
    total_orders: int
    total_revenue: int  # cents
    total_customers: int
    pending_applications: int
    prev_orders: int
    prev_revenue: int  # cents
    prev_customers: int


class TimeSeriesPoint(BaseModel):
    date: str
    value: int


class StatusCount(BaseModel):
    status: str
    count: int


class TopProduct(BaseModel):
    product_id: str
    name: str
    style_number: str
    revenue: int  # cents
    quantity: int


class TopCustomer(BaseModel):
    user_id: str
    name: str
    email: str
    company: Optional[str] = None
    total_spent: int  # cents
    order_count: int


class StateBucket(BaseModel):
    state: str
    revenue: int  # cents
    order_count: int


class RecentOrder(BaseModel):
    id: str
    order_number: str
    customer_name: str
    customer_email: str
    total: int  # cents
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _date_range(days: int):
    """Return (start_current, end_current, start_prev) for comparison."""
    now = datetime.utcnow()
    start_current = now - timedelta(days=days)
    start_prev = start_current - timedelta(days=days)
    return start_current, now, start_prev


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Summary stats with period-over-period comparison."""
    start_current, now, start_prev = _date_range(days)

    # Current period
    current_orders = (
        db.query(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .filter(Order.created_at >= start_current, Order.status != "cancelled")
        .first()
    )
    total_orders = current_orders[0] or 0
    total_revenue = current_orders[1] or 0

    # Previous period
    prev_orders = (
        db.query(func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .filter(
            Order.created_at >= start_prev,
            Order.created_at < start_current,
            Order.status != "cancelled",
        )
        .first()
    )

    # Customers
    total_customers = (
        db.query(func.count(StoreUser.id))
        .filter(StoreUser.role.in_(["customer", "wholesale", "golf"]))
        .scalar()
    ) or 0

    prev_customers = (
        db.query(func.count(StoreUser.id))
        .filter(
            StoreUser.role.in_(["customer", "wholesale", "golf"]),
            StoreUser.created_at < start_current,
        )
        .scalar()
    ) or 0

    # Pending applications
    pending_apps = (
        db.query(func.count(StoreUser.id))
        .filter(StoreUser.application_status == "pending")
        .scalar()
    ) or 0

    return OverviewResponse(
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_customers=total_customers,
        pending_applications=pending_apps,
        prev_orders=prev_orders[0] or 0,
        prev_revenue=prev_orders[1] or 0,
        prev_customers=prev_customers,
    )


@router.get("/revenue-over-time", response_model=list[TimeSeriesPoint])
async def revenue_over_time(
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Revenue grouped by day."""
    start = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            func.date(Order.created_at).label("day"),
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
        )
        .filter(Order.created_at >= start, Order.status != "cancelled")
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )

    return [TimeSeriesPoint(date=str(r.day), value=r.revenue) for r in rows]


@router.get("/orders-over-time", response_model=list[TimeSeriesPoint])
async def orders_over_time(
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Order count grouped by day."""
    start = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("count"),
        )
        .filter(Order.created_at >= start)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )

    return [TimeSeriesPoint(date=str(r.day), value=r.count) for r in rows]


@router.get("/orders-by-status", response_model=list[StatusCount])
async def orders_by_status(
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Order count per status."""
    start = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(Order.status, func.count(Order.id).label("count"))
        .filter(Order.created_at >= start)
        .group_by(Order.status)
        .order_by(func.count(Order.id).desc())
        .all()
    )

    return [StatusCount(status=r.status, count=r.count) for r in rows]


@router.get("/top-products", response_model=list[TopProduct])
async def top_products(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Top products by revenue."""
    start = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            OrderItem.product_id,
            Product.name,
            Product.style_number,
            func.coalesce(func.sum(OrderItem.total_price), 0).label("revenue"),
            func.coalesce(func.sum(OrderItem.quantity), 0).label("quantity"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Order.created_at >= start, Order.status != "cancelled")
        .group_by(OrderItem.product_id, Product.name, Product.style_number)
        .order_by(func.sum(OrderItem.total_price).desc())
        .limit(limit)
        .all()
    )

    return [
        TopProduct(
            product_id=r.product_id,
            name=r.name,
            style_number=r.style_number,
            revenue=r.revenue,
            quantity=r.quantity,
        )
        for r in rows
    ]


@router.get("/top-customers", response_model=list[TopCustomer])
async def top_customers(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Top customers by total spend."""
    start = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            StoreUser.id,
            StoreUser.first_name,
            StoreUser.last_name,
            StoreUser.email,
            StoreUser.company_name,
            func.coalesce(func.sum(Order.total), 0).label("total_spent"),
            func.count(Order.id).label("order_count"),
        )
        .join(Order, Order.store_user_id == StoreUser.id)
        .filter(Order.created_at >= start, Order.status != "cancelled")
        .group_by(StoreUser.id, StoreUser.first_name, StoreUser.last_name, StoreUser.email, StoreUser.company_name)
        .order_by(func.sum(Order.total).desc())
        .limit(limit)
        .all()
    )

    return [
        TopCustomer(
            user_id=r.id,
            name=f"{r.first_name} {r.last_name}".strip() or r.email,
            email=r.email,
            company=r.company_name,
            total_spent=r.total_spent,
            order_count=r.order_count,
        )
        for r in rows
    ]


@router.get("/sales-by-state", response_model=list[StateBucket])
async def sales_by_state(
    days: int = Query(default=30, ge=1, le=365),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Revenue grouped by shipping address state."""
    start = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(
            Address.state,
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .join(Order, Order.shipping_address_id == Address.id)
        .filter(Order.created_at >= start, Order.status != "cancelled")
        .group_by(Address.state)
        .order_by(func.sum(Order.total).desc())
        .all()
    )

    return [
        StateBucket(state=r.state or "Unknown", revenue=r.revenue, order_count=r.order_count)
        for r in rows
    ]


@router.get("/recent-orders", response_model=list[RecentOrder])
async def recent_orders(
    limit: int = Query(default=10, ge=1, le=50),
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Most recent orders with customer info."""
    rows = (
        db.query(Order, StoreUser.first_name, StoreUser.last_name, StoreUser.email)
        .join(StoreUser, StoreUser.id == Order.store_user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        RecentOrder(
            id=order.id,
            order_number=order.order_number,
            customer_name=f"{first} {last}".strip() or email,
            customer_email=email,
            total=order.total,
            status=order.status,
            created_at=order.created_at,
        )
        for order, first, last, email in rows
    ]
