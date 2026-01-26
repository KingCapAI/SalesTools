import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    image = Column(String(500), nullable=True)
    team_id = Column(String(36), ForeignKey("teams.id"), nullable=True)
    role = Column(String(50), nullable=False, default="member")
    provider = Column(String(50), nullable=False)  # 'microsoft'
    provider_account_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    # Relationships
    team = relationship("Team", back_populates="users")
    customers = relationship("Customer", back_populates="created_by")
    brands = relationship("Brand", back_populates="created_by")
    designs = relationship("Design", back_populates="created_by")

    def __repr__(self):
        return f"<User {self.email}>"
