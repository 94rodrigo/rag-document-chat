from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

import tiktoken


@dataclass
class TextChunk:
    content: str
    chunk_index: int
    token_count: int
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ChunkerProtocol(Protocol):
    async def chunk(self, pages: list[tuple[int | None, str]]) -> list[TextChunk]:
        """
        pages: list of (page_number, text) tuples.
        Returns ordered list of TextChunks.
        """
        ...


def get_tokenizer(model: str = "cl100k_base") -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, tokenizer: tiktoken.Encoding) -> int:
    return len(tokenizer.encode(text))


def split_sentences(text: str) -> list[str]:
    """Sentence splitter that respects paragraph and punctuation boundaries."""
    paragraphs = re.split(r"\n\n+", text)
    sentences: list[str] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\'])", para)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences
