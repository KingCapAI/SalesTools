from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from ..database import Base


class SiteContent(Base):
    """Editable JSON content for internal HQ pages (e.g. the marketing calendar).

    One row per content key. The payload is stored as a JSON string so pages can
    evolve their own schema without a migration.
    """
    __tablename__ = "site_content"

    key = Column(String(100), primary_key=True)
    data = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)  # editor's email

    def __repr__(self):
        return f"<SiteContent {self.key}>"
