import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class Design(Base):
    """Design with customer and brand as simple text fields for filtering/tracking."""
    __tablename__ = "designs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_name = Column(String(255), nullable=False, index=True)  # Text field for filtering
    brand_name = Column(String(255), nullable=False, index=True)  # Text field for filtering and prompts
    design_name = Column(String(255), nullable=True)  # Optional custom name
    design_number = Column(Integer, nullable=False)
    current_version = Column(Integer, nullable=False, default=1)
    hat_style = Column(String(100), nullable=False)
    material = Column(String(100), nullable=False)
    crown_color = Column(String(100), nullable=True)  # Color of the hat crown
    visor_color = Column(String(100), nullable=True)  # Color of the visor
    structure = Column(String(50), nullable=True)  # "structured" or "unstructured"
    closure = Column(String(50), nullable=True)  # "snapback", "metal_slider_buckle", "velcro_strap"
    style_directions = Column(String(500), nullable=False)  # Comma-separated list (up to 3)
    custom_description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    approval_status = Column(String(50), nullable=False, default="pending")  # pending, approved, rejected
    shared_with_team = Column(Boolean, nullable=False, default=False)
    design_type = Column(String(50), nullable=False, default="ai_generated")  # "ai_generated" or "custom"
    reference_hat_path = Column(String(500), nullable=True)  # Path to reference hat image for custom designs
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship("User", back_populates="designs")
    versions = relationship("DesignVersion", back_populates="design", cascade="all, delete-orphan")
    chats = relationship("DesignChat", back_populates="design", cascade="all, delete-orphan")
    quote = relationship("DesignQuote", back_populates="design", uselist=False, cascade="all, delete-orphan")
    location_logos = relationship("DesignLocationLogo", back_populates="design", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Design #{self.design_number} for {self.brand_name}>"


class DesignVersion(Base):
    __tablename__ = "design_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_id = Column(String(36), ForeignKey("designs.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    prompt = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    generation_status = Column(String(50), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    design = relationship("Design", back_populates="versions")

    def __repr__(self):
        return f"<DesignVersion v{self.version_number} of design {self.design_id}>"


class DesignChat(Base):
    __tablename__ = "design_chats"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_id = Column(String(36), ForeignKey("designs.id"), nullable=False, index=True)
    version_id = Column(String(36), ForeignKey("design_versions.id"), nullable=True)
    message = Column(Text, nullable=False)
    is_user = Column(Boolean, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    design = relationship("Design", back_populates="chats")

    def __repr__(self):
        return f"<DesignChat {'user' if self.is_user else 'ai'} for design {self.design_id}>"


class DesignQuote(Base):
    """Quote associated with a design - stores quote parameters and calculated results."""
    __tablename__ = "design_quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_id = Column(String(36), ForeignKey("designs.id"), nullable=False, unique=True, index=True)

    # Quote type
    quote_type = Column(String(20), nullable=False)  # "domestic" or "overseas"

    # Common fields
    quantity = Column(Integer, nullable=False)
    front_decoration = Column(String(100), nullable=True)
    left_decoration = Column(String(100), nullable=True)
    right_decoration = Column(String(100), nullable=True)
    back_decoration = Column(String(100), nullable=True)

    # Domestic-specific fields
    style_number = Column(String(50), nullable=True)
    shipping_speed = Column(String(100), nullable=True)
    include_rope = Column(Boolean, nullable=True, default=False)
    num_dst_files = Column(Integer, nullable=True, default=1)

    # Overseas-specific fields
    hat_type = Column(String(50), nullable=True)
    visor_decoration = Column(String(100), nullable=True)
    design_addons = Column(Text, nullable=True)  # JSON string of add-ons list
    accessories = Column(Text, nullable=True)    # JSON string of accessories list
    shipping_method = Column(String(100), nullable=True)

    # Cached calculation results (for quick display)
    cached_price_breaks = Column(Text, nullable=True)  # JSON string of price breaks
    cached_total = Column(Integer, nullable=True)      # Total in cents
    cached_per_piece = Column(Integer, nullable=True)  # Per-piece in cents

    # Metadata
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    design = relationship("Design", back_populates="quote")
    created_by = relationship("User")

    def __repr__(self):
        return f"<DesignQuote {self.quote_type} for design {self.design_id}>"


class DesignLocationLogo(Base):
    """Logo specification for a specific location on a custom design."""
    __tablename__ = "design_location_logos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_id = Column(String(36), ForeignKey("designs.id"), nullable=False, index=True)
    location = Column(String(50), nullable=False)  # "front", "left", "right", "back", "visor"
    logo_path = Column(String(500), nullable=False)  # Path to uploaded logo file
    logo_filename = Column(String(255), nullable=False)  # Original filename
    decoration_method = Column(String(100), nullable=False)  # embroidery, screen_print, patch, etc.
    size = Column(String(50), nullable=False)  # "small", "medium", "large", or "custom"
    size_details = Column(String(100), nullable=True)  # Optional: specific dimensions like "3x2 inches"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    design = relationship("Design", back_populates="location_logos")

    def __repr__(self):
        return f"<DesignLocationLogo {self.location} for design {self.design_id}>"
