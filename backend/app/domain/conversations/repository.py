from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.conversations.models import Citation, Conversation, Message, MessageRole
from app.shared.pagination import PaginationParams


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> Conversation:
        conv = Conversation(**kwargs)
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def get_by_id(self, conv_id: str) -> Conversation | None:
        return await self._session.get(Conversation, conv_id)

    async def get_by_id_with_messages(self, conv_id: str) -> Conversation | None:
        result = await self._session.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.messages)
                .selectinload(Message.citations)
            )
            .where(Conversation.id == conv_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_owner(
        self, conv_id: str, user_id: str | None, anon_session_id: str | None
    ) -> Conversation | None:
        query = select(Conversation).where(Conversation.id == conv_id)
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        elif anon_session_id:
            query = query.where(Conversation.anon_session_id == anon_session_id)
        else:
            return None
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_user(
        self, user_id: str, params: PaginationParams
    ) -> tuple[list[Conversation], int]:
        count_result = await self._session.execute(
            select(func.count()).select_from(Conversation).where(
                Conversation.user_id == user_id
            )
        )
        total = count_result.scalar_one()

        result = await self._session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(params.offset)
            .limit(params.limit)
        )
        return list(result.scalars().all()), total

    async def update_title(self, conv_id: str, title: str) -> None:
        result = await self._session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.title = title
            await self._session.flush()

    async def delete(self, conv: Conversation) -> None:
        await self._session.delete(conv)
        await self._session.flush()


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> Message:
        msg = Message(**kwargs)
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get_history(
        self, conversation_id: str, limit: int = 20
    ) -> list[Message]:
        result = await self._session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def count_by_conversation(self, conversation_id: str) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()


class CitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, citations: list[Citation]) -> None:
        self._session.add_all(citations)
        await self._session.flush()
