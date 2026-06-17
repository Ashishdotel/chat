"""
chat.py — Chat Routes (Phase 4 with Phase 5 update)
----------------------------------------
Phase 4: RAG support with rag_used flag
Phase 5: Return rag_used in response
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.chat_service import process_chat
from backend.database import get_db
from backend import memory
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the Nepali chatbot"
)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint.
    Accepts user message, returns Nepali reply.
    Persists both messages to the database.
    """
    logger.info(
        f"Chat request | Session: {request.session_id} | "
        f"Msg length: {len(request.message)}"
    )

    try:
        bot_reply, session_id, rag_used = process_chat(
            db=db,
            user_message=request.message,
            session_id=request.session_id,
            language=request.language
        )
        return ChatResponse(
            reply=bot_reply,
            session_id=session_id,
            model_used=settings.ollama_model,
            timestamp=datetime.utcnow(),
            rag_used=rag_used
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "LLM_ERROR",
                "detail": "माफ गर्नुहोस्, अहिले जवाफ दिन सकिएन। कृपया पुनः प्रयास गर्नुहोस्।",
                "english": "Sorry, could not generate a response. Please try again."
            }
        )


@router.delete(
    "/chat/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Clear a chat session"
)
async def clear_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Clears the conversation memory for a session."""
    cleared = memory.clear_session(db=db, session_id=session_id)
    if not cleared:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )
    return {"message": "Session cleared", "session_id": session_id}


@router.get(
    "/session/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Get session debug info"
)
async def get_session_info(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Returns session metadata for debugging."""
    from backend.database import repository
    session = repository.get_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found"
        )
    messages = repository.get_messages(db=db, session_id=session_id)
    return {
        "session_id": session_id,
        "title": session.title,
        "message_count": session.message_count,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "history_preview": [
            {"role": m.role, "content": m.content[:80]}
            for m in messages[-4:]
        ]
    }