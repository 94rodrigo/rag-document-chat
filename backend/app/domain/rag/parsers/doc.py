from __future__ import annotations

import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

import structlog

from app.domain.rag.parsers.base import ParsedDocument, ParsedPage, clean_text
from app.shared.exceptions import DocumentProcessingError, UnsupportedFileTypeError

log = structlog.get_logger(__name__)

_DOC_MIME = "application/msword"


def parse_doc(content: bytes) -> ParsedDocument:
    """
    Parse legacy .doc files. Strategy:
    1. Try mammoth (works if file is actually OOXML masquerading as .doc)
    2. Fall back to LibreOffice headless conversion
    3. Raise UnsupportedFileTypeError with clear instructions if neither works
    """
    try:
        return _parse_with_mammoth(content)
    except Exception as mammoth_err:
        log.debug("parser.doc.mammoth_failed", error=str(mammoth_err))

    try:
        return _parse_with_libreoffice(content)
    except Exception as lo_err:
        log.debug("parser.doc.libreoffice_failed", error=str(lo_err))

    raise UnsupportedFileTypeError(
        "Legacy .doc files require LibreOffice installed on the server. "
        "Install with: sudo apt install libreoffice-writer. "
        "Alternatively, save the file as .docx and re-upload."
    )


def _parse_with_mammoth(content: bytes) -> ParsedDocument:
    import mammoth  # type: ignore[import-untyped]

    result = mammoth.extract_raw_text(BytesIO(content))
    text = clean_text(result.value)

    if not text.strip():
        raise DocumentProcessingError("mammoth extracted empty text")

    return ParsedDocument(
        pages=[ParsedPage(page_number=1, content=text)],
        total_pages=1,
        mime_type=_DOC_MIME,
    )


def _parse_with_libreoffice(content: bytes) -> ParsedDocument:
    libreoffice = _find_libreoffice()
    if not libreoffice:
        raise DocumentProcessingError("LibreOffice not found on PATH")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.doc"
        input_path.write_bytes(content)

        # Use `unshare --net` to run LibreOffice in a network namespace with no
        # external access, preventing SSRF via DDE fields, OLE links, or remote
        # images embedded in .doc files.
        #
        # Requires Linux with user namespaces enabled:
        #   sysctl kernel.unprivileged_userns_clone=1  (Debian/Ubuntu)
        #
        # If unshare is unavailable we run LibreOffice directly but log a warning.
        _unshare = _find_binary("unshare")
        if _unshare:
            cmd = [_unshare, "--net", libreoffice]
        else:
            log.warning(
                "parser.doc.libreoffice_no_network_isolation",
                hint="Install util-linux and enable unprivileged user namespaces",
            )
            cmd = [libreoffice]

        cmd += [
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--convert-to",
            "txt:Text",
            "--outdir",
            tmpdir,
            str(input_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            # Prevent inheriting sensitive environment variables
            env={"HOME": tmpdir, "PATH": "/usr/bin:/bin"},
        )

        if result.returncode != 0:
            raise DocumentProcessingError(
                f"LibreOffice conversion failed: {result.stderr[:500]}"
            )

        output_path = Path(tmpdir) / "input.txt"
        if not output_path.exists():
            raise DocumentProcessingError("LibreOffice produced no output file")

        raw = output_path.read_text(encoding="utf-8", errors="replace")
        text = clean_text(raw)

        if not text.strip():
            raise DocumentProcessingError("LibreOffice conversion produced empty text")

        return ParsedDocument(
            pages=[ParsedPage(page_number=1, content=text)],
            total_pages=1,
            mime_type=_DOC_MIME,
        )


def _find_libreoffice() -> str | None:
    return _find_binary("libreoffice") or _find_binary("soffice")


def _find_binary(name: str) -> str | None:
    try:
        result = subprocess.run(
            ["which", name], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None
