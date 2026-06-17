"""
main.py — FastAPI Application Entry Point
==========================================
This is the root of the entire backend application.

What this file does:
    1. Creates the FastAPI app instance with metadata (title, version, docs URL)
    2. Registers CORS middleware (allows browser requests from any origin in debug mode)
    3. Registers request-timing middleware (adds X-Response-Time header to every response)
    4. Includes all API routers (auth, chat, sessions, documents, translate)
    5. Serves the frontend (HTML/CSS/JS) as static files
    6. Exposes a /health endpoint for monitoring

Routers registered:
    /api/auth/*         — User registration and login (JWT)
    /api/translate/*    — Language translation (text + document)
    /api/chat           — Main chatbot endpoint
    /api/sessions/*     — Conversation history management
    /api/documents/*    — RAG PDF upload and management

Static files:
    The frontend/ directory is mounted at /static so the browser can load
    style.css and app.js. The root URL (/) serves index.html.

To run:
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import time

from backend.config import settings
from backend.routes.chat      import router as chat_router
from backend.routes.sessions  import router as sessions_router
from backend.routes.documents import router as documents_router
from backend.routes.auth      import router as auth_router
from backend.routes.translate import router as translate_router
from backend.database import init_db
from backend.models.schemas import HealthResponse
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version}")
    logger.info(f"  Debug:   {settings.debug}")
    logger.info(f"  Model:   {settings.ollama_model}")
    logger.info(f"  DB:      {settings.database_url}")
    logger.info(f"  RAG:     {settings.rag_enabled}")
    init_db()
    logger.info("=" * 60)
    yield
    logger.info("Shutdown complete.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Nepali Language Intelligent Chatbot — Thesis Project",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# In production, replace "*" with your actual domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ─────────────────────────────────────────────────
@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    """
    Adds X-Response-Time header to every response.
    Used by the evaluation module to measure API latency.
    """
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 2)
    response.headers["X-Response-Time"] = f"{duration_ms}ms"
    return response


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(translate_router)
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(documents_router)

# ── Static files ──────────────────────────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        message="नेपाली च्याटबट सर्भर चलिरहेको छ।"
    )


@app.get("/", tags=["system"])
async def serve_frontend():
    return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )