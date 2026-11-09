"""
Knowledge service: embed a question with Gemini and perform
a semantic search against the Qdrant vector store.
"""

from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models

from app.core.config import get_settings

settings = get_settings()

# Initialise clients once at module load
_gemini = genai.Client(api_key=settings.GEMINI_API_KEY)
_qdrant = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)


def search_knowledge(question: str, limit: int = 3) -> list[dict]:
    """
    Convert *question* to a vector embedding, then return the
    *limit* most-relevant FAQ entries from Qdrant.

    Returns a list of dicts with keys: question, answer, category, score.
    """
    # 1. Embed the question
    embed_result = _gemini.models.embed_content(
        model=settings.GEMINI_EMBEDDING_MODEL,
        contents=f"task: search result | query: {question}",
        config=types.EmbedContentConfig(
            output_dimensionality=settings.GEMINI_EMBEDDING_DIM
        ),
    )
    if not embed_result.embeddings or not embed_result.embeddings[0].values:
        raise RuntimeError("Gemini returned no query embedding")
    query_vector = embed_result.embeddings[0].values

    # 2. Search Qdrant
    search_result = _qdrant.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_vector,
        limit=limit,
        with_payload=True,
        query_filter=qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="embedding_model",
                    match=qdrant_models.MatchValue(value=settings.GEMINI_EMBEDDING_MODEL),
                )
            ]
        ),
    )

    # 3. Build and return results
    return [
        {
            "question": (point.payload or {}).get("question", ""),
            "answer": (point.payload or {}).get("answer", ""),
            "category": (point.payload or {}).get("category", ""),
            "score": round(point.score, 4),
        }
        for point in search_result.points
    ]

