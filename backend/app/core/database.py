"""
Database engine, session factory, and declarative base.
All database interaction goes through the SessionLocal factory.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # auto-reconnect on stale connections
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def create_tables() -> None:
    """Create all tables that do not exist yet."""
    Base.metadata.create_all(bind=engine)


def test_connection() -> str:
    """Return DB server version — used by /health endpoint."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        return result.scalar()

