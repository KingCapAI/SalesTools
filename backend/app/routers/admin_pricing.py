"""Admin pricing management routes - tiers, rules, and pricing matrix."""

from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models.store_pricing import PricingTier, PricingRule
from ..models.store_product import Product
from ..utils.store_dependencies import require_store_role

router = APIRouter(prefix="/admin/pricing", tags=["Admin Pricing"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PricingTierListItem(BaseModel):
    id: str
    name: str
    tier_type: str
    discount_pct: float
    is_default: bool
    rule_count: int = 0

    class Config:
        from_attributes = True


class PricingRuleResponse(BaseModel):
    id: str
    pricing_tier_id: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    style_number: Optional[str] = None
    min_qty: int
    max_qty: Optional[int] = None
    price_per_unit: int  # cents

    class Config:
        from_attributes = True


class PricingRuleCreate(BaseModel):
    product_id: Optional[str] = None
    min_qty: int
    max_qty: Optional[int] = None
    price_per_unit: int  # cents


class PricingRuleUpdate(BaseModel):
    min_qty: Optional[int] = None
    max_qty: Optional[int] = None
    price_per_unit: Optional[int] = None


class PricingMatrixRow(BaseModel):
    product_id: str
    product_name: str
    style_number: str
    collection: str
    base_price: int  # DTC retail price in cents
    breaks: list[dict]  # list of {min_qty, max_qty, price_per_unit} per tier


# ---------------------------------------------------------------------------
# Tier endpoints
# ---------------------------------------------------------------------------

@router.get("/tiers", response_model=list[PricingTierListItem])
async def list_tiers(
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """List all pricing tiers with rule counts."""
    results = (
        db.query(
            PricingTier,
            func.count(PricingRule.id).label("rule_count"),
        )
        .outerjoin(PricingRule, PricingTier.id == PricingRule.pricing_tier_id)
        .group_by(PricingTier.id)
        .order_by(PricingTier.tier_type)
        .all()
    )

    items = []
    for tier, rule_count in results:
        items.append(PricingTierListItem(
            id=tier.id,
            name=tier.name,
            tier_type=tier.tier_type,
            discount_pct=tier.discount_pct or 0.0,
            is_default=tier.is_default,
            rule_count=rule_count,
        ))
    return items


# ---------------------------------------------------------------------------
# Rule endpoints
# ---------------------------------------------------------------------------

@router.get("/tiers/{tier_id}/rules", response_model=list[PricingRuleResponse])
async def list_tier_rules(
    tier_id: str,
    product_id: Optional[str] = None,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """List pricing rules for a tier, optionally filtered by product."""
    tier = db.query(PricingTier).filter(PricingTier.id == tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")

    query = (
        db.query(PricingRule, Product.name, Product.style_number)
        .outerjoin(Product, PricingRule.product_id == Product.id)
        .filter(PricingRule.pricing_tier_id == tier_id)
    )

    if product_id:
        query = query.filter(PricingRule.product_id == product_id)

    query = query.order_by(Product.name, PricingRule.min_qty)
    results = query.all()

    items = []
    for rule, product_name, style_number in results:
        items.append(PricingRuleResponse(
            id=rule.id,
            pricing_tier_id=rule.pricing_tier_id,
            product_id=rule.product_id,
            product_name=product_name,
            style_number=style_number,
            min_qty=rule.min_qty,
            max_qty=rule.max_qty,
            price_per_unit=rule.price_per_unit,
        ))
    return items


@router.post("/tiers/{tier_id}/rules", response_model=PricingRuleResponse)
async def create_rule(
    tier_id: str,
    data: PricingRuleCreate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Create a new pricing rule for a tier."""
    tier = db.query(PricingTier).filter(PricingTier.id == tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")

    rule = PricingRule(
        pricing_tier_id=tier_id,
        **data.model_dump(),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Fetch product name/style_number if linked
    product_name = None
    style_number = None
    if rule.product_id:
        product = db.query(Product).filter(Product.id == rule.product_id).first()
        if product:
            product_name = product.name
            style_number = product.style_number

    return PricingRuleResponse(
        id=rule.id,
        pricing_tier_id=rule.pricing_tier_id,
        product_id=rule.product_id,
        product_name=product_name,
        style_number=style_number,
        min_qty=rule.min_qty,
        max_qty=rule.max_qty,
        price_per_unit=rule.price_per_unit,
    )


@router.put("/rules/{rule_id}", response_model=PricingRuleResponse)
async def update_rule(
    rule_id: str,
    data: PricingRuleUpdate,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Update a pricing rule."""
    rule = db.query(PricingRule).filter(PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.commit()
    db.refresh(rule)

    # Fetch product name/style_number if linked
    product_name = None
    style_number = None
    if rule.product_id:
        product = db.query(Product).filter(Product.id == rule.product_id).first()
        if product:
            product_name = product.name
            style_number = product.style_number

    return PricingRuleResponse(
        id=rule.id,
        pricing_tier_id=rule.pricing_tier_id,
        product_id=rule.product_id,
        product_name=product_name,
        style_number=style_number,
        min_qty=rule.min_qty,
        max_qty=rule.max_qty,
        price_per_unit=rule.price_per_unit,
    )


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Delete a pricing rule."""
    rule = db.query(PricingRule).filter(PricingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    db.delete(rule)
    db.commit()
    return {"message": "Pricing rule deleted"}


# ---------------------------------------------------------------------------
# Pricing matrix endpoint
# ---------------------------------------------------------------------------

@router.get("/matrix")
async def get_pricing_matrix(
    admin=Depends(require_store_role("admin")),
    db: Session = Depends(get_db),
):
    """Full pricing matrix across all tiers for all active products."""
    # Fetch all tiers
    tiers = (
        db.query(PricingTier)
        .order_by(PricingTier.tier_type)
        .all()
    )

    # Fetch all active products
    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(Product.collection, Product.style_number)
        .all()
    )

    # Fetch all pricing rules
    all_rules = db.query(PricingRule).all()

    # Group rules by product_id and tier_id
    rules_map = defaultdict(lambda: defaultdict(list))
    for rule in all_rules:
        rules_map[rule.product_id][rule.pricing_tier_id].append({
            "id": rule.id,
            "min_qty": rule.min_qty,
            "max_qty": rule.max_qty,
            "price_per_unit": rule.price_per_unit,
        })

    # Sort each tier's rules by min_qty
    for product_id in rules_map:
        for tier_id in rules_map[product_id]:
            rules_map[product_id][tier_id].sort(key=lambda r: r["min_qty"])

    # Build response
    tiers_data = [
        {
            "id": t.id,
            "name": t.name,
            "tier_type": t.tier_type,
            "discount_pct": t.discount_pct or 0.0,
        }
        for t in tiers
    ]

    products_data = []
    for product in products:
        product_rules = {}
        for tier in tiers:
            product_rules[tier.id] = rules_map.get(product.id, {}).get(tier.id, [])

        products_data.append({
            "id": product.id,
            "name": product.name,
            "style_number": product.style_number,
            "collection": product.collection or "",
            "base_price": product.base_price,
            "rules": product_rules,
        })

    return {
        "tiers": tiers_data,
        "products": products_data,
    }
