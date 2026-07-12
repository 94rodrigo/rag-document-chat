from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog

from app.config import get_settings
from app.domain.billing.service import UsageLimitService
from app.domain.conversations.models import MessageRole
from app.domain.conversations.repository import (
    CitationRepository,
    ConversationRepository,
    MessageRepository,
)
from app.domain.conversations.schemas import (
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
    StreamChunk,
)
from app.domain.documents.repository import DocumentRepository
from app.domain.rag.pipeline import RAGPipeline
from app.domain.rag.service import RAGService
from app.infrastructure.llm import ChatProtocol
from app.shared.exceptions import ConversationNotFoundError, PermissionDeniedError
from app.shared.pagination import PaginatedResponse, PaginationParams

log = structlog.get_logger(__name__)
settings = get_settings()


class ConversationService:
    def __init__(
        self,
        conv_repo: ConversationRepository,
        msg_repo: MessageRepository,
        citation_repo: CitationRepository,
        doc_repo: DocumentRepository,
        pipeline: RAGPipeline,
        chat: ChatProtocol,
        usage_svc: UsageLimitService,
    ) -> None:
        self._convs = conv_repo
        self._msgs = msg_repo
        self._citations = citation_repo
        self._docs = doc_repo
        self._usage = usage_svc
        self._rag = RAGService(
            pipeline=pipeline,
            chat=chat,
            doc_repo=doc_repo,
            message_repo=msg_repo,
            citation_repo=citation_repo,
        )

    async def create(
        self,
        document_ids: list[str],
        user_id: str | None,
        anon_session_id: str | None,
        title: str | None = None,
    ) -> ConversationResponse:
        # Verify documents belong to user
        if user_id:
            for doc_id in document_ids:
                doc = await self._docs.get_by_id_and_user(doc_id, user_id)
                if not doc:
                    raise PermissionDeniedError(f"Document {doc_id} not found")

        conv = await self._convs.create(
            user_id=user_id,
            anon_session_id=anon_session_id,
            title=title or "New conversation",
            document_ids=document_ids,
        )
        return self._to_response(conv)

    async def list(
        self, user_id: str, params: PaginationParams
    ) -> PaginatedResponse[ConversationResponse]:
        convs, total = await self._convs.list_for_user(user_id, params)
        items = [self._to_response(c) for c in convs]
        return PaginatedResponse.build(items=items, total=total, params=params)

    async def get_detail(
        self, conv_id: str, user_id: str | None, anon_session_id: str | None
    ) -> ConversationDetailResponse:
        conv = await self._convs.get_by_id_with_messages(conv_id)
        if not conv:
            raise ConversationNotFoundError()
        self._assert_access(conv, user_id, anon_session_id)

        messages = [self._message_to_response(m) for m in conv.messages]
        return ConversationDetailResponse(
            id=conv.id,
            title=conv.title,
            document_ids=conv.document_ids,
            message_count=len(messages),
            last_message=messages[-1].content[:100] if messages else None,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            messages=messages,
        )

    async def stream_message(
        self,
        conv_id: str,
        query: str,
        user_id: str | None,
        anon_session_id: str | None,
    ) -> AsyncGenerator[StreamChunk, None]:
        # Check query limits
        await self._usage.assert_can_query(user_id, anon_session_id)

        conv = await self._convs.get_by_id(conv_id)
        if not conv:
            raise ConversationNotFoundError()
        self._assert_access(conv, user_id, anon_session_id)

        # Check before creating so we detect the first message without lazy-loading conv.messages
        is_first_message = await self._msgs.count_by_conversation(conv_id) == 0

        # Save user message
        await self._msgs.create(
            conversation_id=conv_id,
            role=MessageRole.user,
            content=query,
        )

        # Auto-generate title on first message
        if is_first_message and conv.title == "New conversation":
            title = await self._rag.generate_title(query)
            await self._convs.update_title(conv_id, title)

        history = await self._msgs.get_history(conv_id, limit=10)

        async for chunk in self._rag.stream_answer(
            conversation_id=conv_id,
            user_id=user_id or anon_session_id or "",
            query=query,
            document_ids=conv.document_ids,
            history=history,
        ):
            yield chunk

        # Increment usage counter
        await self._usage.record_query(user_id, anon_session_id)

    async def delete(
        self, conv_id: str, user_id: str | None, anon_session_id: str | None
    ) -> None:
        conv = await self._convs.get_by_id(conv_id)
        if not conv:
            raise ConversationNotFoundError()
        self._assert_access(conv, user_id, anon_session_id)
        await self._convs.delete(conv)

    def _assert_access(
        self,
        conv: object,
        user_id: str | None,
        anon_session_id: str | None,
    ) -> None:
        from app.domain.conversations.models import Conversation
        assert isinstance(conv, Conversation)
        if user_id and conv.user_id != user_id:
            raise PermissionDeniedError()
        if anon_session_id and conv.anon_session_id != anon_session_id:
            raise PermissionDeniedError()

    def _to_response(self, conv: object) -> ConversationResponse:
        from app.domain.conversations.models import Conversation
        assert isinstance(conv, Conversation)
        return ConversationResponse(
            id=conv.id,
            title=conv.title,
            document_ids=conv.document_ids,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    def _message_to_response(self, msg: object) -> MessageResponse:
        from app.domain.conversations.models import Message
        assert isinstance(msg, Message)
        citations = [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "document_name": c.document_name,
                "content": c.content_snippet,
                "page_number": c.page_number,
                "score": c.similarity_score,
            }
            for c in (msg.citations or [])
        ]
        return MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            citations=citations,
            created_at=msg.created_at,
        )
