"""ShipStation shipping integration service.

Handles order creation in ShipStation and tracking lookups.
ShipStation uses Basic Auth (API Key:Secret base64-encoded).

API Docs: https://www.shipstation.com/docs/api/
"""

import base64
import logging
from typing import Any, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_BASE_URL = "https://ssapi.shipstation.com"


def _get_auth_header() -> str:
    """Build Basic Auth header from API key + secret."""
    if not settings.shipstation_api_key or not settings.shipstation_api_secret:
        raise ValueError("ShipStation API credentials not configured")
    creds = f"{settings.shipstation_api_key}:{settings.shipstation_api_secret}"
    encoded = base64.b64encode(creds.encode()).decode()
    return f"Basic {encoded}"


def _headers() -> dict[str, str]:
    return {
        "Authorization": _get_auth_header(),
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def create_order(
    order_number: str,
    order_date: str,
    ship_to: dict[str, str],
    items: list[dict[str, Any]],
    order_key: Optional[str] = None,
    carrier_code: Optional[str] = None,
    service_code: Optional[str] = None,
    internal_notes: Optional[str] = None,
    customer_email: Optional[str] = None,
) -> dict[str, Any]:
    """Create an order in ShipStation.

    Args:
        order_number: Our order number (e.g. KC-2026-00001)
        order_date: ISO date string
        ship_to: {name, street1, street2, city, state, postalCode, country, phone}
        items: [{name, quantity, unitPrice, sku}]
        order_key: Unique key (defaults to order_number)
        carrier_code: e.g. "ups", "fedex", "stamps_com"
        service_code: e.g. "ups_ground", "fedex_home_delivery"
        internal_notes: Internal notes for warehouse
        customer_email: For ShipStation notifications

    Returns:
        ShipStation order dict with orderId
    """
    payload: dict[str, Any] = {
        "orderNumber": order_number,
        "orderKey": order_key or order_number,
        "orderDate": order_date,
        "orderStatus": "awaiting_shipment",
        "shipTo": {
            "name": ship_to.get("name", ""),
            "street1": ship_to.get("street1", ""),
            "street2": ship_to.get("street2", ""),
            "city": ship_to.get("city", ""),
            "state": ship_to.get("state", ""),
            "postalCode": ship_to.get("postalCode", ""),
            "country": ship_to.get("country", "US"),
            "phone": ship_to.get("phone", ""),
        },
        "items": [
            {
                "name": item.get("name", "Hat"),
                "quantity": item.get("quantity", 1),
                "unitPrice": item.get("unitPrice", 0),
                "sku": item.get("sku", ""),
            }
            for item in items
        ],
    }

    if carrier_code:
        payload["carrierCode"] = carrier_code
    if service_code:
        payload["serviceCode"] = service_code
    if internal_notes:
        payload["internalNotes"] = internal_notes
    if customer_email:
        payload["customerEmail"] = customer_email

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            f"{_BASE_URL}/orders/createorder",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()

    return resp.json()


def get_order(order_number: str) -> Optional[dict[str, Any]]:
    """Look up a ShipStation order by our order number."""
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{_BASE_URL}/orders",
            headers=_headers(),
            params={"orderNumber": order_number},
        )
        resp.raise_for_status()

    data = resp.json()
    orders = data.get("orders", [])
    return orders[0] if orders else None


# ---------------------------------------------------------------------------
# Shipments / Tracking
# ---------------------------------------------------------------------------

def get_tracking(order_number: str) -> Optional[dict[str, Any]]:
    """Get tracking info for an order from ShipStation.

    Returns:
        {tracking_number, tracking_url, carrier, ship_date, delivery_date, status}
        or None if no shipment found.
    """
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{_BASE_URL}/shipments",
            headers=_headers(),
            params={"orderNumber": order_number},
        )
        resp.raise_for_status()

    data = resp.json()
    shipments = data.get("shipments", [])

    if not shipments:
        return None

    shipment = shipments[0]
    return {
        "tracking_number": shipment.get("trackingNumber", ""),
        "tracking_url": _build_tracking_url(
            shipment.get("carrierCode", ""),
            shipment.get("trackingNumber", ""),
        ),
        "carrier": shipment.get("carrierCode", ""),
        "service": shipment.get("serviceCode", ""),
        "ship_date": shipment.get("shipDate"),
        "delivery_date": shipment.get("deliveryDate"),
        "shipstation_shipment_id": shipment.get("shipmentId"),
    }


def _build_tracking_url(carrier: str, tracking_number: str) -> str:
    """Build a tracking URL from carrier code and tracking number."""
    if not tracking_number:
        return ""
    carrier_lower = carrier.lower()
    if "ups" in carrier_lower:
        return f"https://www.ups.com/track?tracknum={tracking_number}"
    if "fedex" in carrier_lower:
        return f"https://www.fedex.com/fedextrack/?trknbr={tracking_number}"
    if "usps" in carrier_lower or "stamps" in carrier_lower:
        return f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"
    # Generic fallback
    return f"https://parcelsapp.com/en/tracking/{tracking_number}"


# ---------------------------------------------------------------------------
# Webhook Resource Fetch
# ---------------------------------------------------------------------------

def fetch_webhook_resource(resource_url: str) -> dict[str, Any]:
    """Fetch the actual data from a ShipStation webhook resource_url.

    ShipStation webhooks only contain a resource_url — you must GET it
    to retrieve the actual shipment/order data.
    """
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(resource_url, headers=_headers())
        resp.raise_for_status()

    return resp.json()
