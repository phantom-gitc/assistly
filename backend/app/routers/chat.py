"""
Chat router — customer REST endpoints, agent REST endpoints,
customer WebSocket, and agent WebSocket.

Chat mode lifecycle
-------------------
bot    → AI replies automatically to every customer message.
human  → Agent has taken over; AI is silent.
        Mode reverts to 'bot' when the last agent disconnects.
"""

import asyncio
import json
import logging
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import create_access_token, decode_token, get_current_agent, get_current_user
from app.database_session import SessionLocal
from app.models.chat_room import ChatRoom
from app.models.message import Message
from app.models.user import User
from app.schemas.chat_room import ChatRoomCreate, ChatRoomResponse
from app.schemas.guest import GuestRoomSessionResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.services.ai_service import generate_ai_reply

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])
_password_hash = PasswordHash.recommended()
_guest_start_attempts: dict[str, deque[float]] = defaultdict(deque)
_guest_start_lock = threading.Lock()


def _check_guest_start_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    with _guest_start_lock:
        attempts = _guest_start_attempts[client_ip]
        while attempts and attempts[0] <= now - 60:
            attempts.popleft()
        if len(attempts) >= 8:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait a moment before starting another conversation.",
            )
        attempts.append(now)
        # Bound memory use if a deployment sees many distinct client IPs.
        if len(_guest_start_attempts) > 10_000:
            stale_before = now - 60
            for ip, recent in list(_guest_start_attempts.items()):
                while recent and recent[0] <= stale_before:
                    recent.popleft()
                if not recent:
                    _guest_start_attempts.pop(ip, None)


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket connection manager
# ══════════════════════════════════════════════════════════════════════════════

class ConnectionManager:
    """
    Tracks all active WebSocket connections per chat room.
    Maintains a separate set for agent connections so we know
    when to revert a room from 'human' back to 'bot' mode.
    """

    def __init__(self) -> None:
        self._all: dict[int, set[WebSocket]] = {}
        self._agents: dict[int, set[WebSocket]] = {}

    # ── connect / disconnect ──────────────────────────────────────────────────

    async def connect_customer(self, ws: WebSocket, room_id: int) -> None:
        await ws.accept()
        self._all.setdefault(room_id, set()).add(ws)

    async def connect_agent(self, ws: WebSocket, room_id: int) -> None:
        await ws.accept()
        self._all.setdefault(room_id, set()).add(ws)
        self._agents.setdefault(room_id, set()).add(ws)

    def disconnect_customer(self, ws: WebSocket, room_id: int) -> None:
        self._all.get(room_id, set()).discard(ws)

    def disconnect_agent(self, ws: WebSocket, room_id: int) -> None:
        self._all.get(room_id, set()).discard(ws)
        self._agents.get(room_id, set()).discard(ws)

    def has_agents(self, room_id: int) -> bool:
        return bool(self._agents.get(room_id))

    async def close_room(self, room_id: int) -> None:
        """Disconnect clients before an administrator deletes a room."""
        sockets = list(self._all.get(room_id, set()))
        for websocket in sockets:
            try:
                await websocket.close(code=1001, reason="Conversation deleted")
            except Exception:
                logger.debug("WebSocket already closed for deleted room %s", room_id)
        self._all.pop(room_id, None)
        self._agents.pop(room_id, None)

    # ── broadcast ─────────────────────────────────────────────────────────────

    async def broadcast(self, message: str, room_id: int) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._all.get(room_id, [])):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_customer(ws, room_id)
            self.disconnect_agent(ws, room_id)


