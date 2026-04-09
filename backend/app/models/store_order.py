import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Order(Base):
    """E-commerce order for the King Cap store."""
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number = Column(String(50), unique=True, nullable=False, index=True)  # e.g. "KC-2026-00001"
    store_user_id = Column(String(36), ForeignKey("store_users.id"), nullable=False, index=True)

    # Status
    status = Column(String(50), nullable=False, default="pending", index=True)
    # pending, confirmed, mockup_pending, mockup_approved, in_production, quality_check, shipped, delivered, cancelled, refunded
    payment_status = Column(String(50), nullable=False, default="unpaid", index=True)
    # unpaid, paid, partially_refunded, refunded, failed

    # Pricing (all in cents)
    subtotal = Column(Integer, nullable=False, default=0)
    shipping_cost = Column(Integer, nullable=False, default=0)
    tax_amount = Column(Integer, nullable=False, default=0)
    discount_amount = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)

    # Shipping
    shipping_address_id = Column(String(36), ForeignKey("addresses.id"), nullable=True)
    billing_address_id = Column(String(36), ForeignKey("addresses.id"), nullable=True)
    shipping_method = Column(String(100), nullable=True)
    carrier = Column(String(100), nullable=True)
    in_hand_date = Column(DateTime, nullable=True)
    tracking_number = Column(String(255), nullable=True)
    tracking_url = Column(String(500), nullable=True)

    # EBizCharge Payment
    ebiz_transaction_id = Column(String(255), nullable=True, index=True)
    ebiz_form_key = Column(String(255), nullable=True, index=True)
    ebiz_auth_code = Column(String(100), nullable=True)
    ebiz_refund_transaction_id = Column(String(255), nullable=True)

    # Production
    production_type = Column(String(50), nullable=True)  # domestic, overseas
    estimated_ship_date = Column(DateTime, nullable=True)
    actual_ship_date = Column(DateTime, nullable=True)

    # Notes
    customer_notes = Column(Text, nullable=True)
    internal_notes = Column(Text, nullable=True)

    # Salesperson
    salesperson_id = Column(String(36), ForeignKey("store_users.id"), nullable=True, index=True)

    # Cross-entity links
    source_quote_id = Column(String(36), ForeignKey("quotes.id"), nullable=True, index=True)
    source_sample_request_id = Column(String(36), ForeignKey("sample_requests.id"), nullable=True, index=True)
    order_type = Column(String(50), nullable=False, default="standard")
    # standard, quote_conversion, sample_production
    linked_production_order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    # For sample orders: points to the production order created from it
    linked_design_request_id = Column(String(36), ForeignKey("design_requests.id"), nullable=True)

    # BigCommerce sync
    bc_sales_order_id = Column(String(100), nullable=True, index=True)
    bc_invoice_id = Column(String(100), nullable=True)
    bc_synced_at = Column(DateTime, nullable=True)
    bc_sync_status = Column(String(50), nullable=True)

    # Pipedrive sync
    pipedrive_deal_id = Column(String(100), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store_user = relationship("StoreUser", back_populates="orders", foreign_keys=[store_user_id])
    salesperson = relationship("StoreUser", foreign_keys=[salesperson_id])
    shipping_address = relationship("Address", foreign_keys=[shipping_address_id])
    billing_address = relationship("Address", foreign_keys=[billing_address_id])
    source_quote = relationship("Quote", foreign_keys=[source_quote_id])
    source_sample_request = relationship("SampleRequest", foreign_keys=[source_sample_request_id])
    linked_production_order = relationship("Order", foreign_keys=[linked_production_order_id], remote_side=[id])
    linked_design_request = relationship("DesignRequest", foreign_keys=[linked_design_request_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusHistory.created_at")
    invoices = relationship("Invoice", back_populates="order", cascade="all, delete-orphan")
    mockup_approvals = relationship("MockupApproval", back_populates="order", cascade="all, delete-orphan")
    attachments = relationship("OrderAttachment", back_populates="order", cascade="all, delete-orphan", order_by="OrderAttachment.created_at")

    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderItem(Base):
    """Line item within an order."""
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)
    hat_color = Column(String(255), nullable=True)

    # Pricing (in cents)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)
    total_price = Column(Integer, nullable=False)

    # Customization
    customization = Column(Text, nullable=True)  # JSON string
    customization_preview = Column(String(500), nullable=True)

    # Decoration details
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
    item_production_type = Column(String(50), nullable=True)  # blank, domestic, overseas

    # Overseas extras
    design_addons = Column(Text, nullable=True)  # JSON array of add-on names
    overseas_accessories = Column(Text, nullable=True)  # JSON array
    overseas_shipping_method = Column(String(255), nullable=True)

    # Domestic extras
    rush_speed = Column(String(255), nullable=True)
    include_rope = Column(Boolean, nullable=True, default=False)

    # Reference photo
    reference_photo_path = Column(String(500), nullable=True)

    # Design link
    art_id = Column(String(100), nullable=True)  # e.g. "ART-2026-00042"
    design_request_id = Column(String(36), ForeignKey("design_requests.id"), nullable=True)

    # BigCommerce sync
    bc_sales_line_id = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    variant = relationship("ProductVariant")
    design_request = relationship("DesignRequest", foreign_keys=[design_request_id])

    def __repr__(self):
        return f"<OrderItem product={self.product_id} qty={self.quantity}>"


class OrderStatusHistory(Base):
    """Audit trail of order status changes."""
    __tablename__ = "order_status_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    changed_by = Column(String(36), nullable=True)  # store_user id or admin id
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="status_history")

    def __repr__(self):
        return f"<OrderStatusHistory order={self.order_id} status={self.status}>"


class Invoice(Base):
    """Invoice associated with an order."""
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    amount = Column(Integer, nullable=False)  # cents
    pdf_url = Column(String(500), nullable=True)

    # BigCommerce sync
    bc_invoice_id = Column(String(100), nullable=True)

    # Dates
    issued_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="invoices")

    def __repr__(self):
        return f"<Invoice {self.invoice_number} for order {self.order_id}>"
