"""Repository layer for jobs and questions."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobModel, QuestionModel


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        job_id: str,
        file_name: str = "",
        file_path: str = "",
        subject: str = "",
        class_name: str = "",
        term: str = "",
        uploaded_by: str = "",
    ) -> JobModel:
        job = JobModel(
            id=job_id,
            status="uploaded",
            file_name=file_name,
            file_path=file_path,
            subject=subject,
            class_name=class_name,
            term=term,
            uploaded_by=uploaded_by,
        )
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: str) -> JobModel | None:
        result = await self._session.execute(select(JobModel).where(JobModel.id == job_id))
        return result.scalars().first()

    async def update_status(
        self,
        job_id: str,
        status: str,
        error: str | None = None,
        chunks_count: int | None = None,
        questions_count: int | None = None,
    ) -> None:
        values: dict = {"status": status, "updated_at": datetime.utcnow()}
        if error is not None:
            values["error"] = error
        if chunks_count is not None:
            values["chunks_count"] = chunks_count
        if questions_count is not None:
            values["questions_count"] = questions_count
        await self._session.execute(update(JobModel).where(JobModel.id == job_id).values(**values))

    async def set_file_path(self, job_id: str, file_path: str) -> None:
        await self._session.execute(
            update(JobModel).where(JobModel.id == job_id).values(file_path=file_path, updated_at=datetime.utcnow())
        )


class QuestionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job_id: str, content: str) -> QuestionModel:
        q = QuestionModel(job_id=job_id, content=content)
        self._session.add(q)
        await self._session.flush()
        return q

    async def get_all_text(self, job_id: str) -> list[str]:
        result = await self._session.execute(
            select(QuestionModel.content).where(QuestionModel.job_id == job_id).order_by(QuestionModel.created_at)
        )
        return list(result.scalars().all())

    async def count(self, job_id: str) -> int:
        result = await self._session.execute(
            select(func.count(QuestionModel.id)).where(QuestionModel.job_id == job_id)
        )
        return result.scalar() or 0
