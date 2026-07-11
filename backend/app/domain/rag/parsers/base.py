from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedPage:
    page_number: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    total_pages: int
    mime_type: str
    title: str = ""
    author: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.content for p in self.pages if p.content.strip())

    @property
    def page_texts(self) -> list[str]:
        return [p.content for p in self.pages]

    @property
    def page_count(self) -> int:
        return self.total_pages


def clean_text(text: str) -> str:
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
