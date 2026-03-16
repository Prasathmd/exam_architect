"""Document chunk and embedding models."""
from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A chunk of document text with optional embedding metadata."""

    id: UUID | None = None
    job_id: str
    content: str
    chunk_index: int = 0
    token_count: int = 0
    source_file: str = ""
    page_start: int | None = None
    page_end: int | None = None


class ChunkWithEmbedding(DocumentChunk):
    """Chunk with vector embedding for storage/retrieval."""

    embedding: list[float] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """Single result from vector retrieval."""

    chunk: DocumentChunk
    score: float
    metadata: dict = Field(default_factory=dict)
