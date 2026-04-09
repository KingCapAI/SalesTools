import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class MockupApproval(Base):
    """Mockup approval workflow for custom hat orders."""
    __tablename__ = "mockup_approvals"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    store_user_id = Column(String(36), ForeignKey("store_users.id"), nullable=False, index=True)
    mockup_image_url = Column(String(500), nullable=False)
    version = Column(Integer, nullable=False, default=1)

    # Type: mockup (pre-order digital) or sew_out (post-order factory sample)
    approval_type = Column(String(50), nullable=False, default="mockup")

    # Approval status
    status = Column(String(50), nullable=False, default="pending")  # pending, approved, revision, superseded

    # Notes
    customer_notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)

    # Dates
    responded_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="mockup_approvals")
    store_user = relationship("StoreUser", back_populates="mockup_approvals")

    def __repr__(self):
        return f"<MockupApproval v{self.version} order={self.order_id} status={self.status}>"
