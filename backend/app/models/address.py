import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Address(Base):
    """Shipping/billing address for store customers."""
    __tablename__ = "addresses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_user_id = Column(String(36), ForeignKey("store_users.id"), nullable=False, index=True)
    label = Column(String(100), nullable=True)  # e.g. "Home", "Office", "Warehouse"
    is_default = Column(Boolean, nullable=False, default=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    company = Column(String(255), nullable=True)
    line1 = Column(String(255), nullable=False)
    line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(2), nullable=False, default="US")
    phone = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store_user = relationship("StoreUser", back_populates="addresses")

    def __repr__(self):
        return f"<Address {self.label or self.line1} for user {self.store_user_id}>"
