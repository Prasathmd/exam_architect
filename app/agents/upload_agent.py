"""Upload agent: handles document uploads and job creation."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.config.settings import get_settings
from app.models.job_status import JobStatus, UploadResponse
from app.utils.file_utils import (
    validate_file_type,
    validate_file_size,
    generate_job_id,
    upload_path_for_job,
)

if TYPE_CHECKING:
    from fastapi import UploadFile


class UploadAgent:
    """Handles file validation and persistence for uploads."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def create_job_id(self) -> str:
        return generate_job_id()

    def validate_upload(self, file: UploadFile) -> tuple[bool, str]:
        """
        Validate file type and size. Returns (ok, error_message).
        """
        content_type = file.content_type or ""
        ok, msg = validate_file_type(content_type, file.filename)
        if not ok:
            return False, msg
        # Size: need to read or check content_length if available
        size = 0
        if hasattr(file, "size") and file.size is not None:
            size = file.size
        # For multipart, size might not be known until read; allow and check in endpoint
        if size > 0:
            ok, msg = validate_file_size(size, self._settings.max_upload_bytes)
            if not ok:
                return False, msg
        return True, ""

    async def save_upload(self, job_id: str, file: UploadFile) -> Path:
        """Save uploaded file to disk; return path."""
        self._settings.upload_dir.mkdir(parents=True, exist_ok=True)
        path = upload_path_for_job(
            self._settings.upload_dir,
            job_id,
            file.filename or "document.pdf",
        )
        content = await file.read()
        if len(content) > self._settings.max_upload_bytes:
            raise ValueError(f"File size exceeds {self._settings.max_upload_size_mb} MB")
        path.write_bytes(content)
        return path

    def build_upload_response(
        self,
        job_id: str,
        subject: str = "",
        class_name: str = "",
        term: str = "",
        uploaded_by: str = "",
    ) -> UploadResponse:
        return UploadResponse(
            job_id=job_id,
            status=JobStatus.UPLOADED.value,
            subject=subject,
            class_name=class_name,
            term=term,
            uploaded_by=uploaded_by,
        )
