"""
SQLAlchemy ORM model for the chat_rooms table.
chat_mode: 'bot' (AI handles chat) | 'human' (agent has taken over)
status:    'open' | 'closed'
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_name = Column(String(100), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    assigned_agent_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    chat_mode = Column(String(10), nullable=False, default="bot")    # bot | human
    status = Column(String(10), nullable=False, default="open")       # open | closed
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # relationships
    creator = relationship(
        "User", foreign_keys=[created_by], back_populates="created_rooms"
    )
    assigned_agent = relationship(
        "User", foreign_keys=[assigned_agent_id], back_populates="assigned_rooms"
    )
    messages = relationship(
        "Message", back_populates="room", cascade="all, delete-orphan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ChatRoom id={self.id} name={self.room_name!r} mode={self.chat_mode!r}>"

