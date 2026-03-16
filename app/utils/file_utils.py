"""File handling utilities: validation, paths, sanitization."""
from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import UploadFile

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png"}
CONTENT_TYPE_MAP = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "text/plain": ".txt",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def validate_file_type(content_type: str, filename: str | None) -> tuple[bool, str]:
    """
    Validate upload by content type and extension.
    Returns (is_valid, error_message).
    """
    ext = Path(filename or "").suffix.lower()
    if content_type not in CONTENT_TYPE_MAP and not ext:
        return False, "Unsupported file type"
    if ext and ext not in ALLOWED_EXTENSIONS:
        return False, f"Extension not allowed: {ext}"
    return True, ""


def validate_file_size(size: int, max_bytes: int) -> tuple[bool, str]:
    """Check file size within limit. Returns (is_valid, error_message)."""
    if size > max_bytes:
        return False, f"File size exceeds {max_bytes // (1024*1024)} MB"
    return True, ""


def safe_filename(original: str) -> str:
    """Return a safe filename (alphanumeric, dash, underscore)."""
    base = Path(original).stem
    safe = re.sub(r"[^\w\-.]", "_", base)[:100]
    return safe or "document"


def generate_job_id() -> str:
    """Generate a unique job identifier."""
    return f"JOB{uuid.uuid4().hex[:8].upper()}"


def upload_path_for_job(upload_dir: Path, job_id: str, original_filename: str) -> Path:
    """Path where uploaded file for job_id should be stored."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(original_filename).suffix or CONTENT_TYPE_MAP.get(
        "application/pdf", ".pdf"
    )
    return upload_dir / f"{job_id}_{safe_filename(original_filename)}{ext}"


def file_hash(path: Path, block_size: int = 8192) -> str:
    """Compute SHA256 hash of file for deduplication."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block_size):
            h.update(chunk)
    return h.hexdigest()
