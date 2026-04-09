"""Sample request models: versioned, multi-line-item, audited sample system."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class SampleRequest(Base):
    """Parent record for a sample request project (can contain multiple hats)."""
    __tablename__ = "sample_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_number = Column(String(50), unique=True, nullable=False, index=True)

    # Who requested and for whom
    requested_by_id = Column(String(36), ForeignKey("store_users.id"), nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("store_users.id"), nullable=True, index=True)

    # Status workflow (expanded)
    # draft → submitted → under_review → approved → in_production →
    # sample_complete → customer_review → customer_approved | changes_requested →
    # converting → production_ordered   (or rejected from any non-terminal)
    status = Column(String(50), nullable=False, default="draft", index=True)

    # Versioning
    current_version = Column(Integer, nullable=False, default=0)

    # External references
    factory_reference_number = Column(String(255), nullable=True)
    bc_sales_order_number = Column(String(100), nullable=True)
    bc_purchase_order_number = Column(String(100), nullable=True)

    # Purchasing assignment
    purchasing_assignee_id = Column(String(36), ForeignKey("store_users.id"), nullable=True)

    # Addresses
    shipping_address_id = Column(String(36), ForeignKey("addresses.id"), nullable=True)
    billing_address_id = Column(String(36), ForeignKey("addresses.id"), nullable=True)

    # Shipping account info
    shipping_account_number = Column(String(255), nullable=True)
    shipping_account_company = Column(String(255), nullable=True)
    shipping_account_zip = Column(String(20), nullable=True)

    # Tracking
    tracking_number = Column(String(255), nullable=True)
    tracking_url = Column(String(500), nullable=True)

    # Pricing
    charge_amount = Column(Integer, nullable=False, default=0)  # cents
    discount_amount = Column(Integer, nullable=False, default=0)  # cents

    # Notes
    notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ---- Legacy columns (kept for migration, no longer used in new code) ----
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)
    hat_color = Column(String(255), nullable=True)
    sample_type = Column(String(30), nullable=True)
    quantity = Column(Integer, nullable=True)
    front_decoration = Column(String(255), nullable=True)
    left_decoration = Column(String(255), nullable=True)
    right_decoration = Column(String(255), nullable=True)
    back_decoration = Column(String(255), nullable=True)
    visor_decoration = Column(String(255), nullable=True)
    front_logo_path = Column(String(500), nullable=True)
    left_logo_path = Column(String(500), nullable=True)
    right_logo_path = Column(String(500), nullable=True)
    back_logo_path = Column(String(500), nullable=True)
    visor_logo_path = Column(String(500), nullable=True)
    decoration_notes = Column(Text, nullable=True)
    logo_path = Column(String(500), nullable=True)

    # Relationships
    requested_by = relationship("StoreUser", foreign_keys=[requested_by_id], backref="sample_requests_made")
    customer = relationship("StoreUser", foreign_keys=[customer_id], backref="sample_requests_received")
    purchasing_assignee = relationship("StoreUser", foreign_keys=[purchasing_assignee_id])
    shipping_address = relationship("Address", foreign_keys=[shipping_address_id])
    billing_address = relationship("Address", foreign_keys=[billing_address_id])

    # Children
    line_items = relationship("SampleLineItem", back_populates="sample_request", cascade="all, delete-orphan", order_by="SampleLineItem.line_number")
    versions = relationship("SampleVersion", back_populates="sample_request", cascade="all, delete-orphan", order_by="SampleVersion.version_number")
    activities = relationship("SampleActivity", back_populates="sample_request", cascade="all, delete-orphan", order_by="SampleActivity.created_at.desc()")

    def __repr__(self):
        return f"<SampleRequest {self.sample_number} ({self.status})>"


class SampleLineItem(Base):
    """Individual hat/item within a sample request."""
    __tablename__ = "sample_line_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_request_id = Column(String(36), ForeignKey("sample_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)

    # Product info
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)
    hat_color = Column(String(255), nullable=True)

    # Sample type
    sample_type = Column(String(30), nullable=False, default="blank")
    quantity = Column(Integer, nullable=False, default=1)

    # Decoration fields per location
    front_decoration = Column(String(255), nullable=True)
    left_decoration = Column(String(255), nullable=True)
    right_decoration = Column(String(255), nullable=True)
    back_decoration = Column(String(255), nullable=True)
    visor_decoration = Column(String(255), nullable=True)

    # Per-location logo file paths
    front_logo_path = Column(String(500), nullable=True)
    left_logo_path = Column(String(500), nullable=True)
    right_logo_path = Column(String(500), nullable=True)
    back_logo_path = Column(String(500), nullable=True)
    visor_logo_path = Column(String(500), nullable=True)

    decoration_notes = Column(Text, nullable=True)

    # Per-location thread/ink colors
    front_thread_colors = Column(String(500), nullable=True)
    left_thread_colors = Column(String(500), nullable=True)
    right_thread_colors = Column(String(500), nullable=True)
    back_thread_colors = Column(String(500), nullable=True)
    visor_thread_colors = Column(String(500), nullable=True)

    # Per-location decoration sizes
    front_decoration_size = Column(String(255), nullable=True)
    left_decoration_size = Column(String(255), nullable=True)
    right_decoration_size = Column(String(255), nullable=True)
    back_decoration_size = Column(String(255), nullable=True)
    visor_decoration_size = Column(String(255), nullable=True)

    # Production details
    production_type = Column(String(50), nullable=True)  # blank, domestic, overseas

    # Overseas extras
    design_addons = Column(Text, nullable=True)  # JSON array
    overseas_accessories = Column(Text, nullable=True)  # JSON array
    overseas_shipping_method = Column(String(255), nullable=True)

    # Reference photo
    reference_photo_path = Column(String(500), nullable=True)

    # Art tracking
    art_id = Column(String(100), nullable=True)
    art_version = Column(Integer, nullable=True, default=1)

    # Per-line status and customer feedback
    line_status = Column(String(50), nullable=False, default="pending")
    customer_feedback = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sample_request = relationship("SampleRequest", back_populates="line_items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    def __repr__(self):
        return f"<SampleLineItem #{self.line_number} for {self.sample_request_id}>"


class SampleVersion(Base):
    """Version record tracking each revision round of a sample."""
    __tablename__ = "sample_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_request_id = Column(String(36), ForeignKey("sample_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    created_by_id = Column(String(36), ForeignKey("store_users.id"), nullable=True)
    change_summary = Column(Text, nullable=True)

    # Customer response
    customer_response = Column(String(30), nullable=True)  # approved / changes_requested
    customer_feedback = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    responded_by_id = Column(String(36), ForeignKey("store_users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sample_request = relationship("SampleRequest", back_populates="versions")
    created_by = relationship("StoreUser", foreign_keys=[created_by_id])
    responded_by = relationship("StoreUser", foreign_keys=[responded_by_id])
    photos = relationship("SamplePhoto", back_populates="version", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SampleVersion v{self.version_number} for {self.sample_request_id}>"


class SamplePhoto(Base):
    """Photo attached to a specific version of a sample."""
    __tablename__ = "sample_photos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_version_id = Column(String(36), ForeignKey("sample_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    sample_line_item_id = Column(String(36), ForeignKey("sample_line_items.id"), nullable=True)

    photo_path = Column(String(500), nullable=False)
    caption = Column(String(500), nullable=True)
    uploaded_by_id = Column(String(36), ForeignKey("store_users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    version = relationship("SampleVersion", back_populates="photos")
    line_item = relationship("SampleLineItem")
    uploaded_by = relationship("StoreUser")

    def __repr__(self):
        return f"<SamplePhoto {self.id[:8]} for version {self.sample_version_id[:8]}>"


class SampleActivity(Base):
    """Audit log entry for a sample request."""
    __tablename__ = "sample_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sample_request_id = Column(String(36), ForeignKey("sample_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("store_users.id"), nullable=True)

    action = Column(String(100), nullable=False)  # e.g. "status_change", "photo_upload"
    description = Column(Text, nullable=False)     # human-readable log entry
    details = Column(Text, nullable=True)          # JSON blob for extra context

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sample_request = relationship("SampleRequest", back_populates="activities")
    user = relationship("StoreUser")

    def __repr__(self):
        return f"<SampleActivity {self.action} at {self.created_at}>"
