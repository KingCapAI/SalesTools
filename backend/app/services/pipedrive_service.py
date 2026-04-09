"""Pipedrive CRM integration service.

Handles person, organization, deal, and note CRUD via the Pipedrive REST API v1.

API Docs: https://developers.pipedrive.com/docs/api/v1
"""

import logging
from typing import Any, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_BASE_URL = "https://api.pipedrive.com/v1"


def _params(**extra: Any) -> dict[str, Any]:
    """Base query params with API token."""
    return {"api_token": settings.pipedrive_api_token, **extra}


def _check_configured():
    if not settings.pipedrive_api_token:
        raise ValueError("Pipedrive API token not configured")


# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------

def create_person(
    first_name: str,
    last_name: str,
    email: str,
    phone: Optional[str] = None,
    org_id: Optional[int] = None,
    custom_fields: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a person in Pipedrive."""
    _check_configured()

    payload: dict[str, Any] = {
        "name": f"{first_name} {last_name}".strip(),
        "first_name": first_name,
        "last_name": last_name,
        "email": [{"value": email, "primary": True}],
    }
    if phone:
        payload["phone"] = [{"value": phone, "primary": True}]
    if org_id:
        payload["org_id"] = org_id
    if custom_fields:
        payload.update(custom_fields)

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            f"{_BASE_URL}/persons",
            params=_params(),
            json=payload,
        )
        resp.raise_for_status()

    data = resp.json()
    return data.get("data", {})


def update_person(
    person_id: int,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Update a person in Pipedrive."""
    _check_configured()

    with httpx.Client(timeout=15.0) as client:
        resp = client.put(
            f"{_BASE_URL}/persons/{person_id}",
            params=_params(),
            json=fields,
        )
        resp.raise_for_status()

    return resp.json().get("data", {})


def find_person_by_email(email: str) -> Optional[dict[str, Any]]:
    """Search for a person by email. Returns the first match or None."""
    _check_configured()

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{_BASE_URL}/persons/search",
            params=_params(term=email, fields="email", limit=1),
        )
        resp.raise_for_status()

    items = resp.json().get("data", {}).get("items", [])
    if items:
        return items[0].get("item", {})
    return None


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

def create_organization(
    name: str,
    address: Optional[str] = None,
) -> dict[str, Any]:
    """Create an organization in Pipedrive."""
    _check_configured()

    payload: dict[str, Any] = {"name": name}
    if address:
        payload["address"] = address

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            f"{_BASE_URL}/organizations",
            params=_params(),
            json=payload,
        )
        resp.raise_for_status()

    return resp.json().get("data", {})


def find_organization_by_name(name: str) -> Optional[dict[str, Any]]:
    """Search for an organization by name."""
    _check_configured()

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(
            f"{_BASE_URL}/organizations/search",
            params=_params(term=name, limit=1),
        )
        resp.raise_for_status()

    items = resp.json().get("data", {}).get("items", [])
    if items:
        return items[0].get("item", {})
    return None


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------

def create_deal(
    title: str,
    person_id: Optional[int] = None,
    org_id: Optional[int] = None,
    value: Optional[float] = None,
    currency: str = "USD",
    stage_id: Optional[int] = None,
    custom_fields: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Create a deal in Pipedrive."""
    _check_configured()

    payload: dict[str, Any] = {"title": title, "currency": currency}
    if person_id:
        payload["person_id"] = person_id
    if org_id:
        payload["org_id"] = org_id
    if value is not None:
        payload["value"] = value
    if stage_id:
        payload["stage_id"] = stage_id
    if custom_fields:
        payload.update(custom_fields)

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            f"{_BASE_URL}/deals",
            params=_params(),
            json=payload,
        )
        resp.raise_for_status()

    return resp.json().get("data", {})


def update_deal(
    deal_id: int,
    fields: dict[str, Any],
) -> dict[str, Any]:
    """Update a deal in Pipedrive."""
    _check_configured()

    with httpx.Client(timeout=15.0) as client:
        resp = client.put(
            f"{_BASE_URL}/deals/{deal_id}",
            params=_params(),
            json=fields,
        )
        resp.raise_for_status()

    return resp.json().get("data", {})


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

def add_note(
    content: str,
    person_id: Optional[int] = None,
    org_id: Optional[int] = None,
    deal_id: Optional[int] = None,
) -> dict[str, Any]:
    """Add a note to a person, org, or deal in Pipedrive."""
    _check_configured()

    payload: dict[str, Any] = {"content": content}
    if person_id:
        payload["person_id"] = person_id
    if org_id:
        payload["org_id"] = org_id
    if deal_id:
        payload["deal_id"] = deal_id

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            f"{_BASE_URL}/notes",
            params=_params(),
            json=payload,
        )
        resp.raise_for_status()

    return resp.json().get("data", {})
