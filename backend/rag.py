"""
rag.py — RAG Module (Phase 4 Full Implementation)
---------------------------------------------------
This file is the public interface for RAG.
chat_service.py imports from here — never from rag_service.py directly.

Phase 1-3: is_rag_enabled() returned False, retrieve_context() returned ""
Phase 4:   Both now delegate to rag_service.py for real functionality

The interface is IDENTICAL to Phase 1 — zero changes needed in chat_service.py.
"""

from backend.services import rag_service
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def is_rag_enabled() -> bool:
    """
    Returns True if RAG is active and documents have been indexed.

    Two conditions must both be true:
    1. RAG_ENABLED=True in .env (or auto-set after first document upload)
    2. At least one document has been successfully indexed
    """
    if not settings.rag_enabled:
        return False
    return rag_service.has_indexed_documents()


def retrieve_context(query: str) -> str:
    """
    Retrieves relevant document context for a query and formats it
    as a string ready to inject into the GPT prompt.

    Args:
        query: User's message

    Returns:
        Formatted context string, or "" if RAG is disabled / no results
    """
    if not is_rag_enabled():
        return ""

    try:
        chunks  = rag_service.retrieve_relevant_chunks(query)
        context = rag_service.format_context_for_prompt(chunks)
        logger.info(f"RAG context: {len(chunks)} chunks, {len(context)} chars")
        return context

    except Exception as e:
        # RAG failure should NOT break the chat — fall back to no context
        logger.error(f"RAG retrieval failed: {str(e)} — continuing without context")
        return ""