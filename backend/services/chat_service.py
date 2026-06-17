"""
chat_service.py — Chat Business Logic
=======================================
This module contains the core logic that processes every chat message.
It coordinates between the database (memory), RAG (document retrieval),
and the LLM (Claude AI).

The process_chat() function follows these steps:

    Step 1: Generate a new session ID if this is a new conversation.
    Step 2: Ensure the session record exists in the SQLite database.
    Step 3: Load conversation history (last N messages) from the database.
    Step 4: If RAG is enabled, search the FAISS vector index for relevant
            document chunks that match the user's question.
    Step 5: If relevant chunks were found, prepend them to the user message
            as context so Claude can use them to answer.
    Step 6: Save the user's message to the database.
    Step 7: Call Claude API via llm.get_chat_response() with the history
            and (possibly augmented) message.
    Step 8: Save Claude's reply to the database.
    Step 9: Return (reply, session_id, rag_used) to the route handler.

The language parameter controls which language Claude responds in.
"""

import uuid
from typing import Tuple
from sqlalchemy.orm import Session as DBSession

from backend import memory
from backend import llm
from backend import rag
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def process_chat(
    db: DBSession,
    user_message: str,
    session_id: str | None,
    language: str = "ne"
) -> Tuple[str, str, bool]:
    """
    Processes a user message and returns (reply, session_id, rag_used).

    Returns:
        Tuple of (bot_reply: str, session_id: str, rag_used: bool)
    """

    # Step 1: Generate session ID for new conversations
    if not session_id:
        session_id = str(uuid.uuid4())
        logger.info(f"New session started: {session_id}")

    # Step 2: Ensure session exists in DB
    memory.ensure_session_exists(
        db=db,
        session_id=session_id,
        first_message=user_message
    )

    # Step 3: Load conversation history from DB
    history = memory.get_history(db=db, session_id=session_id)
    logger.debug(f"Session {session_id[:8]}... | History: {len(history)} messages")

    # Step 4: RAG retrieval
    context  = ""
    rag_used = False

    if rag.is_rag_enabled():
        context = rag.retrieve_context(user_message)
        if context:
            rag_used = True
            logger.info(f"RAG context injected ({len(context)} chars)")

    # Step 5: Augment message with RAG context if available
    augmented_message = user_message
    if context:
        augmented_message = (
            f"{context}\n\n"
            f"माथिको सन्दर्भमा आधारित भएर उत्तर दिनुहोस्:\n"
            f"(Answer based on the above context:)\n"
            f"{user_message}"
        )

    # Step 6: Save user message to DB
    memory.add_message(
        db=db,
        session_id=session_id,
        role="user",
        content=user_message
    )

    # Step 7: Call OpenAI — pass history without the message just saved
    history_for_llm = memory.get_history(db=db, session_id=session_id)[:-1]

    try:
        bot_reply = llm.get_chat_response(
            history=history_for_llm,
            user_message=augmented_message,
            language=language
        )
    except Exception as e:
        logger.error(f"LLM error for session {session_id[:8]}...: {str(e)}")
        raise

    # Step 8: Save bot reply to DB
    memory.add_message(
        db=db,
        session_id=session_id,
        role="assistant",
        content=bot_reply
    )

    logger.info(f"Session {session_id[:8]}... | Response saved to DB")
    return bot_reply, session_id, rag_used