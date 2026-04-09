import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class CmsPage(Base):
    """CMS page for the King Cap storefront."""
    __tablename__ = "cms_pages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    og_image = Column(String(500), nullable=True)

    # Publishing
    status = Column(String(50), nullable=False, default="draft")  # draft, published, archived
    template = Column(String(100), nullable=False, default="default")
    published_at = Column(DateTime, nullable=True)

    # Authorship
    created_by = Column(String(36), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sections = relationship("CmsSection", back_populates="page", cascade="all, delete-orphan", order_by="CmsSection.sort_order")

    def __repr__(self):
        return f"<CmsPage {self.slug}>"


class CmsSection(Base):
    """Modular content section within a CMS page."""
    __tablename__ = "cms_sections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    page_id = Column(String(36), ForeignKey("cms_pages.id"), nullable=False, index=True)
    module_type = Column(String(100), nullable=False)  # hero, text_block, product_grid, image_gallery, etc.
    config = Column(Text, nullable=True)  # JSON string of module configuration
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    page = relationship("CmsPage", back_populates="sections")

    def __repr__(self):
        return f"<CmsSection {self.module_type} on page {self.page_id}>"


class CmsNavigation(Base):
    """Navigation menu configuration."""
    __tablename__ = "cms_navigation"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    location = Column(String(100), nullable=False, index=True)  # header, footer, sidebar
    items = Column(Text, nullable=True)  # JSON string of navigation items

    # Timestamps
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CmsNavigation {self.location}>"


class CmsMedia(Base):
    """Uploaded media files for the CMS."""
    __tablename__ = "cms_media"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    mime_type = Column(String(100), nullable=True)
    size = Column(Integer, nullable=True)  # bytes
    alt = Column(String(255), nullable=True)
    folder = Column(String(255), nullable=True, index=True)

    # Authorship
    uploaded_by = Column(String(36), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CmsMedia {self.filename}>"
