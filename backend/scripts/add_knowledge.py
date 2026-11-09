"""
Seed the Qdrant collection with sample FAQ entries.
Run from the backend/ directory:

    python scripts/add_knowledge.py

Add your own FAQs to the `FAQS` list below.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
from google import genai
from google.genai import types
from qdrant_client import QdrantClient
from qdrant_client import models as qdrant_models

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")
EMBEDDING_DIM = int(os.getenv("GEMINI_EMBEDDING_DIM", "768"))
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION = os.getenv("QDRANT_COLLECTION", "support_knowledge_embedding_2")

if not all([GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY]):
    raise EnvironmentError("GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY must be set in .env")

gemini = genai.Client(api_key=GEMINI_API_KEY)
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# ── FAQ knowledge base ────────────────────────────────────────────────────────
# Add, edit, or remove entries here to customise the knowledge base.

FAQS: list[dict] = [
    {
        "question": "How can I reset my password?",
        "answer": (
            "Go to the login page and click 'Forgot Password'. "
            "Enter your registered email address and follow the reset instructions sent to your inbox."
        ),
        "category": "account",
    },
    {
        "question": "How can I contact customer support?",
        "answer": (
            "Open the live chat widget and type your question. "
            "If the AI cannot help you, ask to speak with a human support agent."
        ),
        "category": "support",
    },
    {
        "question": "How do I update my email address?",
        "answer": (
            "Log in and go to Account Settings. "
            "Click 'Change Email', enter your new address, and verify it via the confirmation email."
        ),
        "category": "account",
    },
    {
        "question": "Why can't I log in to my account?",
        "answer": (
            "Check that your email and password are correct. "
            "Make sure Caps Lock is off. "
            "If you have forgotten your password, use the 'Forgot Password' link on the login page."
        ),
        "category": "login",
    },
    {
        "question": "How do I cancel my subscription?",
        "answer": (
            "Go to Account Settings → Subscription and click 'Cancel Subscription'. "
            "Your access will continue until the end of the current billing period."
        ),
        "category": "billing",
    },
    {
        "question": "What payment methods do you accept?",
        "answer": (
            "We accept all major credit and debit cards (Visa, Mastercard, Amex) "
            "as well as PayPal and bank transfers for annual plans."
        ),
        "category": "billing",
    },
    {
        "question": "How do I request a refund?",
        "answer": (
            "Refund requests must be submitted within 14 days of the charge. "
            "Contact support through the live chat or email billing@example.com with your order number."
        ),
        "category": "billing",
    },
    {
        "question": "Is my data secure?",
        "answer": (
            "Yes. All data is encrypted in transit (TLS) and at rest (AES-256). "
            "We are GDPR-compliant and never sell your data to third parties."
        ),
        "category": "security",
    },
]

# ── Embed and upsert ──────────────────────────────────────────────────────────

points: list[qdrant_models.PointStruct] = []

for idx, faq in enumerate(FAQS, start=1):
    text = f"title: {faq['question']} | text: {faq['answer']}"

    result = gemini.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
    )
    vector = result.embeddings[0].values

    points.append(
        qdrant_models.PointStruct(
            id=idx,
            vector=vector,
            payload={
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq["category"],
                "text": text,
                "embedding_model": EMBEDDING_MODEL,
            },
        )
    )
    print(f"  [{idx}/{len(FAQS)}] Embedded: {faq['question'][:60]}")

qdrant.upsert(collection_name=COLLECTION, points=points, wait=True)
print(f"\nDone — {len(points)} FAQs stored in '{COLLECTION}'.")

