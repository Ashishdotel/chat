"""
jwt_handler.py — JWT Token Creation & Verification
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def create_access_token(user_id: str) -> str:
    """Creates a signed JWT access token for a given user_id."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub":  user_id,
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),
        "type": "access"
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    logger.debug(f"JWT created for user {user_id[:8]}... expires {expire}")
    return token


def decode_access_token(token: str) -> Optional[str]:
    """Decodes and validates a JWT token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str     = payload.get("sub")
        token_type: str  = payload.get("type")
        if user_id is None or token_type != "access":
            return None
        return user_id
    except JWTError as e:
        logger.warning(f"JWT decode failed: {str(e)}")
        return None
