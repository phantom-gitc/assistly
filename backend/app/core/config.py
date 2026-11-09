"""
Application configuration loaded from environment variables.
All secrets and service URLs are read from a .env file.
"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=BACKEND_DIR / ".env")


class Settings:
    # ── Application ──────────────────────────────────────────
    APP_TITLE: str = "Assistly API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    # ── Gemini AI ────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    GEMINI_EMBEDDING_MODEL: str = os.getenv(
        "GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"
    )
    GEMINI_EMBEDDING_DIM: int = int(os.getenv("GEMINI_EMBEDDING_DIM", "768"))

    # ── Qdrant ───────────────────────────────────────────────
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = os.getenv(
        "QDRANT_COLLECTION", "support_knowledge_embedding_2"
    )

    # ── CORS ─────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]

    def validate(self) -> None:
        """Raise at startup if any required secret is missing."""
        required = {
            "DATABASE_URL": self.DATABASE_URL,
            "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
            "GEMINI_API_KEY": self.GEMINI_API_KEY,
            "QDRANT_URL": self.QDRANT_URL,
            "QDRANT_API_KEY": self.QDRANT_API_KEY,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    settings = Settings()
    settings.validate()
    return settings

