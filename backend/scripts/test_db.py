"""
Verify that the application can connect to the database.
Run from the backend/ directory:

    python scripts/test_db.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from app.core.database import test_connection  # noqa: E402

try:
    version = test_connection()
    print("Database connection OK")
    print("Server version:", version)
except Exception as exc:
    print("Database connection FAILED:", exc)
    sys.exit(1)

