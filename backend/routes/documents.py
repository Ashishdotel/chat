"""
documents.py — PDF Upload & RAG Management Routes
---------------------------------------------------
Endpoints:
  POST   /api/documents/upload      ← Upload & index a PDF
  GET    /api/documents/            ← List all indexed documents
  GET    /api/documents/status      ← RAG system status
  DELETE /api/documents/{filename}  ← Remove a document
  POST   /api/documents/rag/toggle  ← Enable/disable RAG
"""

import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from backend.services import rag_service
from backend.models.schemas import (
    IngestResponse, RAGStatusResponse, DocumentInfo
)
from backend.config import settings, get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
)

# Allowed file types for upload
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE_MB   = 50


@router.post(
    "/upload",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and index a PDF document",
    description=(
        "Upload a PDF file to be processed for RAG. "
        "The file is saved, text is extracted, chunked, embedded, "
        "and added to the FAISS vector index. "
        "RAG is automatically enabled after the first successful upload."
    )
)
async def upload_document(file: UploadFile = File(...)):
    """
    Full ingestion pipeline triggered by a file upload.

    1. Validate file type and size
    2. Save file to data/documents/
    3. Run ingestion pipeline (extract → chunk → embed → index)
    4. Auto-enable RAG in settings
    5. Return ingestion summary
    """
    # --- Validate file extension ---
    filename  = file.filename or "upload.pdf"
    _, ext    = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only PDF files are supported. Got: '{ext}'"
        )

    # --- Validate file size ---
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {size_mb:.1f}MB. Maximum: {MAX_FILE_SIZE_MB}MB"
        )

    logger.info(f"Upload received: {filename} ({size_mb:.2f}MB)")

    # --- Save file to disk ---
    os.makedirs(settings.documents_dir, exist_ok=True)
    save_path = os.path.join(settings.documents_dir, filename)

    with open(save_path, "wb") as f:
        f.write(content)

    logger.info(f"File saved: {save_path}")

    # --- Run ingestion pipeline ---
    try:
        result = rag_service.ingest_pdf(pdf_path=save_path, filename=filename)
    except ValueError as e:
        # Clean up saved file if ingestion fails
        os.remove(save_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        os.remove(save_path)
        logger.error(f"Ingestion failed for {filename}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )

    # --- Auto-enable RAG after first successful ingestion ---
    # We modify the cached settings object directly since .env write
    # would require a restart. This persists for the lifetime of the server.
    cached_settings = get_settings()
    object.__setattr__(cached_settings, "rag_enabled", True)
    logger.info("RAG automatically enabled after document ingestion")

    return IngestResponse(
        message=f"'{filename}' सफलतापूर्वक इन्डेक्स गरियो! (Indexed successfully!)",
        filename=result["filename"],
        page_count=result["page_count"],
        chunk_count=result["chunk_count"],
        total_vectors=result["total_vectors"],
        rag_enabled=True,
    )


@router.get(
    "/status",
    response_model=RAGStatusResponse,
    summary="Get RAG system status",
    description="Returns whether RAG is active and lists all indexed documents."
)
def get_rag_status():
    """
    Returns the current state of the RAG system.
    Frontend uses this to show the document list and RAG status badge.
    """
    docs = rag_service.get_indexed_documents()

    # Try to get FAISS vector count
    vector_count = None
    try:
        index = rag_service._load_faiss_index()
        if index:
            vector_count = index.ntotal
    except Exception:
        pass

    return RAGStatusResponse(
        rag_enabled=rag_service.has_indexed_documents() and settings.rag_enabled,
        document_count=len(docs),
        documents=[
            DocumentInfo(
                filename=d["filename"],
                page_count=d["page_count"],
                chunk_count=d["chunk_count"],
                indexed_at=d["indexed_at"],
            )
            for d in docs
        ],
        vector_count=vector_count,
    )


@router.get(
    "/",
    summary="List indexed documents",
    description="Returns a simple list of all indexed PDF filenames."
)
def list_documents():
    """Returns all indexed documents."""
    docs = rag_service.get_indexed_documents()
    return {"documents": docs, "count": len(docs)}


@router.delete(
    "/{filename}",
    summary="Remove a document from the index",
    description="Removes the document record. Full re-indexing required to remove its vectors."
)
def remove_document(filename: str):
    """
    Removes a document from the index list and deletes the PDF file.
    Note: FAISS vectors are not immediately removed (Phase 5 adds re-indexing).
    """
    # Remove from index list
    removed = rag_service.delete_document_from_index(filename)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found in index"
        )

    # Delete the PDF file
    pdf_path = os.path.join(settings.documents_dir, filename)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        logger.info(f"Deleted PDF file: {pdf_path}")

    # If no documents remain, disable RAG
    if not rag_service.has_indexed_documents():
        cached_settings = get_settings()
        object.__setattr__(cached_settings, "rag_enabled", False)
        logger.info("RAG disabled — no documents remaining")

    return {
        "message": f"'{filename}' हटाइयो। (Document removed.)",
        "filename": filename,
        "rag_still_enabled": rag_service.has_indexed_documents()
    }


@router.post(
    "/rag/toggle",
    summary="Toggle RAG on or off",
    description="Manually enable or disable RAG without removing documents."
)
def toggle_rag(enabled: bool):
    """Manually toggle RAG. Useful for A/B comparison in thesis evaluation."""
    if enabled and not rag_service.has_indexed_documents():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enable RAG: no documents indexed yet. Upload a PDF first."
        )

    cached_settings = get_settings()
    object.__setattr__(cached_settings, "rag_enabled", enabled)

    state = "सक्षम (enabled)" if enabled else "अक्षम (disabled)"
    logger.info(f"RAG manually toggled: {state}")

    return {
        "rag_enabled": enabled,
        "message": f"RAG {state}"
    }