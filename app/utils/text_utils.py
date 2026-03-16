"""Text processing utilities: sanitization, chunking helpers."""
from __future__ import annotations

import re
from typing import Iterator


def sanitize_for_llm(text: str, max_length: int = 100_000) -> str:
    """
    Sanitize text before sending to LLM: remove control chars, limit length.
    """
    if not text or not text.strip():
        return ""
    # Remove control characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_length].strip()


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English)."""
    return max(1, len(text) // 4)


def split_sentences(text: str) -> list[str]:
    """Simple sentence splitter for chunking boundaries."""
    return re.split(r"(?<=[.!?])\s+", text.strip()) if text else []


def iter_chunks(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
    token_estimator: bool = True,
) -> Iterator[tuple[str, int]]:
    """
    Yield (chunk_text, estimated_tokens) with overlap.
    Uses character-based sliding window; overlap is in chars.
    """
    text = text.strip()
    if not text:
        return
    size = chunk_size * 4 if token_estimator else chunk_size  # approx chars
    step = size - overlap
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunk = text[start:end]
        if chunk.strip():
            tokens = estimate_tokens(chunk) if token_estimator else len(chunk) // 4
            yield chunk, tokens
        start += step
        idx += 1
        if start < len(text) and end == len(text):
            break
