"""Sync management routes — admin-only endpoints for BC and Pipedrive integration."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.store_user import StoreUser
from ..models.store_order import Order
from ..models.sync import SyncLog
from ..utils.store_dependencies import require_store_role
from ..services import bc_sync_service, pipedrive_sync_service

router = APIRouter(prefix="/sync", tags=["Sync Management"])

_require_admin = require_store_role("admin")


# ---------------------------------------------------------------------------
# Sync Status Dashboard
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_sync_status(
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Get overall sync health dashboard."""
    return bc_sync_service.get_sync_status(db)


# ---------------------------------------------------------------------------
# Sync Logs
# ---------------------------------------------------------------------------

@router.get("/logs")
async def get_sync_logs(
    integration: Optional[str] = None,
    entity_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """View sync audit log with optional filters."""
    query = db.query(SyncLog)

    if integration:
        query = query.filter(SyncLog.integration == integration)
    if entity_type:
        query = query.filter(SyncLog.entity_type == entity_type)
    if status:
        query = query.filter(SyncLog.status == status)

    logs = (
        query.order_by(SyncLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": log.id,
            "integration": log.integration,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "external_id": log.external_id,
            "direction": log.direction,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Product Sync: BC → Website
# ---------------------------------------------------------------------------

@router.post("/bc/products/pull")
async def pull_products(
    full: bool = False,
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Trigger a product sync from Business Central.

    Args:
        full: If True, pull all items (not just changes since last sync)
    """
    try:
        stats = await bc_sync_service.sync_products(db, full=full)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BC product sync failed: {e}")

    return {"message": "Product sync complete", **stats}


# ---------------------------------------------------------------------------
# Inventory Sync: BC → Website
# ---------------------------------------------------------------------------

@router.post("/bc/inventory/pull")
async def pull_inventory(
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Trigger an inventory sync from Business Central."""
    try:
        stats = await bc_sync_service.sync_inventory(db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BC inventory sync failed: {e}")

    return {"message": "Inventory sync complete", **stats}


# ---------------------------------------------------------------------------
# Customer Sync: Website → BC
# ---------------------------------------------------------------------------

@router.post("/bc/customers/push")
async def push_all_customers(
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Push all unsynced customers to Business Central."""
    try:
        stats = await bc_sync_service.push_all_unsynced_customers(db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BC customer push failed: {e}")

    return {"message": "Customer push complete", **stats}


@router.post("/bc/customers/{user_id}/push")
async def push_customer(
    user_id: str,
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Push a specific customer to Business Central."""
    user = db.query(StoreUser).filter(StoreUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        bc_id = await bc_sync_service.push_customer(db, user)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BC customer push failed: {e}")

    if not bc_id:
        raise HTTPException(status_code=502, detail="Customer sync to BC failed")

    return {
        "message": "Customer pushed to BC",
        "user_id": user.id,
        "bc_customer_id": bc_id,
    }


# ---------------------------------------------------------------------------
# Order Sync: Website → BC
# ---------------------------------------------------------------------------

@router.post("/bc/orders/{order_id}/push")
async def push_order(
    order_id: str,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Push a confirmed order to Business Central as a Sales Order."""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.store_user),
            joinedload(Order.items),
        )
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status not in ("confirmed", "mockup_pending", "mockup_approved", "in_production"):
        raise HTTPException(
            status_code=400,
            detail=f"Order status '{order.status}' is not eligible for BC sync",
        )

    try:
        bc_so_id = await bc_sync_service.push_order(db, order)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BC order push failed: {e}")

    if not bc_so_id:
        raise HTTPException(status_code=502, detail="Order sync to BC failed")

    return {
        "message": "Order pushed to BC",
        "order_id": order.id,
        "order_number": order.order_number,
        "bc_sales_order_id": bc_so_id,
    }


@router.get("/bc/orders/{order_id}/status")
async def get_order_sync_status(
    order_id: str,
    admin=Depends(require_store_role("admin", "purchasing_manager")),
    db: Session = Depends(get_db),
):
    """Check BC sync status for a specific order."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "bc_sales_order_id": order.bc_sales_order_id,
        "bc_sync_status": order.bc_sync_status,
        "bc_synced_at": order.bc_synced_at.isoformat() if order.bc_synced_at else None,
        "bc_invoice_id": order.bc_invoice_id,
    }


# ---------------------------------------------------------------------------
# Invoice Sync: BC → Website
# ---------------------------------------------------------------------------

@router.post("/bc/invoices/pull")
async def pull_invoices(
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Pull recent invoices from Business Central."""
    try:
        stats = await bc_sync_service.sync_invoices(db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"BC invoice sync failed: {e}")

    return {"message": "Invoice sync complete", **stats}


# ---------------------------------------------------------------------------
# Pipedrive: Contact Sync (Website → Pipedrive)
# ---------------------------------------------------------------------------

@router.post("/pipedrive/persons/push")
async def push_all_pipedrive_contacts(
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Push all unsynced customers to Pipedrive."""
    try:
        stats = pipedrive_sync_service.push_all_unsynced_contacts(db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pipedrive contact push failed: {e}")

    return {"message": "Pipedrive contact push complete", **stats}


@router.post("/pipedrive/persons/{user_id}/push")
async def push_pipedrive_contact(
    user_id: str,
    admin=Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Push a specific customer to Pipedrive."""
    user = db.query(StoreUser).filter(StoreUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        person_id = pipedrive_sync_service.push_contact(db, user)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pipedrive contact push failed: {e}")

    if not person_id:
        raise HTTPException(status_code=502, detail="Contact sync to Pipedrive failed")

    return {
        "message": "Contact pushed to Pipedrive",
        "user_id": user.id,
        "pipedrive_person_id": person_id,
    }
