from __future__ import annotations

from io import BytesIO
from typing import Any

import structlog

from app.domain.rag.parsers.base import ParsedDocument, ParsedPage, clean_text
from app.shared.exceptions import DocumentProcessingError

log = structlog.get_logger(__name__)


def parse_pdf(content: bytes) -> ParsedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise DocumentProcessingError("pypdf is required for PDF parsing") from e

    try:
        reader = PdfReader(BytesIO(content))
        pages: list[ParsedPage] = []

        for i, page in enumerate(reader.pages, start=1):
            raw = page.extract_text() or ""
            text = clean_text(raw)
            if text:
                pages.append(ParsedPage(page_number=i, content=text))

        if not pages:
            raise DocumentProcessingError("PDF contained no extractable text")

        meta: dict[str, Any] = {}
        title = ""
        author = ""
        if reader.metadata:
            title = str(reader.metadata.get("/Title") or "")
            author = str(reader.metadata.get("/Author") or "")
            meta = {
                "subject": str(reader.metadata.get("/Subject") or ""),
                "creator": str(reader.metadata.get("/Creator") or ""),
            }

        return ParsedDocument(
            pages=pages,
            total_pages=len(reader.pages),
            mime_type="application/pdf",
            title=title,
            author=author,
            metadata=meta,
        )

    except DocumentProcessingError:
        raise
    except Exception as e:
        log.exception("parser.pdf.failed")
        raise DocumentProcessingError(f"PDF parsing failed: {e}") from e
