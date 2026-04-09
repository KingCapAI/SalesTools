"""Design request models: tracked, versioned design workflow system."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class DesignRequest(Base):
    """Design request — a 'job ticket' from sales team to design team."""
    __tablename__ = "design_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_number = Column(String(50), unique=True, nullable=False, index=True)

    # Status & priority
    status = Column(String(50), nullable=False, default="submitted", index=True)
    priority = Column(String(20), nullable=False, default="normal")

    # Who
    requested_by_id = Column(String(36), ForeignKey("store_users.id"), nullable=False, index=True)
    assigned_to_id = Column(String(36), ForeignKey("store_users.id"), nullable=True, index=True)
    customer_id = Column(String(36), ForeignKey("store_users.id"), nullable=True)
    customer_name = Column(String(255), nullable=False, default="")
    brand_name = Column(String(255), nullable=False, default="")

    # What
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    design_type = Column(String(50), nullable=False, default="new_design")
    hat_style = Column(String(100), nullable=True)
    hat_color = Column(String(100), nullable=True)
    decoration_locations = Column(Text, nullable=True)  # JSON list
    decoration_methods = Column(Text, nullable=True)  # JSON list

    # Links
    linked_sample_request_id = Column(String(36), ForeignKey("sample_requests.id"), nullable=True, index=True)
    linked_design_id = Column(String(36), ForeignKey("designs.id"), nullable=True)
    linked_quote_id = Column(String(36), ForeignKey("quotes.id"), nullable=True)
    art_id = Column(String(100), nullable=True)

    # Dates
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Notes
    internal_notes = Column(Text, nullable=True)

    # Relationships
    requested_by = relationship("StoreUser", foreign_keys=[requested_by_id])
    assigned_to = relationship("StoreUser", foreign_keys=[assigned_to_id])
    customer = relationship("StoreUser", foreign_keys=[customer_id])
    linked_sample_request = relationship("SampleRequest", foreign_keys=[linked_sample_request_id])
    linked_design = relationship("Design", foreign_keys=[linked_design_id])
    linked_quote = relationship("Quote", foreign_keys=[linked_quote_id])
    versions = relationship("DesignRequestVersion", back_populates="design_request", cascade="all, delete-orphan", order_by="DesignRequestVersion.version_number")
    comments = relationship("DesignRequestComment", back_populates="design_request", cascade="all, delete-orphan", order_by="DesignRequestComment.created_at")
    activities = relationship("DesignRequestActivity", back_populates="design_request", cascade="all, delete-orphan", order_by="DesignRequestActivity.created_at.desc()")

    def __repr__(self):
        return f"<DesignRequest {self.request_number} status={self.status}>"


class DesignRequestVersion(Base):
    """A design iteration uploaded by the design team."""
    __tablename__ = "design_request_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_request_id = Column(String(36), ForeignKey("design_requests.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=False, default="png")
    notes = Column(String(1000), nullable=True)
    is_production_file = Column(String(10), nullable=False, default="false")  # "true" for production files
    uploaded_by_id = Column(String(36), ForeignKey("store_users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    design_request = relationship("DesignRequest", back_populates="versions")
    uploaded_by = relationship("StoreUser", foreign_keys=[uploaded_by_id])

    def __repr__(self):
        return f"<DesignRequestVersion v{self.version_number} of {self.design_request_id}>"


class DesignRequestComment(Base):
    """Threaded communication between salesperson and designer."""
    __tablename__ = "design_request_comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_request_id = Column(String(36), ForeignKey("design_requests.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("store_users.id"), nullable=False)
    message = Column(Text, nullable=False)
    attachment_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    design_request = relationship("DesignRequest", back_populates="comments")
    user = relationship("StoreUser", foreign_keys=[user_id])

    def __repr__(self):
        return f"<DesignRequestComment by {self.user_id}>"


class DesignRequestActivity(Base):
    """Audit log for design request state changes."""
    __tablename__ = "design_request_activities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    design_request_id = Column(String(36), ForeignKey("design_requests.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("store_users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON blob
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    design_request = relationship("DesignRequest", back_populates="activities")
    user = relationship("StoreUser", foreign_keys=[user_id])

    def __repr__(self):
        return f"<DesignRequestActivity {self.action}>"
