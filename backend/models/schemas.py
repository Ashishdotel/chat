"""
schemas.py — Final (Phase 5)
------------------------------
Added: UserRegister, UserLogin, TokenResponse, UserProfile
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


# ── Chat Schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = Field(default=None)
    language: str = Field(default="ne", description="Response language code (ne, en, hi, zh, etc.)")


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model_used: str
    timestamp: datetime
    rag_used: bool = Field(default=False)


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    session_id: Optional[str] = None


# ── Session / History Schemas ─────────────────────────────────────────────────

class SessionSummary(BaseModel):
    id: str
    title: str
    message_count: int
    updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class MessageSchema(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationHistory(BaseModel):
    session_id: str
    title: str
    messages: List[MessageSchema]
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Document / RAG Schemas ────────────────────────────────────────────────────

class DocumentInfo(BaseModel):
    filename: str
    page_count: int
    chunk_count: int
    indexed_at: str


class IngestResponse(BaseModel):
    message: str
    filename: str
    page_count: int
    chunk_count: int
    total_vectors: int
    rag_enabled: bool


class RAGStatusResponse(BaseModel):
    rag_enabled: bool
    document_count: int
    documents: List[DocumentInfo]
    vector_count: Optional[int] = None


# ── Authentication Schemas ← NEW ──────────────────────────────────────────────

class UserRegister(BaseModel):
    """Request body for POST /api/auth/register"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="3-50 characters, alphanumeric and underscores only"
    )
    email: str = Field(..., description="Valid email address")
    password: str = Field(
        ...,
        min_length=8,
        description="Minimum 8 characters"
    )


class UserLogin(BaseModel):
    """Request body for POST /api/auth/login"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Returned after successful login/register"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int           # Seconds until expiry
    username: str
    user_id: str


class UserProfile(BaseModel):
    """Current user profile — returned by GET /api/auth/me"""
    user_id: str
    username: str
    email: str
    created_at: datetime
    session_count: int = 0

    class Config:
        from_attributes = True


# ── Translation Schemas ────────────────────────────────────────────────────────

class TranslateTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    source_language: str = Field(default="auto", description="Source language code or 'auto' for auto-detect")
    target_language: str = Field(default="ne", description="Target language code")


class TranslateTextResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    char_count: int


class TranslateDocumentResponse(BaseModel):
    translated_text: str
    original_text: str
    source_language: str
    target_language: str
    filename: str
    page_count: Optional[int] = None
    char_count: int