"""Order file attachment model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class OrderAttachment(Base):
    """File attached to an order (DST, production art, logo, reference, etc.)."""
    __tablename__ = "order_attachments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False, default="other")  # dst, production_art, logo, reference, other
    uploaded_by_id = Column(String(36), ForeignKey("store_users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="attachments")
    uploaded_by = relationship("StoreUser", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<OrderAttachment {self.file_name} type={self.file_type}>"
