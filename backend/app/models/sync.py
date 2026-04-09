import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, UniqueConstraint
from ..database import Base


class SyncLog(Base):
    """Log of sync operations with external integrations (BigCommerce, Pipedrive)."""
    __tablename__ = "sync_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration = Column(String(100), nullable=False, index=True)  # bigcommerce, pipedrive
    entity_type = Column(String(100), nullable=False, index=True)  # product, order, customer, etc.
    entity_id = Column(String(36), nullable=True, index=True)  # local entity id
    external_id = Column(String(100), nullable=True, index=True)  # external system id
    direction = Column(String(20), nullable=False)  # inbound, outbound
    status = Column(String(50), nullable=False, index=True)  # success, error, skipped
    error_message = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)  # JSON string of request/response data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<SyncLog {self.integration}/{self.entity_type} {self.direction} {self.status}>"


class SyncCursor(Base):
    """Tracks the last sync position for incremental syncing."""
    __tablename__ = "sync_cursors"
    __table_args__ = (
        UniqueConstraint("integration", "entity_type", name="uq_sync_cursor_integration_entity"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    integration = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    last_synced_at = Column(DateTime, nullable=True)
    last_external_id = Column(String(100), nullable=True)
    cursor_data = Column(Text, nullable=True)  # JSON string of additional cursor data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SyncCursor {self.integration}/{self.entity_type}>"
