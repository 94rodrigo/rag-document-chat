from __future__ import annotations

import structlog

from app.config import get_settings
from app.domain.billing.service import UsageLimitService
from app.domain.documents.models import DocumentStatus
from app.domain.documents.repository import ChunkRepository, DocumentRepository
from app.domain.documents.schemas import DocumentResponse, DocumentSearchResult, UploadResponse
from app.domain.rag.parsers.registry import SUPPORTED_MIME_TYPES
from app.domain.rag.pipeline import RAGPipeline
from app.infrastructure.storage import StorageService
from app.shared.exceptions import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.shared.pagination import PaginatedResponse, PaginationParams
from app.shared.utils import build_s3_key, generate_id, safe_filename

log = structlog.get_logger(__name__)
settings = get_settings()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Magic byte signatures for each supported MIME type
_MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "application/pdf": [b"%PDF"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK\x03\x04"],
    "application/msword": [b"\xd0\xcf\x11\xe0"],          # Compound Document File
    "application/epub+zip": [b"PK\x03\x04"],
    "text/plain": [],    # validated separately (UTF-8 decodable)
    "text/markdown": [], # validated separately (UTF-8 decodable)
}


def _detect_mime_from_magic(content: bytes) -> str | None:
    """Return the detected MIME type from magic bytes, or None if unrecognised."""
    header = content[:8]
    if header[:4] == b"%PDF":
        return "application/pdf"
    if header[:4] == b"PK\x03\x04":
        # Both DOCX and EPUB are ZIP-based; rely on Content-Type to disambiguate
        return "zip-based"
    if header[:4] == b"\xd0\xcf\x11\xe0":
        return "application/msword"
    # Plain text: must be valid UTF-8
    try:
        content[:1024].decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        return None


def _validate_mime(content: bytes, claimed_mime: str) -> None:
    """
    Reject uploads where the file magic bytes contradict the claimed Content-Type.
    Prevents polyglot files and MIME confusion attacks.
    """
    detected = _detect_mime_from_magic(content)

    if claimed_mime == "application/pdf":
        if detected != "application/pdf":
            raise UnsupportedFileTypeError("File is not a valid PDF (magic bytes mismatch)")

    elif claimed_mime == "application/msword":
        if detected != "application/msword":
            raise UnsupportedFileTypeError("File is not a valid .doc file (magic bytes mismatch)")

    elif claimed_mime in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/epub+zip",
    ):
        if detected != "zip-based":
            raise UnsupportedFileTypeError(
                f"File does not have a valid ZIP/Office structure for {claimed_mime}"
            )

    # Being lenient: text detection is fuzzy, so reject only clear binary — _detect_mime_from_magic
    # returns None exactly when the bytes are not valid UTF-8.
    elif claimed_mime in ("text/plain", "text/markdown") and detected is None:
        raise UnsupportedFileTypeError("File contains invalid characters for a text file")


class DocumentService:
    def __init__(
        self,
        doc_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        storage: StorageService,
        usage_svc: UsageLimitService,
        pipeline: RAGPipeline,
    ) -> None:
        self._docs = doc_repo
        self._chunks = chunk_repo
        self._storage = storage
        self._usage = usage_svc
        self._pipeline = pipeline

    async def upload(
        self,
        user_id: str,
        filename: str,
        content: bytes,
        mime_type: str,
    ) -> UploadResponse:
        # Guard: file type (check allowed list first)
        if mime_type not in SUPPORTED_MIME_TYPES:
            raise UnsupportedFileTypeError(f"Unsupported type: {mime_type}")

        # Guard: magic bytes must match claimed MIME type
        _validate_mime(content, mime_type)

        # Guard: file size
        if len(content) > MAX_FILE_SIZE:
            raise FileTooLargeError(
                f"File exceeds {MAX_FILE_SIZE // 1024 // 1024} MB limit"
            )

        # Guard: storage and document count limits
        await self._usage.assert_can_upload(user_id, len(content))

        doc_id = generate_id()
        safe_name = safe_filename(filename)
        s3_key = build_s3_key(user_id, doc_id, safe_name)

        await self._storage.upload(
            key=s3_key,
            data=content,
            content_type=mime_type,
            metadata={"user_id": user_id, "document_id": doc_id},
        )

        doc = await self._docs.create(
            id=doc_id,
            user_id=user_id,
            name=safe_name,
            original_name=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            s3_key=s3_key,
            status=DocumentStatus.processing,
        )

        from app.workers.tasks.document_processing import process_document
        task = process_document.delay(doc_id)

        log.info("document.upload", doc_id=doc_id, user_id=user_id, size=len(content))
        return UploadResponse(
            document=DocumentResponse.model_validate(doc),
            task_id=task.id,
        )

    async def list(
        self, user_id: str, params: PaginationParams
    ) -> PaginatedResponse[DocumentResponse]:
        docs, total = await self._docs.list_for_user(user_id, params)
        return PaginatedResponse.build(
            items=[DocumentResponse.model_validate(d) for d in docs],
            total=total,
            params=params,
        )

    async def get(self, doc_id: str, user_id: str) -> DocumentResponse:
        doc = await self._docs.get_by_id_and_user(doc_id, user_id)
        if not doc:
            raise DocumentNotFoundError()
        return DocumentResponse.model_validate(doc)

    async def get_raw(self, doc_id: str, user_id: str) -> bytes:
        doc = await self._docs.get_by_id_and_user(doc_id, user_id)
        if not doc:
            raise DocumentNotFoundError()
        return await self._storage.download(doc.s3_key)

    async def get_chunks(self, doc_id: str, user_id: str) -> list:
        doc = await self._docs.get_by_id_and_user(doc_id, user_id)
        if not doc:
            raise DocumentNotFoundError()
        return await self._chunks.get_by_document(doc_id)

    async def search(self, user_id: str, query: str) -> list[DocumentSearchResult]:
        """Semantic search across every ready document the user owns — the same
        retrieve → rerank path chat uses, minus the LLM call."""
        ready_docs = await self._docs.list_ready_for_user(user_id)
        if not ready_docs:
            return []

        document_ids = [d.id for d in ready_docs]
        document_names = {d.id: d.name for d in ready_docs}

        chunks = await self._pipeline.retrieve_and_rerank(
            query=query,
            user_id=user_id,
            document_ids=document_ids,
            document_names=document_names,
        )

        return [
            DocumentSearchResult(
                id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_name=chunk.document_name,
                content=chunk.content,
                page_number=chunk.page_number,
                score=chunk.final_score,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]

    async def delete(self, doc_id: str, user_id: str) -> None:
        doc = await self._docs.get_by_id_and_user(doc_id, user_id)
        if not doc:
            raise DocumentNotFoundError()

        await self._storage.delete(doc.s3_key)
        await self._chunks.delete_by_document(doc_id)
        await self._docs.delete(doc)
        log.info("document.delete", doc_id=doc_id, user_id=user_id)
