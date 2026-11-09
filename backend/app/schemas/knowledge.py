"""Schemas for admin-managed RAG knowledge documents."""

from datetime import datetime

from pydantic import BaseModel



class KnowledgeDocumentResponse(BaseModel):
    id: str
    filename: str
    chunks: int
    uploaded_at: datetime | None = None


class KnowledgeDocumentDeleteResponse(BaseModel):
    deleted: bool
