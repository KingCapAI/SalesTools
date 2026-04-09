import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from ..database import Base


class ProductCategory(Base):
    """Product category with optional parent for hierarchy."""
    __tablename__ = "product_categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    image = Column(String(500), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    parent_id = Column(String(36), ForeignKey("product_categories.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent = relationship("ProductCategory", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<ProductCategory {self.name}>"


class Product(Base):
    """Hat product in the King Cap catalog."""
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    style_number = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    collection = Column(String(255), nullable=True, index=True)

    # Production
    production_type = Column(String(50), nullable=False, default="domestic")  # domestic, overseas

    # Pricing (in cents)
    base_price = Column(Integer, nullable=False)
    compare_at_price = Column(Integer, nullable=True)

    # Hat specifications
    panel_count = Column(String(20), nullable=True)  # e.g. "5", "6", "7"
    crown_type = Column(String(100), nullable=True)
    closure_type = Column(String(100), nullable=True)
    visor_type = Column(String(100), nullable=True)
    material = Column(String(255), nullable=True)
    sweatband = Column(String(100), nullable=True)
    profile = Column(String(50), nullable=True)  # low, mid, high
    is_trucker = Column(Boolean, nullable=False, default=False)
    is_perforated = Column(Boolean, nullable=False, default=False)

    # Visibility & features
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_featured = Column(Boolean, nullable=False, default=False)
    is_customizable = Column(Boolean, nullable=False, default=True)
    min_order_qty = Column(Integer, nullable=False, default=1)

    # SEO
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)

    # BigCommerce sync
    bc_item_id = Column(String(100), unique=True, nullable=True, index=True)
    bc_synced_at = Column(DateTime, nullable=True)

    # Category
    category_id = Column(String(36), ForeignKey("product_categories.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("ProductCategory", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    colorways = relationship("ProductColorway", back_populates="product", cascade="all, delete-orphan")
    decoration_options = relationship("DecorationOption", back_populates="product", cascade="all, delete-orphan")
    pricing_rules = relationship("PricingRule", back_populates="product")

    def __repr__(self):
        return f"<Product {self.style_number} - {self.name}>"


class ProductColorway(Base):
    """Color combination for a product."""
    __tablename__ = "product_colorways"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    crown_color = Column(String(100), nullable=True)
    visor_color = Column(String(100), nullable=True)
    mesh_color = Column(String(100), nullable=True)
    sweatband_color = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="colorways")
    variants = relationship("ProductVariant", back_populates="colorway")
    images = relationship("ProductImage", back_populates="colorway")

    def __repr__(self):
        return f"<ProductColorway {self.name} for product {self.product_id}>"


class ProductVariant(Base):
    """SKU-level variant (colorway + size combination)."""
    __tablename__ = "product_variants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    colorway_id = Column(String(36), ForeignKey("product_colorways.id"), nullable=True, index=True)
    size = Column(String(50), nullable=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    stock_qty = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    # BigCommerce sync
    bc_item_variant_id = Column(String(100), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="variants")
    colorway = relationship("ProductColorway", back_populates="variants")

    def __repr__(self):
        return f"<ProductVariant {self.sku}>"


class ProductImage(Base):
    """Product image with optional colorway association."""
    __tablename__ = "product_images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    alt = Column(String(255), nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)
    is_primary = Column(Boolean, nullable=False, default=False)
    colorway_id = Column(String(36), ForeignKey("product_colorways.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="images")
    colorway = relationship("ProductColorway", back_populates="images")

    def __repr__(self):
        return f"<ProductImage {self.url} for product {self.product_id}>"


class DecorationOption(Base):
    """Available decoration method at a specific location for a product."""
    __tablename__ = "decoration_options"
    __table_args__ = (
        UniqueConstraint("product_id", "location", "method", name="uq_decoration_product_location_method"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    location = Column(String(100), nullable=False)  # front, left, right, back, visor
    method = Column(String(100), nullable=False)  # embroidery, screen_print, patch, heat_transfer, etc.
    is_available = Column(Boolean, nullable=False, default=True)
    additional_cost = Column(Integer, nullable=False, default=0)  # cents

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="decoration_options")

    def __repr__(self):
        return f"<DecorationOption {self.method} at {self.location} for product {self.product_id}>"
