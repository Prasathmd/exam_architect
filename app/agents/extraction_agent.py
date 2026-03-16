"""Extraction agent: extracts raw text from PDF, DOCX, TXT, images."""
from __future__ import annotations

from pathlib import Path

from app.services.document_parser import DocumentParser


class ExtractionAgent:
    """Orchestrates document parsing for the pipeline."""

    def __init__(self) -> None:
        self._parser = DocumentParser()

    async def extract(self, file_path: Path) -> str:
        """Extract full text from document at file_path."""
        return await self._parser.extract_text_async(file_path)
