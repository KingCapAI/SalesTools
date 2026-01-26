import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.orm import relationship
from ..database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    allowed_apps = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship("User", back_populates="team")

    def __repr__(self):
        return f"<Team {self.name}>"
