"""
SQLAlchemy ORM model for the messages table.
sender_type: 'customer' | 'agent' | 'ai'
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sender_type = Column(String(10), nullable=False, default="customer")  # customer | agent | ai
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # relationships
    room = relationship("ChatRoom", back_populates="messages")
    sender = relationship("User", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} room={self.room_id} type={self.sender_type!r}>"

