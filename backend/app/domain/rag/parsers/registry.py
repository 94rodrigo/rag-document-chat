from __future__ import annotations

import structlog

from app.domain.rag.parsers.base import ParsedDocument
from app.shared.exceptions import DocumentProcessingError, UnsupportedFileTypeError

log = structlog.get_logger(__name__)

SUPPORTED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/epub+zip",
    "text/plain",
    "text/markdown",
}

MIME_EXTENSIONS: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/epub+zip": ".epub",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


def parse_document(content: bytes, mime_type: str) -> ParsedDocument:
    if mime_type not in SUPPORTED_MIME_TYPES:
        raise UnsupportedFileTypeError(
            f"Unsupported file type: {mime_type}. "
            f"Supported: {', '.join(sorted(SUPPORTED_MIME_TYPES))}"
        )

    log.info("parser.registry.dispatching", mime_type=mime_type, size_bytes=len(content))

    try:
        if mime_type == "application/pdf":
            from app.domain.rag.parsers.pdf import parse_pdf
            return parse_pdf(content)

        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from app.domain.rag.parsers.docx import parse_docx
            return parse_docx(content, mime_type)

        elif mime_type == "application/msword":
            from app.domain.rag.parsers.doc import parse_doc
            return parse_doc(content)

        elif mime_type == "application/epub+zip":
            from app.domain.rag.parsers.epub import parse_epub
            return parse_epub(content)

        elif mime_type in ("text/plain", "text/markdown"):
            return _parse_text(content, mime_type)

        else:
            raise UnsupportedFileTypeError(mime_type)

    except (UnsupportedFileTypeError, DocumentProcessingError):
        raise
    except Exception as e:
        log.exception("parser.registry.unexpected_error", mime_type=mime_type)
        raise DocumentProcessingError(f"Failed to parse document: {e}") from e


def _parse_text(content: bytes, mime_type: str) -> ParsedDocument:
    import chardet

    from app.domain.rag.parsers.base import ParsedPage, clean_text

    detected = chardet.detect(content)
    encoding = detected.get("encoding") or "utf-8"
    text = content.decode(encoding, errors="replace")
    text = clean_text(text)

    if not text.strip():
        raise DocumentProcessingError("Text file contained no content")

    from app.domain.rag.parsers.base import ParsedDocument

    return ParsedDocument(
        pages=[ParsedPage(page_number=1, content=text)],
        total_pages=1,
        mime_type=mime_type,
    )
