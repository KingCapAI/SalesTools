"""Business Central sync orchestration service.

Handles the business logic of syncing data between our database and BC:
  - Products:  BC → Website (pull items, upsert Product/ProductVariant)
  - Inventory: BC → Website (pull stock levels, update ProductVariant.stock_qty)
  - Customers: Website → BC (push approved/created customers)
  - Orders:    Website → BC (push confirmed orders as Sales Orders)
  - Invoices:  BC → Website (pull posted invoices)

Each function logs to SyncLog for audit trail and updates SyncCursor for
incremental syncing.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models.store_product import Product, ProductVariant, ProductCategory
from ..models.store_user import StoreUser
from ..models.store_order import Order, OrderItem, Invoice
from ..models.sync import SyncLog, SyncCursor
from . import bc_service

logger = logging.getLogger(__name__)


def _log_sync(
    db: Session,
    integration: str,
    entity_type: str,
    entity_id: Optional[str],
    external_id: Optional[str],
    direction: str,
    status: str,
    error_message: Optional[str] = None,
    payload: Optional[dict] = None,
) -> SyncLog:
    """Create a SyncLog entry."""
    log = SyncLog(
        integration=integration,
        entity_type=entity_type,
        entity_id=entity_id,
        external_id=external_id,
        direction=direction,
        status=status,
        error_message=error_message,
        payload=json.dumps(payload) if payload else None,
    )
    db.add(log)
    return log


def _get_cursor(db: Session, entity_type: str) -> Optional[datetime]:
    """Get the last sync timestamp for a BC entity type."""
    cursor = (
        db.query(SyncCursor)
        .filter(
            SyncCursor.integration == "bc",
            SyncCursor.entity_type == entity_type,
        )
        .first()
    )
    return cursor.last_synced_at if cursor else None


def _set_cursor(db: Session, entity_type: str, synced_at: datetime):
    """Update the sync cursor for a BC entity type."""
    cursor = (
        db.query(SyncCursor)
        .filter(
            SyncCursor.integration == "bc",
            SyncCursor.entity_type == entity_type,
        )
        .first()
    )
    if cursor:
        cursor.last_synced_at = synced_at
        cursor.updated_at = datetime.utcnow()
    else:
        cursor = SyncCursor(
            integration="bc",
            entity_type=entity_type,
            last_synced_at=synced_at,
        )
        db.add(cursor)


# ---------------------------------------------------------------------------
# Product Sync: BC → Website
# ---------------------------------------------------------------------------

async def sync_products(db: Session, full: bool = False) -> dict:
    """Pull items from BC and upsert Product records.

    Args:
        db: Database session
        full: If True, ignore cursor and pull all items

    Returns:
        {created: int, updated: int, errors: int}
    """
    cursor_dt = None if full else _get_cursor(db, "products")
    stats = {"created": 0, "updated": 0, "errors": 0}

    try:
        items = await bc_service.get_items(modified_since=cursor_dt)
    except Exception as e:
        _log_sync(db, "bc", "product", None, None, "inbound", "error", str(e))
        db.commit()
        raise

    for item in items:
        item_number = item.get("number", "")
        try:
            product = (
                db.query(Product)
                .filter(
                    (Product.bc_item_id == item.get("id"))
                    | (Product.style_number == item_number)
                )
                .first()
            )

            is_active = not item.get("blocked", False)
            base_price_cents = int(round(float(item.get("unitPrice", 0)) * 100))

            if product:
                # Update existing product
                product.base_price = base_price_cents
                product.is_active = is_active
                product.bc_item_id = item.get("id")
                product.bc_synced_at = datetime.utcnow()
                stats["updated"] += 1
            else:
                # Create new product
                display_name = item.get("displayName", item_number)
                slug = display_name.lower().replace(" ", "-").replace("/", "-")
                # Ensure unique slug
                existing = db.query(Product).filter(Product.slug == slug).first()
                if existing:
                    slug = f"{slug}-{item_number.lower()}"

                product = Product(
                    name=display_name,
                    slug=slug,
                    style_number=item_number,
                    base_price=base_price_cents,
                    is_active=is_active,
                    bc_item_id=item.get("id"),
                    bc_synced_at=datetime.utcnow(),
                )
                db.add(product)
                stats["created"] += 1

            # Map category if itemCategoryCode exists
            cat_code = item.get("itemCategoryCode")
            if cat_code:
                category = (
                    db.query(ProductCategory)
                    .filter(ProductCategory.slug == cat_code.lower())
                    .first()
                )
                if category:
                    product.category_id = category.id

            _log_sync(
                db, "bc", "product", product.id if product.id else None,
                item.get("id"), "inbound", "success",
            )
        except Exception as e:
            logger.error("Failed to sync item %s: %s", item_number, e)
            _log_sync(
                db, "bc", "product", None, item.get("id"),
                "inbound", "error", str(e),
            )
            stats["errors"] += 1

    _set_cursor(db, "products", datetime.utcnow())
    db.commit()
    return stats


# ---------------------------------------------------------------------------
# Inventory Sync: BC → Website
# ---------------------------------------------------------------------------

async def sync_inventory(db: Session) -> dict:
    """Pull inventory levels from BC and update ProductVariant.stock_qty.

    If a product has no variants, we update a default variant or skip.
    """
    stats = {"updated": 0, "skipped": 0, "errors": 0}

    try:
        inventory_data = await bc_service.get_item_inventory()
    except Exception as e:
        _log_sync(db, "bc", "inventory", None, None, "inbound", "error", str(e))
        db.commit()
        raise

    for item in inventory_data:
        item_number = item.get("number", "")
        stock_qty = int(item.get("inventory", 0))

        product = (
            db.query(Product)
            .filter(Product.style_number == item_number)
            .first()
        )
        if not product:
            stats["skipped"] += 1
            continue

        # Update all variants for this product proportionally,
        # or the single default variant
        variants = (
            db.query(ProductVariant)
            .filter(ProductVariant.product_id == product.id)
            .all()
        )
        if variants:
            # Distribute stock evenly across variants (simple approach)
            per_variant = max(stock_qty // len(variants), 0)
            remainder = stock_qty - (per_variant * len(variants))
            for i, v in enumerate(variants):
                v.stock_qty = per_variant + (1 if i < remainder else 0)
            stats["updated"] += 1
        else:
            stats["skipped"] += 1

    _set_cursor(db, "inventory", datetime.utcnow())
    db.commit()
    return stats


# ---------------------------------------------------------------------------
# Customer Sync: Website → BC
# ---------------------------------------------------------------------------

async def push_customer(db: Session, user: StoreUser) -> Optional[str]:
    """Push a single customer to BC. Returns the BC customer ID or None on error."""
    if user.bc_customer_id:
        # Already synced — update instead
        try:
            await bc_service.update_customer(
                user.bc_customer_id,
                {
                    "displayName": f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email,
                    "email": user.email,
                    "phoneNumber": user.phone or "",
                },
            )
            user.bc_synced_at = datetime.utcnow()
            _log_sync(
                db, "bc", "customer", user.id, user.bc_customer_id,
                "outbound", "success",
            )
            db.commit()
            return user.bc_customer_id
        except Exception as e:
            _log_sync(
                db, "bc", "customer", user.id, user.bc_customer_id,
                "outbound", "error", str(e),
            )
            db.commit()
            return None

    # Create new customer in BC
    display_name = user.company_name or f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email

    # Determine price group from pricing tier
    price_group = None
    if user.pricing_tier:
        price_group = user.pricing_tier.name

    try:
        result = await bc_service.create_customer(
            name=display_name,
            email=user.email,
            phone=user.phone,
            customer_price_group=price_group,
        )
        bc_id = result.get("number") or result.get("id", "")
        user.bc_customer_id = bc_id
        user.bc_synced_at = datetime.utcnow()
        _log_sync(
            db, "bc", "customer", user.id, bc_id,
            "outbound", "success",
        )
        db.commit()
        return bc_id
    except Exception as e:
        logger.error("Failed to push customer %s to BC: %s", user.id, e)
        _log_sync(
            db, "bc", "customer", user.id, None,
            "outbound", "error", str(e),
        )
        db.commit()
        return None


async def push_all_unsynced_customers(db: Session) -> dict:
    """Push all customers without a bc_customer_id to BC."""
    stats = {"synced": 0, "errors": 0}

    users = (
        db.query(StoreUser)
        .filter(
            StoreUser.bc_customer_id.is_(None),
            StoreUser.role.in_(["customer", "wholesale", "golf"]),
            StoreUser.status == "active",
        )
        .all()
    )

    for user in users:
        result = await push_customer(db, user)
        if result:
            stats["synced"] += 1
        else:
            stats["errors"] += 1

    return stats


# ---------------------------------------------------------------------------
# Order Sync: Website → BC
# ---------------------------------------------------------------------------

async def push_order(db: Session, order: Order) -> Optional[str]:
    """Push a confirmed order to BC as a Sales Order.

    Returns the BC sales order ID or None on error.
    """
    if order.bc_sales_order_id:
        _log_sync(
            db, "bc", "order", order.id, order.bc_sales_order_id,
            "outbound", "skipped", "Already synced",
        )
        db.commit()
        return order.bc_sales_order_id

    # Ensure the customer is synced to BC
    customer = order.store_user
    if not customer:
        _log_sync(
            db, "bc", "order", order.id, None,
            "outbound", "error", "No customer associated with order",
        )
        db.commit()
        return None

    if not customer.bc_customer_id:
        bc_cust_id = await push_customer(db, customer)
        if not bc_cust_id:
            _log_sync(
                db, "bc", "order", order.id, None,
                "outbound", "error", "Failed to sync customer to BC first",
            )
            db.commit()
            return None

    # Create the sales order header
    try:
        so = await bc_service.create_sales_order(
            customer_number=customer.bc_customer_id,
            order_number=order.order_number,
            order_date=order.created_at.strftime("%Y-%m-%d") if order.created_at else None,
        )
        bc_so_id = so.get("id", "")
    except Exception as e:
        logger.error("Failed to create BC sales order for %s: %s", order.order_number, e)
        _log_sync(
            db, "bc", "order", order.id, None,
            "outbound", "error", str(e),
        )
        order.bc_sync_status = "error"
        db.commit()
        return None

    # Add line items
    items = (
        db.query(OrderItem)
        .filter(OrderItem.order_id == order.id)
        .all()
    )
    for item in items:
        # Look up the product's style_number (= BC item number)
        product = item.product
        item_number = product.style_number if product else "MISC"
        description = product.name if product else "Custom Hat"

        try:
            await bc_service.add_sales_order_line(
                sales_order_id=bc_so_id,
                item_number=item_number,
                quantity=item.quantity,
                unit_price_dollars=item.unit_price / 100.0,
                description=description,
            )
        except Exception as e:
            logger.warning(
                "Failed to add line for item %s on order %s: %s",
                item_number, order.order_number, e,
            )

    # Update our order with BC reference
    order.bc_sales_order_id = bc_so_id
    order.bc_synced_at = datetime.utcnow()
    order.bc_sync_status = "synced"

    _log_sync(
        db, "bc", "order", order.id, bc_so_id,
        "outbound", "success",
    )
    db.commit()
    return bc_so_id


# ---------------------------------------------------------------------------
# Invoice Sync: BC → Website
# ---------------------------------------------------------------------------

async def sync_invoices(db: Session) -> dict:
    """Pull recent invoices from BC and match them to orders."""
    cursor_dt = _get_cursor(db, "invoices")
    stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    try:
        invoices = await bc_service.get_sales_invoices(modified_since=cursor_dt)
    except Exception as e:
        _log_sync(db, "bc", "invoice", None, None, "inbound", "error", str(e))
        db.commit()
        raise

    for inv in invoices:
        ext_doc = inv.get("externalDocumentNumber", "")
        bc_inv_id = inv.get("id", "")
        inv_number = inv.get("number", "")

        # Match to our order by external document number (= our order_number)
        order = (
            db.query(Order)
            .filter(Order.order_number == ext_doc)
            .first()
        ) if ext_doc else None

        if not order:
            stats["skipped"] += 1
            continue

        # Check if invoice already exists
        existing = (
            db.query(Invoice)
            .filter(Invoice.invoice_number == inv_number)
            .first()
        )

        if existing:
            existing.amount = int(round(float(inv.get("totalAmountIncludingTax", 0)) * 100))
            existing.bc_invoice_id = bc_inv_id
            stats["updated"] += 1
        else:
            invoice_date_str = inv.get("invoiceDate")
            due_date_str = inv.get("dueDate")

            new_inv = Invoice(
                order_id=order.id,
                invoice_number=inv_number,
                amount=int(round(float(inv.get("totalAmountIncludingTax", 0)) * 100)),
                bc_invoice_id=bc_inv_id,
                issued_at=datetime.fromisoformat(invoice_date_str) if invoice_date_str else None,
                due_at=datetime.fromisoformat(due_date_str) if due_date_str else None,
            )
            db.add(new_inv)

            # Update order's BC invoice reference
            order.bc_invoice_id = bc_inv_id
            stats["created"] += 1

        _log_sync(
            db, "bc", "invoice", order.id, bc_inv_id,
            "inbound", "success",
        )

    _set_cursor(db, "invoices", datetime.utcnow())
    db.commit()
    return stats


# ---------------------------------------------------------------------------
# Sync Status
# ---------------------------------------------------------------------------

def get_sync_status(db: Session) -> dict:
    """Get the current sync status for all BC entity types."""
    entity_types = ["products", "inventory", "invoices"]
    status = {}

    for et in entity_types:
        cursor = (
            db.query(SyncCursor)
            .filter(SyncCursor.integration == "bc", SyncCursor.entity_type == et)
            .first()
        )
        # Most recent log entry
        last_log = (
            db.query(SyncLog)
            .filter(SyncLog.integration == "bc", SyncLog.entity_type == et.rstrip("s"))
            .order_by(SyncLog.created_at.desc())
            .first()
        )
        status[et] = {
            "last_synced_at": cursor.last_synced_at.isoformat() if cursor and cursor.last_synced_at else None,
            "last_status": last_log.status if last_log else None,
            "last_error": last_log.error_message if last_log and last_log.status == "error" else None,
        }

    # Counts of unsynced entities
    status["unsynced_customers"] = (
        db.query(StoreUser)
        .filter(
            StoreUser.bc_customer_id.is_(None),
            StoreUser.role.in_(["customer", "wholesale", "golf"]),
            StoreUser.status == "active",
        )
        .count()
    )
    status["unsynced_orders"] = (
        db.query(Order)
        .filter(
            Order.bc_sales_order_id.is_(None),
            Order.status == "confirmed",
            Order.payment_status == "paid",
        )
        .count()
    )

    return status
