"""
FastAPI application entry point.

Start the server:
    uvicorn main:app --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_tables
from app.routers import admin, auth, chat, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup() -> None:
    logger.info("Creating database tables if they do not exist …")
    create_tables()
    logger.info("Application started — %s v%s", settings.APP_TITLE, settings.APP_VERSION)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(admin.router)

# ── Root endpoints ────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
def root():
    return {"message": f"{settings.APP_TITLE} is running", "version": settings.APP_VERSION}


@app.get("/health", tags=["Root"])
def health():
    """Lightweight health check — returns 200 if the server is up."""
    return {"status": "healthy"}

