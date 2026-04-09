"""Server-side analytics service for GA4 Measurement Protocol and Google Ads conversions.

Client-side gtag.js handles most e-commerce events (view_item, add_to_cart, begin_checkout).
This service handles server-side events that must be reliable:
  - purchase (order confirmed — bypasses ad blockers)
  - refund  (only backend knows)
  - Google Ads click conversion upload (GCLID-based)
"""

import logging
from typing import Optional
import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

GA4_MP_URL = "https://www.google-analytics.com/mp/collect"
GOOGLE_ADS_UPLOAD_URL = (
    "https://googleads.googleapis.com/v17/customers/{customer_id}/offlineUserDataJobs"
)


def _ga4_enabled() -> bool:
    s = get_settings()
    return bool(s.ga4_measurement_id and s.ga4_api_secret)


# ---------------------------------------------------------------------------
# GA4 Measurement Protocol
# ---------------------------------------------------------------------------

def track_purchase_server(
    client_id: str,
    order_id: str,
    order_number: str,
    items: list[dict],
    total_cents: int,
    tax_cents: int = 0,
    shipping_cents: int = 0,
    currency: str = "USD",
):
    """Send a purchase event to GA4 via Measurement Protocol.

    Args:
        client_id: GA4 client ID (from _ga cookie or generated)
        order_id: Internal order UUID
        order_number: Human-readable order number (KC-2026-XXXXX)
        items: List of dicts with item_id, item_name, quantity, price (dollars)
        total_cents: Order total in cents
        tax_cents: Tax in cents
        shipping_cents: Shipping in cents
    """
    if not _ga4_enabled():
        return

    settings = get_settings()

    ga4_items = [
        {
            "item_id": item.get("item_id", item.get("product_id", "")),
            "item_name": item.get("item_name", item.get("product_name", "")),
            "quantity": item.get("quantity", 1),
            "price": item.get("price", 0),
        }
        for item in items
    ]

    payload = {
        "client_id": client_id,
        "events": [
            {
                "name": "purchase",
                "params": {
                    "transaction_id": order_number,
                    "value": total_cents / 100.0,
                    "currency": currency,
                    "tax": tax_cents / 100.0,
                    "shipping": shipping_cents / 100.0,
                    "items": ga4_items,
                },
            }
        ],
    }

    try:
        resp = httpx.post(
            GA4_MP_URL,
            params={
                "measurement_id": settings.ga4_measurement_id,
                "api_secret": settings.ga4_api_secret,
            },
            json=payload,
            timeout=10,
        )
        if resp.status_code != 204:
            logger.warning("GA4 MP purchase returned %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("GA4 MP purchase event failed: %s", e)


def track_refund_server(
    client_id: str,
    order_number: str,
    refund_cents: int,
    currency: str = "USD",
):
    """Send a refund event to GA4 via Measurement Protocol."""
    if not _ga4_enabled():
        return

    settings = get_settings()

    payload = {
        "client_id": client_id,
        "events": [
            {
                "name": "refund",
                "params": {
                    "transaction_id": order_number,
                    "value": refund_cents / 100.0,
                    "currency": currency,
                },
            }
        ],
    }

    try:
        resp = httpx.post(
            GA4_MP_URL,
            params={
                "measurement_id": settings.ga4_measurement_id,
                "api_secret": settings.ga4_api_secret,
            },
            json=payload,
            timeout=10,
        )
        if resp.status_code != 204:
            logger.warning("GA4 MP refund returned %s: %s", resp.status_code, resp.text)
    except Exception as e:
        logger.error("GA4 MP refund event failed: %s", e)


# ---------------------------------------------------------------------------
# Google Ads Offline Conversion Upload
# ---------------------------------------------------------------------------

def track_conversion_google_ads(
    gclid: str,
    order_number: str,
    total_cents: int,
    currency: str = "USD",
):
    """Upload a click conversion to Google Ads using GCLID.

    The GCLID is captured from URL params on the landing page, stored in
    a cookie/session, and passed to the backend at checkout time.

    Note: Full implementation requires Google Ads API OAuth2 service account.
    This is a placeholder structure — the actual auth flow uses google-ads-python
    or a service account JWT. For now we log the conversion for manual upload
    or future automation.
    """
    settings = get_settings()
    if not settings.google_ads_customer_id or not settings.google_ads_conversion_action_id:
        return

    if not gclid:
        return

    # Log for now — full Google Ads API integration requires OAuth2 service account
    logger.info(
        "Google Ads conversion: gclid=%s, order=%s, value=$%.2f, action=%s",
        gclid,
        order_number,
        total_cents / 100.0,
        settings.google_ads_conversion_action_id,
    )
