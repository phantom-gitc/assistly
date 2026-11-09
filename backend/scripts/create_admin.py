"""
Seed an admin user directly in the database.
Run once after `create_tables()` has been called:

    python scripts/create_admin.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")

from pwdlib import PasswordHash  # noqa: E402

from app.core.database import SessionLocal, create_tables  # noqa: E402
from app.models.user import User  # noqa: E402

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

if not ADMIN_PASSWORD:
    raise EnvironmentError("Set ADMIN_PASSWORD in .env before running this script.")

create_tables()

pwd = PasswordHash.recommended()
db = SessionLocal()

try:
    existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if existing:
        print(f"Admin '{ADMIN_EMAIL}' already exists — skipping.")
    else:
        admin = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            password=pwd.hash(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Admin created: id={admin.id}  username={admin.username}  email={admin.email}")
finally:
    db.close()

