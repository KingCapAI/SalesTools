"""EBizCharge payment gateway service.

Inline tokenization flow:
  1. Frontend embeds EBizCharge PayForm JS (using the public source key)
  2. Customer enters card details in an iframe on our checkout page
  3. EBizCharge JS returns a one-time payment_token to our frontend
  4. Frontend POSTs the token to our backend
  5. Backend calls run_sale() to charge the token server-side

API Docs: https://developer.ebizcharge.com/
"""

import hashlib
import hmac
import httpx
from typing import Optional

from ..config import get_settings

settings = get_settings()

# Base URLs by environment
_BASE_URLS = {
    "sandbox": "https://sandbox.ebizcharge.io/v2",
    "production": "https://api.ebizcharge.io/v2",
}


def _get_base_url() -> str:
    return _BASE_URLS.get(settings.ebizcharge_environment, _BASE_URLS["sandbox"])


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.ebizcharge_source_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _parse_result_code(data: dict) -> str:
    """Normalize EBizCharge result codes to approved/declined/error."""
    code = (data.get("resultCode") or data.get("result", "")).lower()
    if code in ("a", "approved", "success"):
        return "approved"
    if code in ("d", "declined"):
        return "declined"
    return "error"


def _generate_hash(amount_cents: int, order_id: str) -> str:
    """Generate HMAC-SHA256 hash for transaction verification."""
    if not settings.ebizcharge_pin:
        return ""
    message = f"{settings.ebizcharge_source_key}:{order_id}:{amount_cents}"
    return hmac.new(
        settings.ebizcharge_pin.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_callback_hash(amount_cents: int, order_id: str, received_hash: str) -> bool:
    """Verify that a callback hash matches the expected value."""
    if not settings.ebizcharge_pin:
        return True
    expected = _generate_hash(amount_cents, order_id)
    return hmac.compare_digest(expected, received_hash)


def run_sale(
    payment_token: str,
    amount_cents: int,
    order_number: str,
    customer_email: str,
    customer_name: str,
    invoice_number: Optional[str] = None,
    line_items: Optional[list[dict]] = None,
) -> dict:
    """Charge a payment token obtained from the frontend PayForm.

    Args:
        payment_token: One-time token from EBizCharge JS SDK
        amount_cents: Amount to charge in cents
        order_number: Our order number for reference
        customer_email: Customer's email
        customer_name: Customer's name
        invoice_number: Optional invoice number
        line_items: Optional list of {name, quantity, unit_price} dicts

    Returns:
        {status, transaction_id, auth_code, avs_result, cvv_result, error}
    """
    if not settings.ebizcharge_source_key:
        raise ValueError("EBizCharge source key not configured")

    amount_dollars = amount_cents / 100.0

    payload = {
        "command": "sale",
        "sourceKey": settings.ebizcharge_source_key,
        "amount": f"{amount_dollars:.2f}",
        "currency": "USD",
        "token": payment_token,
        "invoice": invoice_number or order_number,
        "orderNumber": order_number,
        "description": f"King Cap Order {order_number}",
        "customerEmail": customer_email,
        "customerName": customer_name,
    }

    if settings.ebizcharge_pin:
        payload["pin"] = settings.ebizcharge_pin

    if line_items:
        payload["lineItems"] = [
            {
                "name": item.get("name", "Hat"),
                "quantity": item.get("quantity", 1),
                "unitPrice": f"{item.get('unit_price', 0) / 100.0:.2f}",
            }
            for item in line_items
        ]

    base_url = _get_base_url()

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{base_url}/transactions",
            headers=_get_headers(),
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    status = _parse_result_code(data)

    return {
        "status": status,
        "transaction_id": data.get("transactionId") or data.get("refNum", ""),
        "auth_code": data.get("authCode", ""),
        "avs_result": data.get("avsResult", ""),
        "cvv_result": data.get("cvvResult", ""),
        "error": data.get("error", "") if status != "approved" else "",
        "raw": data,
    }


def verify_transaction(transaction_id: str) -> dict:
    """Look up a transaction by ID to verify its current state.

    Returns:
        {status, transaction_id, amount_cents, auth_code}
    """
    if not settings.ebizcharge_source_key:
        raise ValueError("EBizCharge source key not configured")

    base_url = _get_base_url()

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            f"{base_url}/transactions/{transaction_id}",
            headers=_get_headers(),
        )
        response.raise_for_status()

    data = response.json()
    amount_str = data.get("amount", "0.00")
    amount_cents = int(round(float(amount_str) * 100))

    return {
        "status": _parse_result_code(data),
        "transaction_id": data.get("transactionId") or data.get("refNum", ""),
        "amount_cents": amount_cents,
        "auth_code": data.get("authCode", ""),
        "raw": data,
    }


def process_refund(
    transaction_id: str,
    amount_cents: int,
    reason: Optional[str] = None,
) -> dict:
    """Process a refund against a previously settled transaction.

    Args:
        transaction_id: The original transaction's ID/refNum
        amount_cents: Amount to refund in cents
        reason: Optional reason

    Returns:
        {status, refund_transaction_id, amount_cents}
    """
    if not settings.ebizcharge_source_key:
        raise ValueError("EBizCharge source key not configured")

    amount_dollars = amount_cents / 100.0

    payload = {
        "command": "credit",
        "sourceKey": settings.ebizcharge_source_key,
        "transactionId": transaction_id,
        "amount": f"{amount_dollars:.2f}",
    }
    if reason:
        payload["description"] = reason

    base_url = _get_base_url()

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{base_url}/transactions/refund",
            headers=_get_headers(),
            json=payload,
        )
        response.raise_for_status()

    data = response.json()

    return {
        "status": _parse_result_code(data),
        "refund_transaction_id": data.get("transactionId") or data.get("refNum", ""),
        "amount_cents": amount_cents,
        "raw": data,
    }


def void_transaction(transaction_id: str) -> dict:
    """Void an unsettled transaction."""
    if not settings.ebizcharge_source_key:
        raise ValueError("EBizCharge source key not configured")

    payload = {
        "command": "void",
        "sourceKey": settings.ebizcharge_source_key,
        "transactionId": transaction_id,
    }

    base_url = _get_base_url()

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{base_url}/transactions/void",
            headers=_get_headers(),
            json=payload,
        )
        response.raise_for_status()

    data = response.json()

    return {
        "status": _parse_result_code(data),
        "raw": data,
    }
