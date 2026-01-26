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
    style_directions = Column(String(500), nullable=False)  # Comma-separated list (up to 3)
    custom_description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    approval_status = Column(String(50), nullable=False, default="pending")  # pending, approved, rejected
    shared_with_team = Column(Boolean, nullable=False, default=False)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by = relationship("User", back_populates="designs")
    versions = relationship("DesignVersion", back_populates="design", cascade="all, delete-orphan")
    chats = relationship("DesignChat", back_populates="design", cascade="all, delete-orphan")

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
