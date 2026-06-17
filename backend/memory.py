"""
memory.py — DB-Backed Chat Session Management
----------------------------------------------------------------
Phase 1/2 used a plain Python dictionary for storage.
Phase 3 replaces the storage backend with SQLite via repository.py.

IMPORTANT: The PUBLIC INTERFACE is identical to Phase 1/2.
- get_history(session_id) → list of {role, content} dicts
- add_message(session_id, role, content) → None
- clear_session(session_id) → bool

chat_service.py calls these same functions with zero changes.
This is the power of the Repository Pattern — the caller never
needs to know whether storage is in-memory, SQLite, or PostgreSQL.

New additions (DB-only):
- create_session_if_new() — initialises DB row for new sessions
- These are called by chat_service.py, not from outside
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session as DBSession

from backend.database import repository
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def get_history(
    db: DBSession,
    session_id: str
) -> List[Dict[str, str]]:
    """
    Retrieves conversation history for a session from the database.

    Returns only the last MAX_HISTORY_LENGTH messages to keep
    the OpenAI prompt within token limits.

    Args:
        db:         SQLAlchemy database session (injected by FastAPI)
        session_id: Session to retrieve history for

    Returns:
        List of dicts: [{"role": "user", "content": "..."}, ...]
        Empty list if session doesn't exist.
    """
    messages = repository.get_messages(
        db=db,
        session_id=session_id,
        limit=settings.max_history_length
    )

    history = [{"role": msg.role, "content": msg.content} for msg in messages]
    logger.debug(f"Loaded {len(history)} messages from DB for session {session_id[:8]}...")
    return history


def add_message(
    db: DBSession,
    session_id: str,
    role: str,
    content: str
) -> None:
    """
    Persists a single message to the database.

    Args:
        db:         SQLAlchemy database session
        session_id: Target session
        role:       "user" or "assistant"
        content:    Message text
    """
    repository.add_message(db=db, session_id=session_id, role=role, content=content)
    logger.debug(f"Persisted [{role}] message for session {session_id[:8]}...")


def ensure_session_exists(
    db: DBSession,
    session_id: str,
    first_message: str
) -> None:
    """
    Creates a session row in the DB if it doesn't already exist.

    Called by chat_service.py before the first message is saved.
    Idempotent — safe to call even if session already exists.

    Args:
        db:            Database session
        session_id:    UUID of the session
        first_message: First user message (used as session title)
    """
    existing = repository.get_session(db=db, session_id=session_id)
    if not existing:
        repository.create_session(
            db=db,
            session_id=session_id,
            first_message=first_message
        )
        logger.info(f"New DB session created: {session_id[:8]}...")


def clear_session(
    db: DBSession,
    session_id: str
) -> bool:
    """
    Soft-deletes a session from the database.

    Returns:
        True if the session existed and was cleared, False otherwise.
    """
    result = repository.delete_session(db=db, session_id=session_id)
    if result:
        logger.info(f"Session cleared: {session_id[:8]}...")
    return result


def get_all_sessions(db: DBSession, limit: int = 20) -> list:
    """
    Returns all active sessions for the sidebar history panel.

    Returns:
        List of SessionModel objects with id, title, updated_at, message_count
    """
    return repository.get_all_sessions(db=db, limit=limit)