manager = ConnectionManager()


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _message_to_dict(msg: Message) -> dict:
    return {
        "id": msg.id,
        "room_id": msg.room_id,
        "sender_id": msg.sender_id,
        "sender_type": msg.sender_type,
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def _require_room(db: Session, room_id: int) -> ChatRoom:
    room = db.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found")
    return room


def _require_open_room(db: Session, room_id: int) -> ChatRoom:
    room = _require_room(db, room_id)
    if room.status == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chat room is closed")
    return room


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMER — REST endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/guest/rooms",
    response_model=GuestRoomSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_guest_room(
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a registration-free, isolated visitor session and first room."""
    client_ip = request.client.host if request.client else "unknown"
    _check_guest_start_rate_limit(client_ip)

    guest_key = uuid.uuid4().hex
    guest = User(
        username=f"visitor_{guest_key[:16]}",
        email=f"visitor-{guest_key}@guest.invalid",
        password=_password_hash.hash(secrets.token_urlsafe(32)),
        role="visitor",
        is_active=True,
    )
    room = ChatRoom(
        room_name="Guest support conversation",
        creator=guest,
        chat_mode="bot",
        status="open",
    )
    db.add(guest)
    db.add(room)
    db.commit()
    db.refresh(guest)
    db.refresh(room)
    return {
        "access_token": create_access_token(guest.id),
        "user": guest,
        "room": room,
    }


@router.post("/rooms", response_model=ChatRoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: ChatRoomCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Customer creates a new chat room."""
    room = ChatRoom(
        room_name=payload.room_name,
        created_by=current_user.id,
        chat_mode="bot",
        status="open",
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.get("/rooms", response_model=list[ChatRoomResponse])
def get_customer_rooms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated customer's conversation history."""
    if current_user.role not in {"customer", "visitor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer access required")
    return (
        db.query(ChatRoom)
        .filter(ChatRoom.created_by == current_user.id)
        .order_by(ChatRoom.id.desc())
        .all()
    )


@router.get("/rooms/{room_id}", response_model=ChatRoomResponse)
def get_room(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a chat room (only the owner may access it)."""
    room = _require_room(db, room_id)
    if room.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return room


@router.get("/rooms/{room_id}/messages", response_model=list[MessageResponse])
def get_messages(
    room_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the message history for a room (owner only)."""
    room = _require_room(db, room_id)
    if room.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return (
        db.query(Message)
        .filter(Message.room_id == room_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )


@router.post("/rooms/{room_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: int,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Customer sends an HTTP (non-WebSocket) message."""
    room = _require_open_room(db, room_id)
    if room.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    msg = Message(
        room_id=room_id,
        sender_id=current_user.id,
        sender_type="customer",
        content=payload.content.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    await manager.broadcast(json.dumps(_message_to_dict(msg)), room_id)

    # Keep HTTP fallback chats useful when the browser's WebSocket is unavailable.
    if room.chat_mode == "bot":
        try:
            ai_text = await asyncio.to_thread(generate_ai_reply, msg.content)
        except Exception:
            logger.exception("AI thread error during HTTP chat (room %s)", room_id)
            ai_text = ""
        if ai_text:
            db.refresh(room)
            if room.chat_mode == "bot" and room.status == "open":
                ai_msg = Message(
                    room_id=room_id,
                    sender_id=None,
                    sender_type="ai",
                    content=ai_text,
                )
                db.add(ai_msg)
                db.commit()
                db.refresh(ai_msg)
                await manager.broadcast(json.dumps(_message_to_dict(ai_msg)), room_id)
    return msg


# ══════════════════════════════════════════════════════════════════════════════
# AGENT — REST endpoints
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/agent/rooms", response_model=list[ChatRoomResponse])
def get_assigned_rooms(
    agent: User = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Return all rooms assigned to the authenticated agent."""
    return (
        db.query(ChatRoom)
        .filter(ChatRoom.assigned_agent_id == agent.id)
        .order_by(ChatRoom.id.desc())
        .all()
    )


@router.get("/agent/rooms/{room_id}/messages", response_model=list[MessageResponse])
def get_agent_messages(
    room_id: int,
    agent: User = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Return message history for a room the agent is assigned to."""
    room = _require_room(db, room_id)
    if agent.role != "admin" and room.assigned_agent_id != agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this room")

    return (
        db.query(Message)
        .filter(Message.room_id == room_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )


@router.post(
    "/agent/rooms/{room_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def agent_send_message(
    room_id: int,
    payload: MessageCreate,
    agent: User = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent sends a reply via HTTP (non-WebSocket)."""
    room = _require_open_room(db, room_id)
    if agent.role != "admin" and room.assigned_agent_id != agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this room")

    msg = Message(
        room_id=room_id,
        sender_id=agent.id,
        sender_type="agent",
        content=payload.content.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    await manager.broadcast(json.dumps(_message_to_dict(msg)), room_id)
    return msg


@router.put("/agent/rooms/{room_id}/takeover", response_model=ChatRoomResponse)
def takeover_room(
    room_id: int,
    agent: User = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent switches the room from bot mode to human mode."""
    room = _require_open_room(db, room_id)
    if agent.role != "admin" and room.assigned_agent_id != agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this room")

    room.chat_mode = "human"
    db.commit()
    db.refresh(room)
    return room


@router.put("/agent/rooms/{room_id}/handback", response_model=ChatRoomResponse)
def handback_room(
    room_id: int,
    agent: User = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent hands the conversation back to the AI bot."""
    room = _require_open_room(db, room_id)
    if agent.role != "admin" and room.assigned_agent_id != agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this room")

    room.chat_mode = "bot"
    db.commit()
    db.refresh(room)
    return room


@router.get("/agent/rooms/{room_id}/status", response_model=ChatRoomResponse)
def get_room_status(
    room_id: int,
    agent: User = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Return the current status of a chat room."""
    room = _require_room(db, room_id)
    if agent.role != "admin" and room.assigned_agent_id != agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this room")
    return room


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOMER WebSocket
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/{room_id}")
async def customer_websocket(
    websocket: WebSocket,
    room_id: int,
    token: str,
):
    """
    Real-time WebSocket endpoint for customers.
    - Authenticates via ?token= query parameter.
    - Saves each message, then either waits for an agent reply
      (human mode) or generates an AI reply (bot mode).
    """
    db = SessionLocal()
    connected = False

    try:
        # 1. Authenticate
        try:
            user_id = decode_token(token)
        except HTTPException:
            await websocket.close(code=1008)
            return

        # 2. Verify room ownership
        room = db.get(ChatRoom, room_id)
        if not room or room.created_by != user_id:
            await websocket.close(code=1008)
            return
        if room.status == "closed":
            await websocket.close(code=1000)
            return

        await manager.connect_customer(websocket, room_id)
        connected = True

        while True:
            raw = await websocket.receive_text()
            content = raw.strip()
            if not content:
                continue

            # 3. Persist customer message
            customer_msg = Message(
                room_id=room_id,
                sender_id=user_id,
                sender_type="customer",
                content=content,
            )
            db.add(customer_msg)
            db.commit()
            db.refresh(customer_msg)

            # 4. Broadcast to everyone in the room (including agent if connected)
            await manager.broadcast(json.dumps(_message_to_dict(customer_msg)), room_id)

            # 5. Refresh room to get latest chat_mode
            db.refresh(room)
            if room.chat_mode == "human":
                # Agent is handling — do not generate AI reply
                continue

            # 6. Generate AI reply (runs in a thread to avoid blocking the event loop)
            try:
                ai_text = await asyncio.to_thread(generate_ai_reply, content)
            except Exception:
                logger.exception("AI thread error")
                ai_text = ""

            if not ai_text:
                ai_text = (
                    "Sorry, I couldn't generate a response right now. "
                    "Please contact a support agent."
                )

            # 7. Re-check mode — agent may have taken over while AI was generating
            db.refresh(room)
            if room.chat_mode == "human":
                continue

            # 8. Persist and broadcast AI reply
            ai_msg = Message(
                room_id=room_id,
                sender_id=None,
                sender_type="ai",
                content=ai_text,
            )
            db.add(ai_msg)
            db.commit()
            db.refresh(ai_msg)

            await manager.broadcast(json.dumps(_message_to_dict(ai_msg)), room_id)

    except WebSocketDisconnect:
        pass

    except Exception:
        logger.exception("Unexpected error in customer WebSocket (room %s)", room_id)
        db.rollback()

    finally:
        if connected:
            manager.disconnect_customer(websocket, room_id)
        db.close()


# ══════════════════════════════════════════════════════════════════════════════
# AGENT WebSocket
# ══════════════════════════════════════════════════════════════════════════════

@router.websocket("/ws/agent/{room_id}")
async def agent_websocket(
    websocket: WebSocket,
    room_id: int,
    token: str,
):
    """
    Real-time WebSocket endpoint for agents.
    - Authenticates and verifies agent role.
    - When the last agent disconnects, chat_mode reverts to 'bot'.
    """
    db = SessionLocal()
    connected = False

    try:
        # 1. Authenticate
        try:
            user_id = decode_token(token)
        except HTTPException:
            await websocket.close(code=1008)
            return

        # 2. Verify agent/admin role
        agent = db.get(User, user_id)
        if not agent or agent.role not in ("agent", "admin"):
            await websocket.close(code=1008)
            return
        if not agent.is_active:
            await websocket.close(code=1008)
            return

        # 3. Verify room exists and agent is assigned
        room = db.get(ChatRoom, room_id)
        if not room:
            await websocket.close(code=1008)
            return
        if agent.role != "admin" and room.assigned_agent_id != agent.id:
            await websocket.close(code=1008)
            return

        await manager.connect_agent(websocket, room_id)
        connected = True

        while True:
            raw = await websocket.receive_text()
            content = raw.strip()
            if not content:
                continue

            # 4. Persist agent message
            agent_msg = Message(
                room_id=room_id,
                sender_id=agent.id,
                sender_type="agent",
                content=content,
            )
            db.add(agent_msg)
            db.commit()
            db.refresh(agent_msg)

            # 5. Broadcast to everyone in the room
            await manager.broadcast(json.dumps(_message_to_dict(agent_msg)), room_id)

    except WebSocketDisconnect:
        pass

    except Exception:
        logger.exception("Unexpected error in agent WebSocket (room %s)", room_id)
        db.rollback()

    finally:
        if connected:
            manager.disconnect_agent(websocket, room_id)
            # Revert to bot mode if no agents remain in this room
            if not manager.has_agents(room_id):
                try:
                    room = db.get(ChatRoom, room_id)
                    if room and room.chat_mode == "human":
                        room.chat_mode = "bot"
                        db.commit()
                except Exception:
                    logger.exception("Failed to revert room %s to bot mode", room_id)
        db.close()


