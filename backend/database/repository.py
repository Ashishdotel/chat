"""
repository.py — Phase 5 Update
---------------------------------
Added: User CRUD operations.
Updated: get_all_sessions() now filters by user_id.
All Phase 3 session/message functions preserved.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

from backend.database.models import (
    Session as SessionModel,
    Message as MessageModel,
    User as UserModel
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ===================== USER OPERATIONS (NEW) =====================

def create_user(
    db: Session,
    username: str,
    email: str,
    hashed_password: str
) -> UserModel:
    """
    Creates a new user record.

    Args:
        db:              Database session
        username:        Chosen display name
        email:           Email address
        hashed_password: bcrypt hash of the password

    Returns:
        Newly created UserModel
    """
    user = UserModel(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"DB: New user created: {username}")
    return user


def get_user_by_username(db: Session, username: str) -> Optional[UserModel]:
    """Finds a user by username. Returns None if not found."""
    return db.query(UserModel).filter(
        UserModel.username == username,
        UserModel.is_active == True
    ).first()


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    """Finds a user by email. Returns None if not found."""
    return db.query(UserModel).filter(
        UserModel.email == email,
        UserModel.is_active == True
    ).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[UserModel]:
    """Finds a user by ID. Returns None if not found."""
    return db.query(UserModel).filter(
        UserModel.id == user_id,
        UserModel.is_active == True
    ).first()


# ===================== SESSION OPERATIONS (updated) =====================

def create_session(
    db: Session,
    session_id: str,
    first_message: str,
    user_id: Optional[str] = None   # ← NEW optional parameter
) -> SessionModel:
    """Creates a new session, optionally linked to a user."""
    title = first_message[:60] + ("..." if len(first_message) > 60 else "")

    session = SessionModel(
        id=session_id,
        title=title,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True,
        message_count=0,
        user_id=user_id            # ← NEW
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info(f"DB: Created session {session_id[:8]}... user={user_id}")
    return session


def get_session(db: Session, session_id: str) -> Optional[SessionModel]:
    """Gets a session by ID."""
    return db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.is_active == True
    ).first()


def get_all_sessions(
    db: Session,
    limit: int = 20,
    user_id: Optional[str] = None   # ← NEW: filter by user
) -> List[SessionModel]:
    """
    Returns active sessions, optionally filtered by user.
    If user_id is provided, only that user's sessions are returned.
    """
    query = db.query(SessionModel).filter(SessionModel.is_active == True)

    if user_id:
        query = query.filter(SessionModel.user_id == user_id)

    return query.order_by(desc(SessionModel.updated_at)).limit(limit).all()


def update_session_timestamp(
    db: Session,
    session_id: str,
    message_count_delta: int = 1
):
    """Updates session updated_at and message count."""
    session = get_session(db, session_id)
    if session:
        session.updated_at = datetime.utcnow()
        session.message_count += message_count_delta
        db.commit()


def delete_session(db: Session, session_id: str) -> bool:
    """Soft-deletes a session."""
    session = get_session(db, session_id)
    if not session:
        return False
    session.is_active = False
    session.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"DB: Soft-deleted session {session_id[:8]}...")
    return True


# ===================== MESSAGE OPERATIONS (unchanged) =====================

def add_message(
    db: Session,
    session_id: str,
    role: str,
    content: str
) -> MessageModel:
    """Inserts a message and updates the session timestamp."""
    message = MessageModel(
        session_id=session_id,
        role=role,
        content=content,
        created_at=datetime.utcnow()
    )
    db.add(message)
    update_session_timestamp(db, session_id)
    db.commit()
    db.refresh(message)
    logger.debug(f"DB: Saved [{role}] message to session {session_id[:8]}...")
    return message


def get_messages(
    db: Session,
    session_id: str,
    limit: Optional[int] = None
) -> List[MessageModel]:
    """Gets all messages for a session (optionally limited to last N)."""
    query = db.query(MessageModel).filter(
        MessageModel.session_id == session_id
    ).order_by(MessageModel.created_at)

    if limit:
        total = query.count()
        if total > limit:
            query = query.offset(total - limit)

    return query.all()


def get_message_count(db: Session, session_id: str) -> int:
    """Returns total message count for a session."""
    return db.query(MessageModel).filter(
        MessageModel.session_id == session_id
    ).count()