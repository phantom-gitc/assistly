"""
SQLAlchemy ORM model for the users table.
Roles: customer | agent | admin
"""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="customer")  # visitor | customer | agent | admin
    is_active = Column(Boolean, nullable=False, default=True)

    # relationships
    created_rooms = relationship(
        "ChatRoom",
        foreign_keys="ChatRoom.created_by",
        back_populates="creator",
        lazy="select",
    )
    assigned_rooms = relationship(
        "ChatRoom",
        foreign_keys="ChatRoom.assigned_agent_id",
        back_populates="assigned_agent",
        lazy="select",
    )
    messages = relationship("Message", back_populates="sender", lazy="select")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"

