import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class CartItem(Base):
    """Shopping cart item for store customers or anonymous sessions."""
    __tablename__ = "cart_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_user_id = Column(String(36), ForeignKey("store_users.id"), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)  # for anonymous/guest carts
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    variant_id = Column(String(36), ForeignKey("product_variants.id"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Integer, nullable=False)  # cents

    # Customization
    customization = Column(Text, nullable=True)  # JSON string of customization options
    customization_preview = Column(String(500), nullable=True)  # path to preview image

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store_user = relationship("StoreUser", back_populates="cart_items")
    product = relationship("Product")
    variant = relationship("ProductVariant")

    def __repr__(self):
        return f"<CartItem product={self.product_id} qty={self.quantity}>"
