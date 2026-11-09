"""
One-time setup: create the Qdrant vector collection for support knowledge.
Run from the backend/ directory:

    python scripts/create_collection.py
"""

import os
import sys
from pathlib import Path

# Allow running from the backend/ folder
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION = os.getenv("QDRANT_COLLECTION", "support_knowledge_embedding_2")
VECTOR_SIZE = int(os.getenv("GEMINI_EMBEDDING_DIM", "768"))

if not QDRANT_URL or not QDRANT_API_KEY:
    raise EnvironmentError("QDRANT_URL and QDRANT_API_KEY must be set in .env")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

if client.collection_exists(COLLECTION):
    print(f"Collection '{COLLECTION}' already exists — skipping.")
else:
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=qdrant_models.VectorParams(
            size=VECTOR_SIZE,
            distance=qdrant_models.Distance.COSINE,
        ),
    )
    print(f"Collection '{COLLECTION}' created (dim={VECTOR_SIZE}, COSINE).")

collection_info = client.get_collection(COLLECTION)
if "embedding_model" not in (collection_info.payload_schema or {}):
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="embedding_model",
        field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        wait=True,
    )
    print("Created keyword index for embedding_model.")

if "document_id" not in (collection_info.payload_schema or {}):
    client.create_payload_index(
        collection_name=COLLECTION,
        field_name="document_id",
        field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
        wait=True,
    )
    print("Created keyword index for document_id.")

print("Current collections:", [c.name for c in client.get_collections().collections])

