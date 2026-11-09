"""
Auth router — login and profile endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import create_access_token, get_current_user
from app.models.user import User
from app.schemas.user import LoginResponse, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

_pwd = PasswordHash.recommended()


@router.post("/login", response_model=LoginResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT access token."""
    user: User | None = db.query(User).filter(User.email == payload.email).first()

    # Use the same error for missing user and wrong password (prevent user enumeration)
    if not user or not _pwd.verify(payload.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is inactive. Contact the administrator.",
        )

    token = create_access_token(user.id)
    return LoginResponse(
        message="Login successful",
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user

