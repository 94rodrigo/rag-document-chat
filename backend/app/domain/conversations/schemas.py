from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    document_ids: list[str] = Field(..., min_length=1, max_length=20)
    title: str | None = Field(None, max_length=512)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=16_000)


class CitationResponse(BaseModel):
    chunk_id: str | None
    document_id: str
    document_name: str
    content: str
    page_number: int | None
    score: float

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[CitationResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    title: str
    document_ids: list[str]
    message_count: int = 0
    last_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


class StreamChunk(BaseModel):
    type: str          # text | citation | done | error
    content: str | None = None
    citation: CitationResponse | None = None
    error: str | None = None
