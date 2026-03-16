"""Validation agent: ensures correctness and removes duplicates."""
from __future__ import annotations

import re
from typing import Sequence


class ValidationAgent:
    """Validates and deduplicates generated MCQ text."""

    def validate_format(self, mcq_text: str) -> bool:
        """Check that text has expected exam structure (Answer:, options, etc.)."""
        if not mcq_text or len(mcq_text.strip()) < 50:
            return False
        has_answer = "Answer:" in mcq_text or "answer:" in mcq_text.lower()
        has_options = re.search(r"\([A-D]\)", mcq_text) is not None
        return has_answer and has_options

    def remove_duplicate_questions(self, mcq_text: str) -> str:
        """
        Simple dedup: split by numbered 'N. ' pattern and keep unique
        question stems (first line after number).
        """
        parts = re.split(r"\n\s*\d+\.\s+", mcq_text.strip())
        seen: set[str] = set()
        kept: list[str] = []
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            first_line = part.split("\n")[0].strip()[:80]
            if first_line in seen:
                continue
            seen.add(first_line)
            prefix = "" if i == 0 else f"{len(kept) + 1}. "
            kept.append(prefix + part)
        return "\n\n".join(kept).strip()

    def sanitize_output(self, mcq_text: str) -> str:
        """Remove common LLM artifacts (markdown code blocks, extra headers)."""
        text = mcq_text.strip()
        for pattern in [r"^```\w*\n", r"\n```\s*$", r"^#+\s*"]:
            text = re.sub(pattern, "", text, flags=re.MULTILINE)
        text = self._cleanup_placeholders(text)
        return text.strip()

    def _cleanup_placeholders(self, text: str) -> str:
        """Remove placeholder template lines accidentally echoed by the model."""
        cleaned_lines: list[str] = []
        for line in text.splitlines():
            normalized = line.strip().lower()
            if normalized in {"question in english", "(tamil translation)", "tamil translation"}:
                continue
            cleaned_lines.append(line)

        cleaned = "\n".join(cleaned_lines)

        # Convert patterns like "1. Question in English" to just "1."
        cleaned = re.sub(
            r"(?im)^(\s*\d+\.)\s*question in english\s*$",
            r"\1",
            cleaned,
        )
        return cleaned

    def process(self, mcq_text: str) -> str:
        """Full validation pipeline: sanitize, validate, deduplicate."""
        text = self.sanitize_output(mcq_text)
        if not self.validate_format(text):
            return text  # Return as-is if invalid; caller may log
        return self.remove_duplicate_questions(text)
