"""Return request models for order returns and refunds."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class ReturnRequest(Base):
    """Customer return / RMA request."""
    __tablename__ = "return_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    return_number = Column(String(50), unique=True, nullable=False, index=True)  # RMA-2026-XXXXX
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    store_user_id = Column(String(36), ForeignKey("store_users.id"), nullable=False, index=True)

    # Status lifecycle
    status = Column(String(50), nullable=False, default="submitted", index=True)
    # submitted, approved, rejected, shipped_back, received, refund_processing, refunded, closed

    # Reason
    reason = Column(String(100), nullable=False)
    # defective, wrong_item, not_as_described, changed_mind, other
    reason_details = Column(Text, nullable=True)

    # Refund
    refund_amount = Column(Integer, nullable=True)  # cents
    refund_method = Column(String(50), nullable=True)  # original_payment, store_credit

    # Return shipping
    return_tracking_number = Column(String(255), nullable=True)
    return_tracking_url = Column(String(500), nullable=True)

    # Approval
    approved_by = Column(String(36), ForeignKey("store_users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Processing dates
    received_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    # BC sync
    bc_credit_memo_id = Column(String(100), nullable=True)

    # Notes
    admin_notes = Column(Text, nullable=True)
    customer_notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", foreign_keys=[order_id])
    store_user = relationship("StoreUser", foreign_keys=[store_user_id])
    approved_by_user = relationship("StoreUser", foreign_keys=[approved_by])
    line_items = relationship("ReturnLineItem", back_populates="return_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ReturnRequest {self.return_number}>"


class ReturnLineItem(Base):
    """Individual item being returned."""
    __tablename__ = "return_line_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    return_request_id = Column(String(36), ForeignKey("return_requests.id"), nullable=False, index=True)
    order_item_id = Column(String(36), ForeignKey("order_items.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True)

    quantity = Column(Integer, nullable=False)
    unit_price = Column(Integer, nullable=False)  # cents
    total_refund = Column(Integer, nullable=False)  # cents

    reason = Column(String(100), nullable=True)
    condition = Column(String(50), nullable=True)  # new, opened, used, damaged

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    return_request = relationship("ReturnRequest", back_populates="line_items")
    order_item = relationship("OrderItem")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    def __repr__(self):
        return f"<ReturnLineItem product={self.product_id} qty={self.quantity}>"
