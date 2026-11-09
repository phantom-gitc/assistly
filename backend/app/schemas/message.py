"""
Pydantic schemas for Message requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ── Request schemas ───────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)


# ── Response schemas ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    id: int
    room_id: int
    sender_id: int | None
    sender_type: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}

