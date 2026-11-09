"""
Shared FastAPI dependencies (database session generator).
Import get_db in every router that needs a DB session.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it when the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

