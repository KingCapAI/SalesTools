import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base


class PricingTier(Base):
    """Pricing tier for different customer segments (DTC, wholesale, golf)."""
    __tablename__ = "pricing_tiers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    tier_type = Column(String(50), nullable=False)  # dtc, wholesale, golf
    discount_pct = Column(Float, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store_users = relationship("StoreUser", back_populates="pricing_tier")
    pricing_rules = relationship("PricingRule", back_populates="pricing_tier", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PricingTier {self.name} ({self.tier_type})>"


class PricingRule(Base):
    """Quantity-based pricing rule for a tier, optionally scoped to a product."""
    __tablename__ = "pricing_rules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pricing_tier_id = Column(String(36), ForeignKey("pricing_tiers.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    min_qty = Column(Integer, nullable=False)
    max_qty = Column(Integer, nullable=True)
    price_per_unit = Column(Integer, nullable=False)  # cents

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pricing_tier = relationship("PricingTier", back_populates="pricing_rules")
    product = relationship("Product", back_populates="pricing_rules")

    def __repr__(self):
        return f"<PricingRule tier={self.pricing_tier_id} qty={self.min_qty}-{self.max_qty}>"
