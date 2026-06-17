"""
sessions.py — Session History API Routes
-----------------------------------------
Provides endpoints the frontend uses to:
  1. List all past conversation sessions (sidebar)
  2. Load the full message history of a specific session
  3. Delete a session (already in chat.py, unified here too)

These routes power the "past conversations" sidebar feature.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend.database import repository
from backend.models.schemas import SessionSummary, ConversationHistory, MessageSchema
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/sessions",
    tags=["sessions"],
)


@router.get(
    "/",
    response_model=List[SessionSummary],
    summary="List all past conversation sessions",
    description="Returns sessions ordered by most recently active. Used to populate the sidebar."
)
def list_sessions(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Returns the 20 most recent active sessions.
    Each item includes: id, title, message_count, updated_at.
    Message content is NOT included (use /api/sessions/{id} for that).
    """
    sessions = repository.get_all_sessions(db=db, limit=limit)
    logger.info(f"Listed {len(sessions)} sessions")
    return sessions


@router.get(
    "/{session_id}",
    response_model=ConversationHistory,
    summary="Get full conversation history",
    description="Returns all messages for a session. Used when user clicks a past chat."
)
def get_conversation(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Loads the complete message history for a session.
    Frontend calls this when user clicks a past conversation in the sidebar.
    """
    session = repository.get_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )

    messages = repository.get_messages(db=db, session_id=session_id)

    return ConversationHistory(
        session_id=session.id,
        title=session.title,
        messages=[
            MessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at
            )
            for m in messages
        ],
        message_count=len(messages),
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.delete(
    "/{session_id}",
    summary="Delete a conversation session",
    description="Soft-deletes the session and all its messages."
)
def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Marks a session as deleted.
    Paired with the DELETE /api/chat/{id} route from Phase 1.
    """
    deleted = repository.delete_session(db=db, session_id=session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )
    return {"message": "Session deleted", "session_id": session_id}