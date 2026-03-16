"""MCQ question and related Pydantic models."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MCQOption(BaseModel):
    """Single option for an MCQ."""

    label: str  # A, B, C, D
    text_en: str
    text_ta: str
    is_correct: bool = False


class MCQQuestion(BaseModel):
    """Single MCQ with bilingual content."""

    id: UUID | None = None
    job_id: str
    question_en: str
    question_ta: str
    options: list[MCQOption] = Field(default_factory=list)
    correct_answer: str  # A, B, C, D
    explanation: str
    source_chunk_id: str | None = None
    created_at: datetime | None = None

    def to_exam_format(self) -> str:
        """Format as exam-style text (no JSON/markdown)."""
        opts = "\n".join(
            f"({o.label}) {o.text_en} / {o.text_ta}" for o in self.options
        )
        return (
            f"1. {self.question_en}\n   ({self.question_ta})\n\n"
            f"{opts}\n\n"
            f"Answer: ({self.correct_answer})\n\n"
            f"Explanation: {self.explanation}"
        )


class MCQGenerateRequest(BaseModel):
    """Request body for direct MCQ generation from text."""

    text_chunk: str = Field(..., min_length=50)
    num_questions: int = Field(default=5, ge=1, le=15)


class MCQGenerateResponse(BaseModel):
    """Response containing generated MCQs as formatted text."""

    job_id: str | None = None
    questions_text: str
    num_generated: int = 0
