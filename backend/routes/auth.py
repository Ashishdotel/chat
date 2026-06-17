"""
auth.py — Authentication Routes
---------------------------------
Endpoints:
  POST /api/auth/register   ← Create new account
  POST /api/auth/login      ← Login, receive JWT token
  GET  /api/auth/me         ← Get current user profile (protected)
  POST /api/auth/logout     ← Client-side logout hint

Password security:
  Passwords are hashed with bcrypt before storage.
  bcrypt is a slow, salted hashing algorithm designed
  specifically to resist brute-force attacks.
  The raw password is NEVER stored or logged anywhere.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime

from backend.database import get_db
from backend.database import repository
from backend.auth.jwt_handler import create_access_token
from backend.auth.dependencies import get_current_user
from backend.models.schemas import (
    UserRegister, UserLogin, TokenResponse, UserProfile
)
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# bcrypt context — handles hashing and verification
# rounds=12 is the recommended bcrypt work factor (balances security vs speed)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new user. Returns a JWT token for immediate login."
)
def register(request: UserRegister, db: Session = Depends(get_db)):
    """
    Registration flow:
    1. Check username is not already taken
    2. Check email is not already registered
    3. Hash the password
    4. Create user in DB
    5. Return JWT token (user is automatically logged in)
    """

    # Check username uniqueness
    if repository.get_user_by_username(db=db, username=request.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{request.username}' is already taken. "
                   f"('{request.username}' पहिले नै प्रयोग भइसकेको छ।)"
        )

    # Check email uniqueness
    if repository.get_user_by_email(db=db, email=request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered. (यो इमेल पहिले नै दर्ता भइसकेको छ।)"
        )

    # Hash password — bcrypt automatically adds a random salt
    hashed_pw = hash_password(request.password)

    # Create user
    user = repository.create_user(
        db=db,
        username=request.username,
        email=request.email,
        hashed_password=hashed_pw
    )

    # Issue JWT token
    token = create_access_token(user_id=user.id)

    logger.info(f"New user registered: {request.username}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        username=user.username,
        user_id=user.id
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT token",
    description="Authenticates with username and password. Returns a JWT access token."
)
def login(request: UserLogin, db: Session = Depends(get_db)):
    """
    Login flow:
    1. Find user by username
    2. Verify password against bcrypt hash
    3. Issue JWT token
    """

    # Generic error message — never reveal whether username or password was wrong
    # (prevents user enumeration attacks)
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="गलत username वा password। (Invalid username or password.)",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = repository.get_user_by_username(db=db, username=request.username)
    if not user:
        raise auth_error

    if not verify_password(request.password, user.hashed_password):
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise auth_error

    token = create_access_token(user_id=user.id)

    logger.info(f"User logged in: {request.username}")

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        username=user.username,
        user_id=user.id
    )


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user."
)
def get_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns profile info for the authenticated user."""
    from backend.database import repository as repo
    sessions = repo.get_all_sessions(db=db, user_id=current_user.id, limit=1000)

    return UserProfile(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
        session_count=len(sessions)
    )


@router.post(
    "/logout",
    summary="Logout hint",
    description="JWT tokens are stateless — actual logout is done client-side by deleting the token."
)
def logout():
    """
    JWT logout note:
    JWTs cannot be 'invalidated' server-side without a token blacklist.
    True logout is handled on the client by deleting the stored token.
    This endpoint exists as a clear API contract for the frontend.
    """
    return {
        "message": "लगआउट सफल। (Logged out successfully.)",
        "instruction": "Delete the token from localStorage to complete logout."
    }