"""
connection.py — SQLAlchemy Engine & Session Factory
-----------------------------------------------------
This file sets up the database connection used by the entire backend.

Key concepts:
- Engine:  the low-level connection to the database file
- Session: a unit-of-work object — open one per request, close when done
- Base:    a shared declarative base that all ORM models inherit from

Why SQLite for Phase 3?
- Zero configuration — the .db file is created automatically
- No separate database server to install (great for thesis demos)
- SQLAlchemy makes switching to PostgreSQL in Phase 5 a one-line change

Why one session per request?
- Prevents data leaking between concurrent requests
- Ensures transactions are committed or rolled back cleanly
- FastAPI's Depends() system manages this automatically
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# --- Declarative Base ---
# All ORM model classes inherit from this.
# SQLAlchemy uses it to track which classes map to which tables.
class Base(DeclarativeBase):
    pass


# --- Ensure the data/ directory exists before creating the DB file ---
db_path = settings.database_url.replace("sqlite:///", "")
os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)


# --- Create Engine ---
# connect_args={"check_same_thread": False} is required for SQLite
# because FastAPI runs in async mode and SQLite's default threading
# policy would otherwise raise an error.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,      # Logs all SQL queries when DEBUG=True
)


# --- Enable WAL mode for SQLite ---
# WAL (Write-Ahead Logging) allows concurrent reads during writes.
# This prevents "database is locked" errors under load.
@event.listens_for(engine, "connect")
def set_wal_mode(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")   # Enforce FK constraints
    cursor.close()


# --- Session Factory ---
# Each call to SessionLocal() creates a new database session.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # We commit manually after successful operations
    autoflush=False,    # We flush manually for better control
)


def get_db():
    """
    FastAPI dependency that yields a database session per request.

    Usage in a route:
        from fastapi import Depends
        from backend.database import get_db
        from sqlalchemy.orm import Session

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The 'finally' block ensures the session is ALWAYS closed,
    even if an exception occurs during request handling.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Creates all database tables defined in models.py.
    Called once at application startup.

    SQLAlchemy checks if each table already exists before creating it,
    so calling init_db() multiple times is safe (idempotent).
    """
    # Import models here so Base knows about them before create_all()
    from backend.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialised successfully")
    logger.info(f"Database location: {db_path}")