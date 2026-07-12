from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, UploadFile, status
from fastapi.responses import Response

from app.dependencies import CurrentUser, get_document_service
from app.domain.documents.schemas import (
    DocumentChunkResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentSearchResult,
    UploadResponse,
)
from app.domain.documents.service import DocumentService
from app.shared.pagination import PaginationParams

router = APIRouter(prefix="/documents", tags=["documents"])

DocSvc = Annotated[DocumentService, Depends(get_document_service)]

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    current_user: CurrentUser,
    svc: DocSvc,
) -> UploadResponse:
    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    return await svc.upload(
        user_id=current_user.id,
        filename=file.filename or "document",
        content=content,
        mime_type=mime_type,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser,
    svc: DocSvc,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> DocumentListResponse:
    params = PaginationParams(page=page, per_page=per_page)
    result = await svc.list(current_user.id, params)
    return DocumentListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        per_page=result.per_page,
        has_more=result.has_more,
    )


@router.get("/search", response_model=list[DocumentSearchResult])
async def search_documents(
    current_user: CurrentUser,
    svc: DocSvc,
    q: str = Query(..., min_length=2, max_length=500),
) -> list[DocumentSearchResult]:
    """Semantic search across every ready document the user owns. Registered
    before /{document_id} so "search" is never swallowed as a document id."""
    return await svc.search(current_user.id, q)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    svc: DocSvc,
) -> DocumentResponse:
    return await svc.get(document_id, current_user.id)


@router.get("/{document_id}/file")
async def download_document(
    document_id: str,
    current_user: CurrentUser,
    svc: DocSvc,
    download: bool = Query(default=False),
) -> Response:
    from urllib.parse import quote
    content = await svc.get_raw(document_id, current_user.id)
    doc = await svc._docs.get_by_id_and_user(document_id, current_user.id)
    filename = doc.name if doc else "document"
    disposition = "attachment" if download else "inline"
    return Response(
        content=content,
        media_type=doc.mime_type if doc else "application/octet-stream",
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename, safe='')}",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
        },
    )


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkResponse])
async def list_document_chunks(
    document_id: str,
    current_user: CurrentUser,
    svc: DocSvc,
) -> list[DocumentChunkResponse]:
    chunks = await svc.get_chunks(document_id, current_user.id)
    return [DocumentChunkResponse.model_validate(c) for c in chunks]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    svc: DocSvc,
) -> None:
    await svc.delete(document_id, current_user.id)
