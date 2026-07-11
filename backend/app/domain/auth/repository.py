from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.auth.models import AnonymousSession, RefreshToken, User
from app.shared.utils import utc_now


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: object) -> User:
        user = User(**kwargs)
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def update(self, user: User, **kwargs: object) -> User:
        for key, value in kwargs.items():
            setattr(user, key, value)
        await self._session.flush()
        return user

    async def deactivate(self, user_id: str) -> None:
        await self._session.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token_id: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=utc_now())
        )

    async def revoke_all_for_user(self, user_id: str) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )


class AnonymousSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, token_hash: str, expires_at: datetime, ip_address: str | None = None
    ) -> AnonymousSession:
        anon = AnonymousSession(
            session_token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
        )
        self._session.add(anon)
        await self._session.flush()
        return anon

    async def get_by_hash(self, token_hash: str) -> AnonymousSession | None:
        result = await self._session.execute(
            select(AnonymousSession).where(
                AnonymousSession.session_token_hash == token_hash,
                AnonymousSession.expires_at > utc_now(),
            )
        )
        return result.scalar_one_or_none()

    async def increment_query_count(self, session_id: str) -> int:
        result = await self._session.execute(
            select(AnonymousSession).where(AnonymousSession.id == session_id)
        )
        anon = result.scalar_one_or_none()
        if anon:
            anon.query_count += 1
            anon.last_used_at = utc_now()
            await self._session.flush()
            return anon.query_count
        return 0
