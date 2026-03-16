"""Document extraction from PDF, DOCX, TXT, and images (OCR)."""
from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

from app.models.document_chunk import DocumentChunk
from app.utils.text_utils import iter_chunks, sanitize_for_llm
from app.config.settings import get_settings


class DocumentParser:
    """Extract raw text from supported document types."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def _read_pdf(self, path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("pypdf is required for PDF: pip install pypdf")
        reader = PdfReader(path)
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    def _read_docx(self, path: Path) -> str:
        try:
            from docx import Document as DocxDocument
        except ImportError:
            raise RuntimeError("python-docx is required: pip install python-docx")
        doc = DocxDocument(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    def _read_txt(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")

    def _read_image_ocr(self, path: Path) -> str:
        try:
            from PIL import Image
            import pytesseract
        except ImportError:
            raise RuntimeError("PIL and pytesseract required for images: pip install Pillow pytesseract")
        img = Image.open(path)
        return pytesseract.image_to_string(img, lang="eng+tam")

    def extract_text(self, path: Path) -> str:
        """Extract full text from file. Path must exist and be a file."""
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(str(path))
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            raw = self._read_pdf(path)
        elif suffix in (".docx", ".doc"):
            raw = self._read_docx(path)
        elif suffix == ".txt":
            raw = self._read_txt(path)
        elif suffix in (".jpg", ".jpeg", ".png"):
            raw = self._read_image_ocr(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")
        return sanitize_for_llm(raw)

    async def extract_text_async(self, path: Path) -> str:
        """Async wrapper; runs extraction in executor to avoid blocking."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.extract_text, path)

    def chunk_document(
        self,
        text: str,
        job_id: str,
        source_file: str = "",
    ) -> list[DocumentChunk]:
        """Split extracted text into chunks for embedding."""
        chunks: list[DocumentChunk] = []
        for idx, (content, token_count) in enumerate(
            iter_chunks(
                text,
                chunk_size=self._settings.chunk_size,
                overlap=self._settings.chunk_overlap,
            )
        ):
            chunks.append(
                DocumentChunk(
                    job_id=job_id,
                    content=content,
                    chunk_index=idx,
                    token_count=token_count,
                    source_file=source_file,
                )
            )
        return chunks

    async def parse_and_chunk(
        self,
        path: Path,
        job_id: str,
    ) -> list[DocumentChunk]:
        """Extract text and return chunks. Use for pipeline."""
        text = await self.extract_text_async(path)
        return self.chunk_document(text, job_id, source_file=path.name)
