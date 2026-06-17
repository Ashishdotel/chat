"""
models.py — Phase 5 Update
----------------------------
Added: User table.
Sessions now have an optional user_id foreign key so
each user sees only their own conversations.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime,
    Integer, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from backend.database.connection import Base


class User(Base):
    """
    Registered user account.

    Table: users
    -------------
    id            — UUID string primary key
    username      — Unique display name (3-50 chars)
    email         — Unique email address
    hashed_password — bcrypt hash; raw password is NEVER stored
    is_active     — False if account is disabled
    created_at    — Registration timestamp
    """
    __tablename__ = "users"

    id              = Column(String(36), primary_key=True, index=True)
    username        = Column(String(50),  unique=True, nullable=False, index=True)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    # One user has many sessions
    sessions = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User id={self.id[:8]}... username={self.username}>"


class Session(Base):
    """
    Conversation session — now linked to a User.
    """
    __tablename__ = "sessions"

    id            = Column(String(36), primary_key=True, index=True)
    title         = Column(String(100), nullable=False, default="नयाँ कुराकानी")
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow, nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)

    # Foreign key to users table (nullable: guest sessions have no user)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    user = relationship("User", back_populates="sessions")

    messages = relationship(
        "Message",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="select"
    )

    def __repr__(self):
        return f"<Session id={self.id[:8]}... title='{self.title}'>"


class Message(Base):
    """Single chat message — unchanged from Phase 3."""
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    role       = Column(String(20), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("Session", back_populates="messages")

    def __repr__(self):
        return f"<Message id={self.id} role={self.role}>"