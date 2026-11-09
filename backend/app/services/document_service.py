"""Extract and index uploaded company documents for support RAG."""

import io
import logging
import uuid
from datetime import datetime, timezone

from google.genai import types
from pypdf import PdfReader
from qdrant_client import models as qdrant_models
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.knowledge_service import _gemini, _qdrant

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_DOCUMENT_CHARS = 200_000
MAX_PDF_PAGES = 100
CHUNK_CHARS = 2800
CHUNK_OVERLAP = 250
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


def extract_document_text(filename: str, data: bytes) -> str:
    """Extract selectable text from a supported PDF or UTF-8 text file."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "pdf":
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("This PDF is password-protected. Upload an unlocked copy.")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError(f"PDFs can contain up to {MAX_PDF_PAGES} pages.")
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix in {"txt", "md"}:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc
    else:
        raise ValueError("Choose a PDF, TXT, or Markdown file.")

    text = "\n".join(line.strip() for line in text.replace("\x00", "").splitlines()).strip()
    if not text:
        raise ValueError("We couldn’t find readable text in this file.")
    if len(text) > MAX_DOCUMENT_CHARS:
        raise ValueError("This document is too long. Keep extracted text under 200,000 characters.")
    return text


def split_into_chunks(text: str) -> list[str]:
    """Split text into overlapping sections without cutting most paragraphs."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + CHUNK_CHARS // 2, end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(start + 1, end - CHUNK_OVERLAP)
    return chunks


def index_document(
    db: Session,
    document_id: str,
    filename: str,
    chunks: list[str],
    admin_id: int,
) -> dict:
    """Save source chunks to PostgreSQL and searchable embeddings to Qdrant."""
    uploaded_at = datetime.now(timezone.utc)
    points = []
    stored_chunks = []
    for index, chunk in enumerate(chunks):
        embedded = _gemini.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=f"title: {filename} | text: {chunk}",
            config=types.EmbedContentConfig(
                output_dimensionality=settings.GEMINI_EMBEDDING_DIM
            ),
        )
        if not embedded.embeddings or not embedded.embeddings[0].values:
            raise RuntimeError("Embedding service returned an empty vector")

        point_id = str(uuid.uuid4())
        points.append(
            qdrant_models.PointStruct(
                id=point_id,
                vector=embedded.embeddings[0].values,
                payload={
                    "question": f"{filename} (section {index + 1})",
                    "answer": chunk,
                    "category": "company_document",
                    "text": f"title: {filename} | text: {chunk}",
                    "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": index,
                    "uploaded_at": uploaded_at.isoformat(),
                },
            )
        )
        stored_chunks.append(
            KnowledgeChunk(
                document_id=document_id,
                chunk_index=index,
                content=chunk,
                qdrant_point_id=point_id,
            )
        )

    document = KnowledgeDocument(
        id=document_id,
        filename=filename,
        uploaded_by=admin_id,
        created_at=uploaded_at,
        chunks=stored_chunks,
    )
    try:
        _qdrant.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points,
            wait=True,
        )
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        try:
            if points:
                _qdrant.delete(
                    collection_name=settings.QDRANT_COLLECTION,
                    points_selector=qdrant_models.PointIdsList(
                        points=[point.id for point in points]
                    ),
                    wait=True,
                )
        except Exception:
            logger.exception("Could not clean up vectors after a failed document upload")
        raise

    return {
        "id": document.id,
        "filename": document.filename,
        "chunks": len(stored_chunks),
        "uploaded_at": document.created_at,
    }


def list_documents(db: Session) -> list[dict]:
    """List indexed source documents from PostgreSQL metadata."""
    rows = (
        db.query(KnowledgeDocument, func.count(KnowledgeChunk.id))
        .outerjoin(KnowledgeChunk, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .group_by(KnowledgeDocument.id)
        .order_by(KnowledgeDocument.created_at.desc())
        .all()
    )
    return [
        {
            "id": document.id,
            "filename": document.filename,
            "chunks": chunk_count,
            "uploaded_at": document.created_at,
        }
        for document, chunk_count in rows
    ]


def delete_document(db: Session, document_id: str) -> bool:
    """Remove source chunks and their Qdrant vectors for one document."""
    document = db.get(KnowledgeDocument, document_id)
    if document is None:
        return False

    point_ids = [chunk.qdrant_point_id for chunk in document.chunks]
    if point_ids:
        _qdrant.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=qdrant_models.PointIdsList(points=point_ids),
            wait=True,
        )
    db.delete(document)
    db.commit()
    return True
