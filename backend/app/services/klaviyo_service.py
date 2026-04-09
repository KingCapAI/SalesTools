"""Klaviyo email marketing integration service.

Handles:
  - Profile creation/update (on registration, login, approval)
  - Event tracking (orders, cart, samples, contact form, etc.)
  - List management (add/remove from DTC, wholesale, golf lists)

Uses Klaviyo API v2024-10-15 (revision header).
"""

import logging
from typing import Optional
import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

KLAVIYO_BASE = "https://a.klaviyo.com/api"
KLAVIYO_REVISION = "2024-10-15"


def _headers() -> dict:
    settings = get_settings()
    return {
        "Authorization": f"Klaviyo-API-Key {settings.klaviyo_private_key}",
        "revision": KLAVIYO_REVISION,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _enabled() -> bool:
    settings = get_settings()
    return bool(settings.klaviyo_private_key)


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

def create_or_update_profile(
    email: str,
    *,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    properties: Optional[dict] = None,
) -> Optional[str]:
    """Create or update a Klaviyo profile. Returns profile ID or None."""
    if not _enabled():
        return None

    attrs: dict = {"email": email}
    if first_name:
        attrs["first_name"] = first_name
    if last_name:
        attrs["last_name"] = last_name
    if phone:
        attrs["phone_number"] = phone
    if properties:
        attrs["properties"] = properties

    payload = {
        "data": {
            "type": "profile",
            "attributes": attrs,
        }
    }

    try:
        resp = httpx.post(
            f"{KLAVIYO_BASE}/profile-import",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        profile_id = data.get("data", {}).get("id")
        return profile_id
    except Exception as e:
        logger.error("Klaviyo create_or_update_profile failed for %s: %s", email, e)
        return None


# ---------------------------------------------------------------------------
# Event Tracking
# ---------------------------------------------------------------------------

def track_event(
    event_name: str,
    email: str,
    properties: Optional[dict] = None,
    value: Optional[float] = None,
    unique_id: Optional[str] = None,
) -> bool:
    """Track a Klaviyo event (metric) for a profile.

    Args:
        event_name: e.g. "Placed Order", "Added to Cart"
        email: Customer email to associate with
        properties: Event-specific data
        value: Monetary value (dollars, not cents)
        unique_id: Deduplication key (e.g. order_id)

    Returns True on success.
    """
    if not _enabled():
        return False

    profile = {"data": {"type": "profile", "attributes": {"email": email}}}
    metric = {"data": {"type": "metric", "attributes": {"name": event_name}}}

    event_attrs: dict = {
        "profile": profile,
        "metric": metric,
        "properties": properties or {},
    }
    if value is not None:
        event_attrs["value"] = value
    if unique_id:
        event_attrs["unique_id"] = unique_id

    payload = {
        "data": {
            "type": "event",
            "attributes": event_attrs,
        }
    }

    try:
        resp = httpx.post(
            f"{KLAVIYO_BASE}/events",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Klaviyo track_event '%s' failed for %s: %s", event_name, email, e)
        return False


# ---------------------------------------------------------------------------
# List Management
# ---------------------------------------------------------------------------

def add_to_list(list_id: str, email: str) -> bool:
    """Add a profile to a Klaviyo list by email."""
    if not _enabled() or not list_id:
        return False

    payload = {
        "data": [
            {
                "type": "profile",
                "attributes": {"email": email},
            }
        ]
    }

    try:
        resp = httpx.post(
            f"{KLAVIYO_BASE}/lists/{list_id}/relationships/profiles",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Klaviyo add_to_list %s failed for %s: %s", list_id, email, e)
        return False


def remove_from_list(list_id: str, email: str) -> bool:
    """Remove a profile from a Klaviyo list."""
    if not _enabled() or not list_id:
        return False

    # First we need the profile ID
    profile_id = _get_profile_id_by_email(email)
    if not profile_id:
        return False

    payload = {
        "data": [
            {"type": "profile", "id": profile_id}
        ]
    }

    try:
        resp = httpx.request(
            "DELETE",
            f"{KLAVIYO_BASE}/lists/{list_id}/relationships/profiles",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Klaviyo remove_from_list %s failed for %s: %s", list_id, email, e)
        return False


def _get_profile_id_by_email(email: str) -> Optional[str]:
    """Look up a Klaviyo profile ID by email."""
    try:
        resp = httpx.get(
            f"{KLAVIYO_BASE}/profiles",
            headers=_headers(),
            params={"filter": f'equals(email,"{email}")'},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            return data[0].get("id")
        return None
    except Exception as e:
        logger.error("Klaviyo profile lookup failed for %s: %s", email, e)
        return None


# ---------------------------------------------------------------------------
# High-Level Helpers (called from routers/services)
# ---------------------------------------------------------------------------

def track_account_created(email: str, first_name: str, account_type: str, source: str = "website"):
    """Track account creation event."""
    create_or_update_profile(email, first_name=first_name, properties={
        "account_type": account_type,
        "source": source,
    })
    track_event("Account Created", email, properties={
        "account_type": account_type,
        "source": source,
    })


def track_placed_order(
    email: str,
    order_id: str,
    order_number: str,
    items: list[dict],
    total_cents: int,
):
    """Track a placed order + individual ordered product events."""
    total_dollars = total_cents / 100.0

    track_event(
        "Placed Order",
        email,
        properties={
            "order_id": order_id,
            "order_number": order_number,
            "items": items,
            "item_count": len(items),
        },
        value=total_dollars,
        unique_id=order_id,
    )

    # Also fire per-item events
    for item in items:
        track_event(
            "Ordered Product",
            email,
            properties={
                "order_id": order_id,
                "order_number": order_number,
                "product_name": item.get("product_name", ""),
                "style_number": item.get("style_number", ""),
                "quantity": item.get("quantity", 1),
                "price": item.get("price", 0),
            },
            value=item.get("price", 0),
            unique_id=f"{order_id}_{item.get('product_id', '')}",
        )

    # Update profile with lifetime stats
    create_or_update_profile(email, properties={
        "last_order_date": order_number,
    })


def track_submitted_application(email: str, application_type: str, company_name: Optional[str] = None):
    """Track wholesale/golf application submission."""
    track_event("Submitted Application", email, properties={
        "application_type": application_type,
        "company_name": company_name or "",
    })


def track_requested_sample(email: str, sample_number: str, product_name: Optional[str] = None):
    """Track sample request."""
    track_event("Requested Sample", email, properties={
        "sample_number": sample_number,
        "product_name": product_name or "",
    })


def track_contact_form(email: str, message_topic: Optional[str] = None):
    """Track contact form submission."""
    track_event("Submitted Contact Form", email, properties={
        "message_topic": message_topic or "general",
    })


def track_started_checkout(email: str, cart_total_cents: int, item_count: int):
    """Track checkout started (server-side fallback)."""
    track_event("Started Checkout", email, properties={
        "item_count": item_count,
    }, value=cart_total_cents / 100.0)
