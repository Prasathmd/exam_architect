"""Application settings and environment configuration."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "Exam-Architect AI"
    debug: bool = False
    upload_dir: Path = Path("uploads")
    export_dir: Path = Path("exports")
    max_upload_size_mb: int = 50
    allowed_extensions: set[str] = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/jpeg",
        "image/png",
    }

    # Database (database = postgres, schema = exam_architect)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    database_schema: str = "exam_architect"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Vector DB (ChromaDB)
    chroma_persist_dir: str = "./chroma_db"

    # LLM
    llm_provider: Literal["openai", "gemini"] = "openai"
    openai_api_key: str | None = None
    google_api_key: str | None = None
    gemini_api_key: str | None = None  # alias; either GOOGLE_API_KEY or GEMINI_API_KEY
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    gemini_embedding_model: str = "models/gemini-embedding-001"
    gemini_chat_model: str = "gemma-3-4b-it"  # Gemma 3 4B: fast, good quality, separate quota

    # Chunking
    chunk_size: int = 1200
    chunk_overlap: int = 200

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def get_gemini_api_key(self) -> str | None:
        """Return Gemini key from GOOGLE_API_KEY or GEMINI_API_KEY (whichever is set)."""
        for k in (self.google_api_key, self.gemini_api_key):
            if k and str(k).strip():
                return str(k).strip()
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Clear the settings cache (call after .env changes)."""
    get_settings.cache_clear()
