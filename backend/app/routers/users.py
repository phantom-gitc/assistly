"""
Users router — public self-registration endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

_pwd = PasswordHash.recommended()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new customer account."""
    existing = (
        db.query(User)
        .filter((User.username == payload.username) | (User.email == payload.email))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    new_user = User(
        username=payload.username,
        email=payload.email,
        password=_pwd.hash(payload.password),
        role="customer",
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

