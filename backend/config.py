"""
config.py — Application Configuration
=======================================
Loads all settings from the .env file using Pydantic BaseSettings.

How it works:
    1. Pydantic reads every field from the .env file automatically.
    2. The @lru_cache() decorator ensures settings are loaded only ONCE
       for the entire lifetime of the server process.
    3. Use `from backend.config import settings` anywhere in the project.

Required environment variables (must be set in .env):
    OLLAMA_API_KEY — Your Ollama API key

Optional environment variables (have defaults):
    OLLAMA_MODEL    — Ollama model to use (default: llama3.1)
    DEBUG           — Enable debug mode and auto-reload (default: False)
    PORT            — Server port (default: 8000)
    DATABASE_URL    — SQLite path (default: sqlite:///./data/chatbot.db)
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):

    # --- Ollama ---
    ollama_api_key: str = Field(...)
    ollama_base_url: str = Field(default="https://api.ollama.com/v1")
    ollama_model: str = Field(default="llama3.1")
    ollama_max_tokens: int = Field(default=1024)

    # --- Application ---
    app_name: str = Field(default="Nepali Language Intelligent Chatbot")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)

    # --- Server ---
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # --- Memory ---
    max_history_length: int = Field(default=20)

    # --- Database ---
    database_url: str = Field(default="sqlite:///./data/chatbot.db")

    # --- RAG ---
    rag_enabled: bool = Field(default=False)
    rag_chunk_size: int = Field(default=500)
    rag_chunk_overlap: int = Field(default=50)
    rag_top_k: int = Field(default=4)
    rag_embedding_model: str = Field(default="text-embedding-3-small")
    documents_dir: str = Field(default="./data/documents")
    vector_store_dir: str = Field(default="./data/vector_store")

    # --- Authentication ---
    secret_key: str = Field(default="change-me-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=1440)

    # --- Evaluation ---
    eval_output_dir: str = Field(default="./evaluation/eval_results")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
