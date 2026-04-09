"""Business Central (Dynamics 365) integration service.

Authenticates via OAuth2 client_credentials and interacts with the
BC OData v4 REST API for products, customers, orders, and inventory.

Source of truth mapping:
  - Products/inventory/pricing: BC → Website
  - Customers: Website → BC (on approval/creation)
  - Sales Orders: Website → BC (on confirmation)
  - Invoices: BC → Website (PM posts in BC)
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level token cache
_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0}

# Hat volume/weight estimates (per unit, including packaging)
CBM_PER_HAT = 0.005
KG_PER_HAT = 0.12


# ---------------------------------------------------------------------------
# Auth & HTTP helpers
# ---------------------------------------------------------------------------

async def _get_access_token() -> str:
    """Acquire or return cached OAuth2 token via client_credentials flow."""
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    if not settings.bc_tenant_id or not settings.bc_client_id:
        raise ValueError(
            "Business Central credentials not configured. "
            "Set BC_TENANT_ID, BC_CLIENT_ID, and BC_CLIENT_SECRET in .env"
        )

    token_url = (
        f"https://login.microsoftonline.com/{settings.bc_tenant_id}/oauth2/v2.0/token"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "client_id": settings.bc_client_id,
                "client_secret": settings.bc_client_secret,
                "grant_type": "client_credentials",
                "scope": "https://api.businesscentral.dynamics.com/.default",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _token_cache["access_token"]


def _base_url() -> str:
    env = settings.bc_environment or "production"
    return (
        f"https://api.businesscentral.dynamics.com/v2.0/{env}"
        f"/api/v2.0/companies({settings.bc_company_id})"
    )


async def _bc_request(
    method: str,
    path: str,
    params: Optional[dict[str, str]] = None,
    json_body: Optional[dict] = None,
    etag: Optional[str] = None,
) -> dict[str, Any]:
    """Generic HTTP helper for Business Central API calls."""
    token = await _get_access_token()
    url = f"{_base_url()}/{path}"

    headers: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if etag:
        headers["If-Match"] = etag

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method, url, headers=headers, params=params, json=json_body,
        )
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()


# ---------------------------------------------------------------------------
# Products — BC → Website
# ---------------------------------------------------------------------------

async def get_items(
    modified_since: Optional[datetime] = None,
    top: int = 500,
) -> list[dict[str, Any]]:
    """Fetch items (products) from BC, optionally filtered by lastModifiedDateTime."""
    params: dict[str, str] = {
        "$select": (
            "id,number,displayName,unitPrice,inventory,blocked,"
            "itemCategoryCode,type,lastModifiedDateTime"
        ),
        "$top": str(top),
        "$orderby": "lastModifiedDateTime asc",
    }
    if modified_since:
        ts = modified_since.strftime("%Y-%m-%dT%H:%M:%SZ")
        params["$filter"] = f"lastModifiedDateTime gt {ts} and type eq 'Inventory'"
    else:
        params["$filter"] = "type eq 'Inventory'"

    data = await _bc_request("GET", "items", params=params)
    return data.get("value", [])


async def get_item(item_id: str) -> dict[str, Any]:
    """Fetch a single item by its BC id."""
    return await _bc_request("GET", f"items({item_id})")


async def get_item_categories() -> list[dict[str, Any]]:
    """Fetch item categories from BC."""
    data = await _bc_request(
        "GET", "itemCategories",
        params={"$select": "id,code,displayName"},
    )
    return data.get("value", [])


async def get_item_inventory(top: int = 1000) -> list[dict[str, Any]]:
    """Fetch lightweight inventory data (item number + stock qty)."""
    data = await _bc_request(
        "GET", "items",
        params={
            "$select": "number,inventory",
            "$filter": "type eq 'Inventory'",
            "$top": str(top),
        },
    )
    return data.get("value", [])


# ---------------------------------------------------------------------------
# Customers — Website → BC
# ---------------------------------------------------------------------------

async def create_customer(
    name: str,
    email: str,
    phone: Optional[str] = None,
    address_line1: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    country: str = "US",
    customer_price_group: Optional[str] = None,
) -> dict[str, Any]:
    """Create a customer record in BC. Returns the created customer dict."""
    payload: dict[str, Any] = {
        "displayName": name,
        "email": email,
        "type": "Company",
    }
    if phone:
        payload["phoneNumber"] = phone
    if address_line1:
        payload["addressLine1"] = address_line1
    if city:
        payload["city"] = city
    if state:
        payload["state"] = state
    if postal_code:
        payload["postalCode"] = postal_code
    if country:
        payload["country"] = country
    if customer_price_group:
        payload["customerPriceGroup"] = customer_price_group

    return await _bc_request("POST", "customers", json_body=payload)


async def update_customer(
    bc_customer_id: str,
    fields: dict[str, Any],
    etag: str = "*",
) -> dict[str, Any]:
    """Patch a customer record in BC."""
    return await _bc_request(
        "PATCH", f"customers({bc_customer_id})",
        json_body=fields, etag=etag,
    )


async def get_customer_by_email(email: str) -> Optional[dict[str, Any]]:
    """Look up a BC customer by email. Returns None if not found."""
    data = await _bc_request(
        "GET", "customers",
        params={"$filter": f"email eq '{email}'", "$top": "1"},
    )
    values = data.get("value", [])
    return values[0] if values else None


# ---------------------------------------------------------------------------
# Sales Orders — Website → BC
# ---------------------------------------------------------------------------

async def create_sales_order(
    customer_number: str,
    order_number: str,
    order_date: Optional[str] = None,
) -> dict[str, Any]:
    """Create a sales order header in BC."""
    payload: dict[str, Any] = {
        "customerNumber": customer_number,
        "externalDocumentNumber": order_number,
    }
    if order_date:
        payload["orderDate"] = order_date

    return await _bc_request("POST", "salesOrders", json_body=payload)


async def add_sales_order_line(
    sales_order_id: str,
    item_number: str,
    quantity: int,
    unit_price_dollars: float,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """Add a line item to a BC sales order."""
    payload: dict[str, Any] = {
        "lineObjectNumber": item_number,
        "lineType": "Item",
        "quantity": quantity,
        "unitPrice": unit_price_dollars,
    }
    if description:
        payload["description"] = description

    return await _bc_request(
        "POST", f"salesOrders({sales_order_id})/salesOrderLines",
        json_body=payload,
    )


async def cancel_sales_order(
    sales_order_id: str,
    etag: str = "*",
) -> dict[str, Any]:
    """Cancel (delete) a sales order in BC."""
    return await _bc_request(
        "DELETE", f"salesOrders({sales_order_id})", etag=etag,
    )


async def get_open_sales_orders() -> list[dict[str, Any]]:
    """Fetch open sales orders from BC."""
    data = await _bc_request(
        "GET", "salesOrders",
        params={
            "$filter": "status eq 'Open'",
            "$select": (
                "id,number,orderDate,requestedDeliveryDate,"
                "totalAmountIncludingTax,status,customerNumber,"
                "customerName,currencyCode,externalDocumentNumber"
            ),
            "$orderby": "requestedDeliveryDate asc",
            "$top": "500",
        },
    )
    return data.get("value", [])


async def get_sales_order_lines(order_id: str) -> list[dict[str, Any]]:
    """Fetch line items for a specific sales order."""
    data = await _bc_request(
        "GET", f"salesOrders({order_id})/salesOrderLines",
        params={
            "$select": (
                "id,lineObjectNumber,description,quantity,"
                "unitPrice,totalAmount,unitOfMeasureCode"
            ),
        },
    )
    return data.get("value", [])


# ---------------------------------------------------------------------------
# Invoices — BC → Website
# ---------------------------------------------------------------------------

async def get_sales_invoices(
    modified_since: Optional[datetime] = None,
    top: int = 100,
) -> list[dict[str, Any]]:
    """Fetch sales invoices from BC."""
    params: dict[str, str] = {
        "$select": (
            "id,number,invoiceDate,dueDate,totalAmountIncludingTax,"
            "status,customerNumber,customerName,externalDocumentNumber"
        ),
        "$orderby": "invoiceDate desc",
        "$top": str(top),
    }
    if modified_since:
        ts = modified_since.strftime("%Y-%m-%dT%H:%M:%SZ")
        params["$filter"] = f"lastModifiedDateTime gt {ts}"

    data = await _bc_request("GET", "salesInvoices", params=params)
    return data.get("value", [])


# ---------------------------------------------------------------------------
# Credit Memos — Website → BC (for returns/refunds)
# ---------------------------------------------------------------------------

async def create_credit_memo(
    customer_number: str,
    external_doc_number: str,
) -> dict[str, Any]:
    """Create a sales credit memo in BC."""
    return await _bc_request(
        "POST", "salesCreditMemos",
        json_body={
            "customerNumber": customer_number,
            "externalDocumentNumber": external_doc_number,
        },
    )


async def add_credit_memo_line(
    credit_memo_id: str,
    item_number: str,
    quantity: int,
    unit_price_dollars: float,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """Add a line item to a BC credit memo."""
    payload: dict[str, Any] = {
        "lineObjectNumber": item_number,
        "lineType": "Item",
        "quantity": quantity,
        "unitPrice": unit_price_dollars,
    }
    if description:
        payload["description"] = description

    return await _bc_request(
        "POST", f"salesCreditMemos({credit_memo_id})/salesCreditMemoLines",
        json_body=payload,
    )


# ---------------------------------------------------------------------------
# Shipping agent helpers (existing functionality)
# ---------------------------------------------------------------------------

async def get_pending_overseas_orders() -> list[dict[str, Any]]:
    """Fetch open sales orders and enrich with volume/weight estimates."""
    orders = await get_open_sales_orders()
    enriched = []

    for order in orders:
        try:
            lines = await get_sales_order_lines(order["id"])
        except Exception as e:
            logger.warning("Failed to fetch lines for order %s: %s", order.get("number"), e)
            lines = []

        total_qty = sum(int(line.get("quantity", 0)) for line in lines)
        est_volume = round(total_qty * CBM_PER_HAT, 3)
        est_weight = round(total_qty * KG_PER_HAT, 2)

        enriched.append({
            "bc_order_id": order.get("id"),
            "bc_order_number": order.get("number", ""),
            "customer_name": order.get("customerName", ""),
            "customer_number": order.get("customerNumber", ""),
            "order_date": order.get("orderDate"),
            "requested_delivery_date": order.get("requestedDeliveryDate"),
            "total_amount": order.get("totalAmountIncludingTax"),
            "currency": order.get("currencyCode", "USD"),
            "total_quantity": total_qty,
            "estimated_volume_cbm": est_volume,
            "estimated_weight_kg": est_weight,
            "line_items": [
                {
                    "item_number": l.get("lineObjectNumber", ""),
                    "description": l.get("description", ""),
                    "quantity": l.get("quantity", 0),
                    "unit_price": l.get("unitPrice", 0),
                    "total": l.get("totalAmount", 0),
                }
                for l in lines
            ],
        })

    return enriched


def generate_mock_orders() -> list[dict[str, Any]]:
    """Generate mock overseas orders for testing without BC credentials."""
    from datetime import timedelta

    today = datetime.utcnow()

    return [
        {
            "bc_order_id": "mock-001",
            "bc_order_number": "SO-2026-0451",
            "customer_name": "Ace Golf Club",
            "customer_number": "C-10045",
            "order_date": (today - timedelta(days=5)).isoformat(),
            "requested_delivery_date": (today + timedelta(days=45)).isoformat(),
            "total_amount": 12500.00,
            "currency": "USD",
            "total_quantity": 500,
            "estimated_volume_cbm": 2.5,
            "estimated_weight_kg": 60.0,
            "line_items": [
                {"item_number": "100", "description": "Origin Cap - Navy", "quantity": 300, "unit_price": 18.50, "total": 5550.00},
                {"item_number": "230", "description": "Buddy Cap - Black", "quantity": 200, "unit_price": 34.75, "total": 6950.00},
            ],
        },
        {
            "bc_order_id": "mock-002",
            "bc_order_number": "SO-2026-0452",
            "customer_name": "Summit Brewing Co",
            "customer_number": "C-10078",
            "order_date": (today - timedelta(days=3)).isoformat(),
            "requested_delivery_date": (today + timedelta(days=30)).isoformat(),
            "total_amount": 8200.00,
            "currency": "USD",
            "total_quantity": 1200,
            "estimated_volume_cbm": 6.0,
            "estimated_weight_kg": 144.0,
            "line_items": [
                {"item_number": "150-FT", "description": "Ace Foam Trucker - White/Black", "quantity": 1200, "unit_price": 6.83, "total": 8200.00},
            ],
        },
    ]
