"""
Quick test: embed a question and show the top results from Qdrant.
Run from the backend/ directory:

    python scripts/search_knowledge.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from app.services.knowledge_service import search_knowledge  # noqa: E402

QUESTION = "I forgot my password. How can I log in?"
print(f"Question: {QUESTION}\n")

results = search_knowledge(QUESTION, limit=3)

if not results:
    print("No results found.")
else:
    for i, r in enumerate(results, 1):
        print(f"Result {i}  (score={r['score']})")
        print(f"  Q: {r['question']}")
        print(f"  A: {r['answer']}")
        print()

