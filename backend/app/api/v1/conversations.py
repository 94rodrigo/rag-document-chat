from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, OptionalUser, get_conversation_service
from app.domain.conversations.schemas import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
    SendMessageRequest,
    StreamChunk,
)
from app.domain.conversations.service import ConversationService
from app.shared.pagination import PaginationParams

router = APIRouter(prefix="/conversations", tags=["conversations"])

ConvSvc = Annotated[ConversationService, Depends(get_conversation_service)]


def _sse_line(chunk: StreamChunk) -> str:
    return f"data: {chunk.model_dump_json()}\n\n"


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: CreateConversationRequest,
    svc: ConvSvc,
    current_user: OptionalUser,
    x_anon_session: Annotated[str | None, Header()] = None,
) -> ConversationResponse:
    return await svc.create(
        document_ids=body.document_ids,
        user_id=current_user.id if current_user else None,
        anon_session_id=x_anon_session,
        title=body.title,
    )


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    current_user: CurrentUser,
    svc: ConvSvc,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> list[ConversationResponse]:
    params = PaginationParams(page=page, per_page=per_page)
    result = await svc.list(current_user.id, params)
    return result.items


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    svc: ConvSvc,
    current_user: OptionalUser,
    x_anon_session: Annotated[str | None, Header()] = None,
) -> ConversationDetailResponse:
    return await svc.get_detail(
        conversation_id,
        user_id=current_user.id if current_user else None,
        anon_session_id=x_anon_session,
    )


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    svc: ConvSvc,
    current_user: OptionalUser,
    x_anon_session: Annotated[str | None, Header()] = None,
) -> StreamingResponse:
    """Stream a RAG answer via Server-Sent Events."""

    async def event_generator():
        import uuid as _uuid

        import structlog as _sl
        _log = _sl.get_logger(__name__)
        try:
            async for chunk in svc.stream_message(
                conv_id=conversation_id,
                query=body.content,
                user_id=current_user.id if current_user else None,
                anon_session_id=x_anon_session,
            ):
                yield _sse_line(chunk)
        except Exception:
            ref = str(_uuid.uuid4())[:8]
            _log.exception(
                "event_generator.unexpected_error",
                ref=ref,
                conversation_id=conversation_id,
            )
            error_chunk = StreamChunk(type="error", error=f"Unexpected error (ref: {ref})")
            yield _sse_line(error_chunk)
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    svc: ConvSvc,
    current_user: OptionalUser,
    x_anon_session: Annotated[str | None, Header()] = None,
) -> None:
    await svc.delete(
        conversation_id,
        user_id=current_user.id if current_user else None,
        anon_session_id=x_anon_session,
    )
