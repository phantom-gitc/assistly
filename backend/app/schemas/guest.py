"""Responses for registration-free visitor chat sessions."""

from pydantic import BaseModel

from app.schemas.chat_room import ChatRoomResponse
from app.schemas.user import UserResponse


class GuestRoomSessionResponse(BaseModel):
    access_token: str
    user: UserResponse
    room: ChatRoomResponse
