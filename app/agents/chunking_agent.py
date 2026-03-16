"""Chunking agent: splits documents into manageable text chunks."""
from __future__ import annotations

from pathlib import Path

from app.models.document_chunk import DocumentChunk
from app.services.document_parser import DocumentParser


class ChunkingAgent:
    """Produces document chunks for embedding and retrieval."""

    def __init__(self) -> None:
        self._parser = DocumentParser()

    async def chunk_file(self, file_path: Path, job_id: str) -> list[DocumentChunk]:
        """Extract and chunk document; return list of chunks."""
        return await self._parser.parse_and_chunk(file_path, job_id)
