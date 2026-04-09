import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..database import Base


class StoreUser(Base):
    """E-commerce customer for the King Cap store."""
    __tablename__ = "store_users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False, default="")
    first_name = Column(String(255), nullable=False, default="")
    last_name = Column(String(255), nullable=False, default="")
    phone = Column(String(50), nullable=True)
    company_name = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)

    # Role & status
    role = Column(String(50), nullable=False, default="customer")  # customer, wholesale, golf, salesperson, admin
    status = Column(String(50), nullable=False, default="active")  # active, suspended, deactivated

    # Email verification
    email_verified_at = Column(DateTime, nullable=True)

    # Application fields (for wholesale/golf approval flow)
    application_status = Column(String(50), nullable=True)  # pending, approved, rejected
    application_date = Column(DateTime, nullable=True)
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    application_notes = Column(Text, nullable=True)

    # Wholesale-specific fields
    tax_id = Column(String(100), nullable=True)
    resale_certificate_path = Column(String(500), nullable=True)
    business_type = Column(String(100), nullable=True)
    annual_volume = Column(String(100), nullable=True)

    # Golf-specific fields
    course_name = Column(String(255), nullable=True)
    course_location = Column(String(255), nullable=True)
    proshop_contact = Column(String(255), nullable=True)

    # Shipping account numbers
    ups_account_number = Column(String(100), nullable=True)
    fedex_account_number = Column(String(100), nullable=True)

    # Tax exemption document
    tax_exemption_path = Column(String(500), nullable=True)

    # Pricing & sales
    pricing_tier_id = Column(String(36), ForeignKey("pricing_tiers.id"), nullable=True, index=True)
    salesperson_id = Column(String(36), ForeignKey("store_users.id"), nullable=True, index=True)

    # BigCommerce sync
    bc_customer_id = Column(String(100), unique=True, nullable=True, index=True)
    bc_synced_at = Column(DateTime, nullable=True)

    # Pipedrive sync
    pipedrive_person_id = Column(String(100), unique=True, nullable=True, index=True)
    pipedrive_synced_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pricing_tier = relationship("PricingTier", back_populates="store_users")
    salesperson = relationship("StoreUser", remote_side=[id], backref="assigned_customers")
    addresses = relationship("Address", back_populates="store_user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store_user", foreign_keys="Order.store_user_id")
    cart_items = relationship("CartItem", back_populates="store_user", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="store_user", foreign_keys="Quote.store_user_id")
    mockup_approvals = relationship("MockupApproval", back_populates="store_user")

    def __repr__(self):
        return f"<StoreUser {self.email}>"
