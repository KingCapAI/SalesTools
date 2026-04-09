"""Inbound webhook handlers for external integrations."""

import hmac
import hashlib
import logging
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import joinedload

from ..database import get_db
from ..config import get_settings
from ..models.store_order import Order, OrderStatusHistory
from ..models.store_user import StoreUser
from ..services import pipedrive_sync_service
from ..services.shipstation_service import fetch_webhook_resource
from ..services.email_service import send_order_status_update

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ---------------------------------------------------------------------------
# Pipedrive Webhooks
# ---------------------------------------------------------------------------

@router.post("/pipedrive")
async def pipedrive_webhook(request: Request):
    """Handle inbound Pipedrive webhooks."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if settings.pipedrive_webhook_secret:
        signature = request.headers.get("x-pipedrive-signature", "")
        body = await request.body()
        expected = hmac.new(
            settings.pipedrive_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")

    event = payload.get("event", "")
    logger.info("Pipedrive webhook received: %s", event)

    db = next(get_db())
    try:
        if event in ("updated.person", "added.person"):
            user_id = pipedrive_sync_service.handle_person_webhook(db, payload)
            return {"status": "ok", "user_id": user_id}

        return {"status": "ok", "event": event, "action": "ignored"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# ShipStation Webhooks
# ---------------------------------------------------------------------------

@router.post("/shipstation")
async def shipstation_webhook(request: Request):
    """Handle ShipStation shipping status webhooks.

    ShipStation POSTs a resource_url; we fetch it to get shipment details,
    then update the order's tracking info and status.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    resource_url = payload.get("resource_url", "")
    resource_type = payload.get("resource_type", "")

    logger.info("ShipStation webhook: %s — %s", resource_type, resource_url)

    if not resource_url:
        return {"status": "ok", "action": "no_resource_url"}

    # Fetch the actual shipment data from ShipStation
    try:
        data = fetch_webhook_resource(resource_url)
    except Exception as e:
        logger.error("Failed to fetch ShipStation resource: %s", e)
        return {"status": "error", "detail": "Failed to fetch resource"}

    # ShipStation SHIP_NOTIFY sends a list of shipments
    shipments = data.get("shipments", [data] if "orderNumber" in data else [])

    db = next(get_db())
    try:
        for shipment in shipments:
            order_number = shipment.get("orderNumber", "")
            if not order_number:
                continue

            order = (
                db.query(Order)
                .options(joinedload(Order.store_user))
                .filter(Order.order_number == order_number)
                .first()
            )
            if not order:
                logger.warning("ShipStation: order %s not found", order_number)
                continue

            tracking_number = shipment.get("trackingNumber", "")
            carrier = shipment.get("carrierCode", "")

            # Update tracking info
            if tracking_number:
                order.tracking_number = tracking_number
                order.tracking_url = _build_tracking_url(carrier, tracking_number)

            # Determine new status
            void_date = shipment.get("voidDate")
            if void_date:
                # Shipment was voided — don't update status
                continue

            ship_date = shipment.get("shipDate")
            if ship_date and order.status not in ("shipped", "delivered", "cancelled", "refunded"):
                from datetime import datetime
                order.status = "shipped"
                order.actual_ship_date = datetime.utcnow()

                history = OrderStatusHistory(
                    order_id=order.id,
                    status="shipped",
                    note=f"Shipped via {carrier.upper()} — {tracking_number}",
                )
                db.add(history)

                # Send shipping email to customer
                if order.store_user and order.store_user.email:
                    send_order_status_update(
                        to_email=order.store_user.email,
                        order_number=order.order_number,
                        new_status="shipped",
                        tracking_number=tracking_number,
                        tracking_url=order.tracking_url,
                    )

        db.commit()
    finally:
        db.close()

    return {"status": "ok", "shipments_processed": len(shipments)}


def _build_tracking_url(carrier: str, tracking_number: str) -> str:
    """Build a tracking URL from carrier code and tracking number."""
    if not tracking_number:
        return ""
    c = carrier.lower()
    if "ups" in c:
        return f"https://www.ups.com/track?tracknum={tracking_number}"
    if "fedex" in c:
        return f"https://www.fedex.com/fedextrack/?trknbr={tracking_number}"
    if "usps" in c or "stamps" in c:
        return f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"
    return f"https://parcelsapp.com/en/tracking/{tracking_number}"


# ---------------------------------------------------------------------------
# Business Central Webhooks (optional real-time sync)
# ---------------------------------------------------------------------------

@router.post("/bc")
async def bc_webhook(request: Request):
    """Handle Business Central change notifications."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info("BC webhook received: %s", payload.get("type", "unknown"))
    return {"status": "ok"}
