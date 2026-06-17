"""
translate.py — Language Translation API Routes
================================================
This module provides three translation endpoints:

Endpoints:
    GET  /api/translate/languages
        Returns all supported language codes and their display names.
        Used by the frontend to populate language dropdown menus.

    POST /api/translate/text
        Accepts a JSON body with {text, source_language, target_language}.
        Calls llm.translate_text() which sends a translation prompt to Claude.
        Set source_language="auto" for automatic language detection.

    POST /api/translate/document
        Accepts a multipart form upload with {file, target_language, source_language}.

        PDF files:
            Text is extracted using pypdf (works for text-based PDFs).
            Extracted text is sent to Claude for translation.
            Documents over 4000 characters are truncated to stay within
            Claude's context window.

        Image files (JPG, PNG, WEBP, GIF):
            Image is base64-encoded and sent to Claude Vision (multimodal).
            Claude performs OCR (reads the text) and translates it
            in a single API call. This works for photos of documents,
            handwritten text, screenshots, etc.

        Maximum file size: 10MB.
        Supported image formats: .jpg, .jpeg, .png, .webp, .gif
"""

import os
import io
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status

from backend.models.schemas import (
    TranslateTextRequest,
    TranslateTextResponse,
    TranslateDocumentResponse,
)
from backend import llm
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/translate", tags=["translation"])

SUPPORTED_IMAGE_EXTS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

MAX_FILE_SIZE_MB = 10


@router.get("/languages", tags=["translation"])
def get_supported_languages():
    """Returns all supported language codes and their display names."""
    return {"languages": llm.LANGUAGE_NAMES}


@router.post(
    "/text",
    response_model=TranslateTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate text between languages",
)
async def translate_text_endpoint(request: TranslateTextRequest):
    """
    Translate typed text from source language to target language.
    Set source_language to 'auto' for automatic language detection.
    """
    if request.source_language == request.target_language and request.source_language != "auto":
        return TranslateTextResponse(
            translated_text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            char_count=len(request.text),
        )

    try:
        result = llm.translate_text(
            text=request.text,
            source_lang=request.source_language,
            target_lang=request.target_language,
        )
        return TranslateTextResponse(
            translated_text=result["translated_text"],
            source_language=request.source_language,
            target_language=request.target_language,
            char_count=result["char_count"],
        )
    except Exception as e:
        logger.error(f"Text translation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}",
        )


@router.post(
    "/document",
    response_model=TranslateDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Translate a PDF or image document",
    description=(
        "Upload a PDF (text-based) or an image file (JPG, PNG, WEBP, GIF). "
        "For PDFs, text is extracted and translated. "
        "For images, GPT-4o Vision performs OCR then translates."
    ),
)
async def translate_document_endpoint(
    file: UploadFile = File(...),
    target_language: str = Form(default="ne"),
    source_language: str = Form(default="auto"),
):
    """
    Translate an uploaded document.
    - PDF: extracts text with pypdf, then translates
    - Image: uses GPT-4o Vision for OCR + translation in one step
    """
    filename = file.filename or "document"
    _, ext = os.path.splitext(filename.lower())

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {size_mb:.1f}MB. Maximum: {MAX_FILE_SIZE_MB}MB",
        )

    # ── PDF handling ───────────────────────────────────────────────────────────
    if ext == ".pdf":
        try:
            import pypdf

            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            page_count = len(pdf_reader.pages)
            extracted_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    extracted_parts.append(text)

            extracted_text = "\n\n".join(extracted_parts).strip()

            if not extracted_text:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        "Could not extract text from this PDF. "
                        "It may be a scanned/image-based PDF — "
                        "please convert it to an image (JPG/PNG) and upload that instead."
                    ),
                )

            # Truncate very long documents to stay within token limits
            MAX_CHARS = 4000
            truncated = False
            if len(extracted_text) > MAX_CHARS:
                extracted_text = extracted_text[:MAX_CHARS]
                truncated = True

            result = llm.translate_text(
                text=extracted_text,
                source_lang=source_language,
                target_lang=target_language,
            )

            note = " [Note: document was truncated to first 4000 characters]" if truncated else ""
            return TranslateDocumentResponse(
                translated_text=result["translated_text"] + note,
                original_text=extracted_text,
                source_language=source_language,
                target_language=target_language,
                filename=filename,
                page_count=page_count,
                char_count=result["char_count"],
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF translation error for {filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF processing failed: {str(e)}",
            )

    # ── Image handling (OCR via GPT-4o Vision) ─────────────────────────────────
    elif ext in SUPPORTED_IMAGE_EXTS:
        try:
            mime_type = SUPPORTED_IMAGE_EXTS[ext]
            b64 = base64.b64encode(content).decode("utf-8")

            result = llm.translate_image_document(
                base64_image=b64,
                image_mime=mime_type,
                target_lang=target_language,
            )

            return TranslateDocumentResponse(
                translated_text=result["translated_text"],
                original_text=result["original_text"],
                source_language=source_language,
                target_language=target_language,
                filename=filename,
                page_count=1,
                char_count=len(result["translated_text"]),
            )

        except Exception as e:
            logger.error(f"Image translation error for {filename}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Image processing failed: {str(e)}",
            )

    else:
        supported = ", ".join([".pdf"] + list(SUPPORTED_IMAGE_EXTS.keys()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Supported: {supported}",
        )
