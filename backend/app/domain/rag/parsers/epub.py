from __future__ import annotations

import re

import structlog

from app.domain.rag.parsers.base import ParsedDocument, ParsedPage, clean_text
from app.shared.exceptions import DocumentProcessingError

log = structlog.get_logger(__name__)

_EPUB_MIME = "application/epub+zip"


def parse_epub(content: bytes) -> ParsedDocument:
    try:
        import ebooklib  # type: ignore[import-untyped]
        from ebooklib import epub
    except ImportError as e:
        raise DocumentProcessingError("ebooklib is required for EPUB parsing") from e

    try:
        import io

        book = epub.read_epub(io.BytesIO(content))
        pages: list[ParsedPage] = []
        page_num = 1

        title = book.get_metadata("DC", "title")
        book_title = str(title[0][0]) if title else ""
        authors = book.get_metadata("DC", "creator")
        book_author = str(authors[0][0]) if authors else ""

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            html_content = item.get_content().decode("utf-8", errors="replace")
            text = _strip_html(html_content)
            text = clean_text(text)

            if text.strip():
                pages.append(ParsedPage(page_number=page_num, content=text))
                page_num += 1

        if not pages:
            raise DocumentProcessingError("EPUB contained no extractable text")

        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            mime_type=_EPUB_MIME,
            title=book_title,
            author=book_author,
        )

    except DocumentProcessingError:
        raise
    except Exception as e:
        log.exception("parser.epub.failed")
        raise DocumentProcessingError(f"EPUB parsing failed: {e}") from e


def _strip_html(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</(p|div|h[1-6]|li|tr|td|th)>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", "", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"&#\d+;", "", html)
    return html
