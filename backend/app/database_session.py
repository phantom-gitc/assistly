"""
Thin re-export so WebSocket handlers can import SessionLocal
without creating a circular dependency through core/database.py.
"""

from app.core.database import SessionLocal  # noqa: F401

