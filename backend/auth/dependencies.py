"""
dependencies.py — FastAPI Authentication Dependencies
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from backend.auth.jwt_handler import decode_access_token
from backend.database import get_db
from backend.database import repository
from backend.database.models import User
from backend.utils.logger import get_logger

logger = get_logger(__name__)

oauth2_scheme          = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Dependency for protected routes. Raises 401 if token is missing/invalid."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed. Please login again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if not user_id:
        raise credentials_exception
    user = repository.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise credentials_exception
    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for optional auth routes. Returns None if no valid token."""
    if not token:
        return None
    user_id = decode_access_token(token)
    if not user_id:
        return None
    return repository.get_user_by_id(db=db, user_id=user_id)
