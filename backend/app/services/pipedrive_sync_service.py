"""Pipedrive CRM sync orchestration service.

Handles business logic for syncing contacts and deals between our DB and Pipedrive:
  - Contacts:  Website → Pipedrive (on registration/creation)
  - Deals:     Website → Pipedrive (on quote sent, order confirmed, etc.)
  - Inbound:   Pipedrive → Website (webhook-driven lead conversion)

All operations log to SyncLog for audit trail.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models.store_user import StoreUser
from ..models.store_order import Order
from ..models.sync import SyncLog
from . import pipedrive_service as pd

logger = logging.getLogger(__name__)


def _log_sync(
    db: Session,
    entity_type: str,
    entity_id: Optional[str],
    external_id: Optional[str],
    direction: str,
    status: str,
    error_message: Optional[str] = None,
):
    log = SyncLog(
        integration="pipedrive",
        entity_type=entity_type,
        entity_id=entity_id,
        external_id=external_id,
        direction=direction,
        status=status,
        error_message=error_message,
    )
    db.add(log)


# ---------------------------------------------------------------------------
# Contact Sync: Website → Pipedrive
# ---------------------------------------------------------------------------

def push_contact(db: Session, user: StoreUser) -> Optional[int]:
    """Push or update a customer as a Pipedrive Person (+ Organization).

    Returns the Pipedrive person_id or None on error.
    """
    try:
        # Check if already synced
        if user.pipedrive_person_id:
            pd.update_person(
                int(user.pipedrive_person_id),
                {
                    "name": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
                    "email": [{"value": user.email, "primary": True}],
                    "phone": [{"value": user.phone, "primary": True}] if user.phone else [],
                },
            )
            user.pipedrive_synced_at = datetime.utcnow()
            _log_sync(db, "person", user.id, user.pipedrive_person_id, "outbound", "success")
            db.commit()
            return int(user.pipedrive_person_id)

        # Create organization if company name exists
        org_id = None
        if user.company_name:
            existing_org = pd.find_organization_by_name(user.company_name)
            if existing_org:
                org_id = existing_org.get("id")
            else:
                org = pd.create_organization(name=user.company_name)
                org_id = org.get("id")

        # Create person
        person = pd.create_person(
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            email=user.email,
            phone=user.phone,
            org_id=org_id,
            custom_fields={
                # These would map to custom Pipedrive fields once configured
            },
        )
        person_id = person.get("id")
        if person_id:
            user.pipedrive_person_id = str(person_id)
            user.pipedrive_synced_at = datetime.utcnow()
            _log_sync(db, "person", user.id, str(person_id), "outbound", "success")
            db.commit()
            return person_id

        _log_sync(db, "person", user.id, None, "outbound", "error", "No person ID returned")
        db.commit()
        return None

    except Exception as e:
        logger.error("Failed to push contact %s to Pipedrive: %s", user.id, e)
        _log_sync(db, "person", user.id, None, "outbound", "error", str(e))
        db.commit()
        return None


def push_all_unsynced_contacts(db: Session) -> dict:
    """Push all customers without a pipedrive_person_id."""
    stats = {"synced": 0, "errors": 0}

    users = (
        db.query(StoreUser)
        .filter(
            StoreUser.pipedrive_person_id.is_(None),
            StoreUser.role.in_(["customer", "wholesale", "golf"]),
            StoreUser.status == "active",
        )
        .all()
    )

    for user in users:
        result = push_contact(db, user)
        if result:
            stats["synced"] += 1
        else:
            stats["errors"] += 1

    return stats


# ---------------------------------------------------------------------------
# Deal Sync: Website → Pipedrive
# ---------------------------------------------------------------------------

def push_order_deal(db: Session, order: Order) -> Optional[int]:
    """Create or update a Pipedrive deal for a confirmed order.

    Returns the Pipedrive deal_id or None on error.
    """
    if order.pipedrive_deal_id:
        # Already has a deal — update it
        try:
            pd.update_deal(
                int(order.pipedrive_deal_id),
                {
                    "title": f"Order {order.order_number}",
                    "value": order.total / 100.0,
                    "status": _order_status_to_deal_status(order.status),
                },
            )
            _log_sync(db, "deal", order.id, order.pipedrive_deal_id, "outbound", "success")
            db.commit()
            return int(order.pipedrive_deal_id)
        except Exception as e:
            logger.error("Failed to update Pipedrive deal for %s: %s", order.order_number, e)
            _log_sync(db, "deal", order.id, order.pipedrive_deal_id, "outbound", "error", str(e))
            db.commit()
            return None

    # Ensure contact is synced first
    customer = order.store_user
    if not customer:
        return None

    person_id = None
    if customer.pipedrive_person_id:
        person_id = int(customer.pipedrive_person_id)
    else:
        person_id = push_contact(db, customer)

    try:
        deal = pd.create_deal(
            title=f"Order {order.order_number}",
            person_id=person_id,
            value=order.total / 100.0,
        )
        deal_id = deal.get("id")
        if deal_id:
            order.pipedrive_deal_id = str(deal_id)
            _log_sync(db, "deal", order.id, str(deal_id), "outbound", "success")
            db.commit()
            return deal_id

        _log_sync(db, "deal", order.id, None, "outbound", "error", "No deal ID returned")
        db.commit()
        return None
    except Exception as e:
        logger.error("Failed to create Pipedrive deal for %s: %s", order.order_number, e)
        _log_sync(db, "deal", order.id, None, "outbound", "error", str(e))
        db.commit()
        return None


def push_application_deal(
    db: Session,
    user: StoreUser,
    application_type: str,
) -> Optional[int]:
    """Create a Pipedrive deal for a wholesale/golf application."""
    person_id = None
    if user.pipedrive_person_id:
        person_id = int(user.pipedrive_person_id)
    else:
        person_id = push_contact(db, user)

    try:
        deal = pd.create_deal(
            title=f"{application_type.title()} Application — {user.company_name or user.email}",
            person_id=person_id,
        )
        deal_id = deal.get("id")
        if deal_id:
            _log_sync(db, "deal", user.id, str(deal_id), "outbound", "success")
            db.commit()
            return deal_id
        return None
    except Exception as e:
        logger.error("Failed to create application deal for %s: %s", user.id, e)
        _log_sync(db, "deal", user.id, None, "outbound", "error", str(e))
        db.commit()
        return None


def update_application_deal(
    db: Session,
    user: StoreUser,
    deal_id: int,
    approved: bool,
) -> None:
    """Update a Pipedrive deal after application approval/rejection."""
    try:
        pd.update_deal(deal_id, {
            "status": "won" if approved else "lost",
            "lost_reason": None if approved else "Application rejected",
        })
        _log_sync(db, "deal", user.id, str(deal_id), "outbound", "success")
    except Exception as e:
        logger.error("Failed to update application deal %s: %s", deal_id, e)
        _log_sync(db, "deal", user.id, str(deal_id), "outbound", "error", str(e))
    db.commit()


# ---------------------------------------------------------------------------
# Inbound: Pipedrive → Website (webhook-driven)
# ---------------------------------------------------------------------------

def handle_person_webhook(db: Session, payload: dict) -> Optional[str]:
    """Handle a Pipedrive person webhook (e.g., lead qualified → create account).

    Returns the created user ID or None.
    """
    event = payload.get("event", "")
    current = payload.get("current", {})

    # Only handle person updates with a specific custom field
    # that signals "create King Cap account"
    if event not in ("updated.person", "added.person"):
        return None

    email_list = current.get("email", [])
    if not email_list:
        return None

    email = email_list[0].get("value", "") if isinstance(email_list, list) else ""
    if not email:
        return None

    # Check if user already exists
    existing = db.query(StoreUser).filter(StoreUser.email == email).first()
    if existing:
        # Update Pipedrive reference if missing
        if not existing.pipedrive_person_id:
            existing.pipedrive_person_id = str(current.get("id", ""))
            existing.pipedrive_synced_at = datetime.utcnow()
            db.commit()
        return existing.id

    # Create a new StoreUser from Pipedrive lead
    from ..services.store_auth_service import hash_password, generate_random_password

    temp_password = generate_random_password()
    name = current.get("name", "")
    parts = name.split(" ", 1) if name else ["", ""]
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else ""

    org = current.get("org_name", "")

    new_user = StoreUser(
        email=email,
        password_hash=hash_password(temp_password),
        first_name=first_name,
        last_name=last_name,
        name=name,
        company_name=org or None,
        role="customer",
        status="active",
        pipedrive_person_id=str(current.get("id", "")),
        pipedrive_synced_at=datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    _log_sync(
        db, "person", new_user.id, str(current.get("id", "")),
        "inbound", "success",
    )
    db.commit()

    # Send account created email with temp password
    from ..services.email_service import send_customer_account_created
    try:
        send_customer_account_created(
            to_email=email,
            first_name=first_name,
            temp_password=temp_password,
            created_by="Pipedrive",
        )
    except Exception as e:
        logger.warning("Failed to send account created email to %s: %s", email, e)

    return new_user.id


def _order_status_to_deal_status(order_status: str) -> str:
    """Map our order status to a Pipedrive deal status."""
    if order_status in ("cancelled", "refunded"):
        return "lost"
    if order_status == "delivered":
        return "won"
    return "open"
