import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class BrandAsset(Base):
    """Assets belonging to a Brand - logos, PDFs, images, or scraped data."""
    __tablename__ = "brand_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id = Column(String(36), ForeignKey("brands.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # 'logo', 'pdf', 'image', 'scraped_data'
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    scraped_data = Column(JSON, nullable=True)  # For AI-scraped brand info
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    brand = relationship("Brand", back_populates="brand_assets")

    def __repr__(self):
        return f"<BrandAsset {self.type} for brand {self.brand_id}>"
