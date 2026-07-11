from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size_bytes: int
    page_count: int | None
    status: str
    error_message: str | None
    chunk_count: int
    created_at: datetime
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
    has_more: bool


class DocumentChunkResponse(BaseModel):
    id: str
    document_id: str
    content: str
    page_number: int | None
    chunk_index: int
    token_count: int

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    document: DocumentResponse
    task_id: str
