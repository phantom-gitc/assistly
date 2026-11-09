"""Admin-only endpoints for agents, conversations, and RAG knowledge."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_admin
from app.models.chat_room import ChatRoom
from app.models.user import User
from app.schemas.chat_room import ChatRoomResponse
from app.schemas.knowledge import KnowledgeDocumentDeleteResponse, KnowledgeDocumentResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.document_service import (
    MAX_FILE_BYTES,
    SUPPORTED_EXTENSIONS,
    delete_document,
    extract_document_text,
    index_document,
    list_documents,
    split_into_chunks,
)
from app.routers.chat import manager

router = APIRouter(prefix="/admin", tags=["Admin"])
logger = logging.getLogger(__name__)

_pwd = PasswordHash.recommended()


# ── Agent management ──────────────────────────────────────────────────────────

@router.post("/agents", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: UserCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a new support agent account."""
    existing = (
        db.query(User)
        .filter((User.username == payload.username) | (User.email == payload.email))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    agent = User(
        username=payload.username,
        email=payload.email,
        password=_pwd.hash(payload.password),
        role="agent",
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/agents", response_model=list[UserResponse])
def list_agents(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return all agent accounts."""
    return db.query(User).filter(User.role == "agent").order_by(User.id.desc()).all()


@router.get("/agents/{agent_id}", response_model=UserResponse)
def get_agent(
    agent_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return a single agent by ID."""
    agent = db.query(User).filter(User.id == agent_id, User.role == "agent").first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.put("/agents/{agent_id}/activate", response_model=UserResponse)
def activate_agent(
    agent_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Re-activate a previously deactivated agent."""
    agent = db.query(User).filter(User.id == agent_id, User.role == "agent").first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent is already active")

    agent.is_active = True
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/agents/{agent_id}/deactivate", response_model=UserResponse)
def deactivate_agent(
    agent_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Deactivate an agent.
    All rooms assigned to them are unassigned and reverted to bot mode.
    """
    agent = db.query(User).filter(User.id == agent_id, User.role == "agent").first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent is already inactive")

    try:
        agent.is_active = False
        db.query(ChatRoom).filter(ChatRoom.assigned_agent_id == agent_id).update(
            {ChatRoom.assigned_agent_id: None, ChatRoom.chat_mode: "bot"},
            synchronize_session=False,
        )
        db.commit()
        db.refresh(agent)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate agent",
        )
    return agent


# ── Room management (admin overview) ─────────────────────────────────────────

@router.get("/rooms", response_model=list[ChatRoomResponse])
def list_all_rooms(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Return all chat rooms (admin only)."""
    return db.query(ChatRoom).order_by(ChatRoom.id.desc()).all()


@router.put("/rooms/{room_id}/assign/{agent_id}", response_model=ChatRoomResponse)
def assign_agent_to_room(
    room_id: int,
    agent_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Assign a support agent to a chat room."""
    room = db.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found")

    agent = db.query(User).filter(User.id == agent_id, User.role == "agent").first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not agent.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot assign inactive agent")

    room.assigned_agent_id = agent_id
    db.commit()
    db.refresh(room)
    return room


@router.put("/rooms/{room_id}/close", response_model=ChatRoomResponse)
def close_room(
    room_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Close a chat room."""
    room = db.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found")
    if room.status == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is already closed")

    room.status = "closed"
    db.commit()
    db.refresh(room)
    return room


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Permanently delete a conversation and its message history."""
    room = db.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat room not found")
    await manager.close_room(room_id)
    try:
        db.delete(room)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Could not delete chat room %s", room_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The conversation could not be deleted.",
        ) from exc
    return None


@router.get(
    "/knowledge/documents",
    response_model=list[KnowledgeDocumentResponse],
)
def get_knowledge_documents(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List documents currently indexed for AI support answers."""
    try:
        return list_documents(db)
    except Exception as exc:
        logger.exception("Could not list indexed knowledge documents")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The knowledge library is temporarily unavailable.",
        ) from exc


@router.post(
    "/knowledge/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_knowledge_document(
    file: UploadFile = File(...),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Extract, chunk, embed, and index an uploaded company document."""
    raw_filename = (file.filename or "").replace("\\", "/")
    filename = Path(raw_filename).name
    suffix = Path(filename).suffix.lower()
    if not filename or suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Choose a PDF, TXT, or Markdown file.",
        )

    try:
        data = file.file.read(MAX_FILE_BYTES + 1)
    finally:
        file.file.close()

    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected file is empty.",
        )
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Files must be 10 MB or smaller.",
        )

    try:
        text = extract_document_text(filename, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Could not extract uploaded document text")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="We couldn’t read this document. Check the file and try again.",
        ) from exc

    document_id = str(uuid.uuid4())
    chunks = split_into_chunks(text)
    try:
        result = index_document(db, document_id, filename, chunks, admin.id)
        return result
    except Exception as exc:
        logger.exception("Could not index uploaded knowledge document")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document could not be added to the knowledge library. Try again later.",
        ) from exc


@router.delete(
    "/knowledge/documents/{document_id}",
    response_model=KnowledgeDocumentDeleteResponse,
)
def remove_knowledge_document(
    document_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Remove all indexed chunks for one uploaded company document."""
    try:
        deleted = delete_document(db, str(document_id))
    except Exception as exc:
        logger.exception("Could not remove knowledge document %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The knowledge library is temporarily unavailable.",
        ) from exc
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge document not found.",
        )
    return {"deleted": True}

