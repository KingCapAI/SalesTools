import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Quote(Base):
    """Sales quote for store customers."""
    __tablename__ = "quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_number = Column(String(50), unique=True, nullable=False, index=True)
    store_user_id = Column(String(36), ForeignKey("store_users.id"), nullable=False, index=True)
    salesperson_id = Column(String(36), ForeignKey("store_users.id"), nullable=True, index=True)

    # Status
    status = Column(String(50), nullable=False, default="draft", index=True)
    # draft, sent, viewed, accepted, rejected, expired, converted

    # Line items & pricing (all in cents)
    items = Column(Text, nullable=True)  # JSON string of quote line items
    subtotal = Column(Integer, nullable=False, default=0)
    discount_amount = Column(Integer, nullable=False, default=0)
    shipping_estimate = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)

    # Notes & validity
    notes = Column(Text, nullable=True)
    valid_until = Column(DateTime, nullable=True)

    # Conversion
    converted_order_id = Column(String(36), ForeignKey("orders.id"), unique=True, nullable=True)

    # Cross-entity links
    linked_sample_request_id = Column(String(36), ForeignKey("sample_requests.id"), nullable=True)
    linked_design_request_id = Column(String(36), ForeignKey("design_requests.id"), nullable=True)

    # Business Central sync
    bc_sync_status = Column(String(50), nullable=True)  # not_synced, synced, error

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store_user = relationship("StoreUser", back_populates="quotes", foreign_keys=[store_user_id])
    salesperson = relationship("StoreUser", foreign_keys=[salesperson_id])
    converted_order = relationship("Order", foreign_keys=[converted_order_id])
    linked_sample_request = relationship("SampleRequest", foreign_keys=[linked_sample_request_id])
    linked_design_request = relationship("DesignRequest", foreign_keys=[linked_design_request_id])
    line_items = relationship("QuoteLineItem", back_populates="quote", cascade="all, delete-orphan", order_by="QuoteLineItem.line_number")

    def __repr__(self):
        return f"<Quote {self.quote_number} status={self.status}>"


class QuoteLineItem(Base):
    """Structured line item within a quote."""
    __tablename__ = "quote_line_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_id = Column(String(36), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)

    # Product reference (optional — some lines may be free-text)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)

    # Line details
    description = Column(String(500), nullable=False, default="")
    hat_color = Column(String(255), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False, default=0)  # cents
    total_price = Column(Integer, nullable=False, default=0)  # cents

    # Decorations (matching SampleLineItem pattern)
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

    decoration_notes = Column(Text, nullable=True)

    # Production details
    production_type = Column(String(50), nullable=True)  # blank, domestic, overseas

    # Overseas extras
    design_addons = Column(Text, nullable=True)  # JSON array
    overseas_accessories = Column(Text, nullable=True)  # JSON array
    overseas_shipping_method = Column(String(255), nullable=True)

    # Domestic extras
    rush_speed = Column(String(255), nullable=True)
    include_rope = Column(Boolean, nullable=True, default=False)

    # Reference photo
    reference_photo_path = Column(String(500), nullable=True)

    # Design link
    art_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    quote = relationship("Quote", back_populates="line_items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    def __repr__(self):
        return f"<QuoteLineItem #{self.line_number} qty={self.quantity}>"
