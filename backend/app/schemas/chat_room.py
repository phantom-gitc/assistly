"""
Pydantic schemas for ChatRoom requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class ChatRoomCreate(BaseModel):
    room_name: str = Field(..., min_length=1, max_length=100)


# ── Response schemas ──────────────────────────────────────────────────────────

class ChatRoomResponse(BaseModel):
    id: int
    room_name: str
    created_by: int
    assigned_agent_id: int | None
    chat_mode: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

