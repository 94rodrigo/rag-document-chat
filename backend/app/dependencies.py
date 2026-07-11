from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import Cookie, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.auth.models import User
from app.domain.auth.repository import (
    AnonymousSessionRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.domain.auth.service import AuthService, decode_access_token
from app.domain.billing.repository import SubscriptionRepository, UsageRepository
from app.domain.billing.service import BillingService, UsageLimitService
from app.domain.conversations.repository import (
    CitationRepository,
    ConversationRepository,
    MessageRepository,
)
from app.domain.conversations.service import ConversationService
from app.domain.documents.repository import ChunkRepository, DocumentRepository
from app.domain.documents.service import DocumentService
from app.domain.rag.pipeline import RAGPipeline, build_pipeline
from app.infrastructure.database import get_db
from app.infrastructure.llm import get_chat
from app.infrastructure.redis import CacheService, get_redis
from app.infrastructure.storage import get_storage
from app.shared.exceptions import AuthenticationError, InvalidTokenError

log = structlog.get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)

# ── Type aliases ──────────────────────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]

# ── Repository deps ───────────────────────────────────────────────────────────

def get_user_repo(db: DbSession) -> UserRepository:
    return UserRepository(db)

def get_refresh_token_repo(db: DbSession) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)

def get_anon_session_repo(db: DbSession) -> AnonymousSessionRepository:
    return AnonymousSessionRepository(db)

def get_document_repo(db: DbSession) -> DocumentRepository:
    return DocumentRepository(db)

def get_chunk_repo(db: DbSession) -> ChunkRepository:
    return ChunkRepository(db)

def get_conversation_repo(db: DbSession) -> ConversationRepository:
    return ConversationRepository(db)

def get_message_repo(db: DbSession) -> MessageRepository:
    return MessageRepository(db)

def get_citation_repo(db: DbSession) -> CitationRepository:
    return CitationRepository(db)

def get_subscription_repo(db: DbSession) -> SubscriptionRepository:
    return SubscriptionRepository(db)

def get_usage_repo(db: DbSession) -> UsageRepository:
    return UsageRepository(db)

# ── Service deps ──────────────────────────────────────────────────────────────

def get_cache_service(redis: RedisClient) -> CacheService:
    return CacheService(redis)

def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    token_repo: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repo)],
    anon_repo: Annotated[AnonymousSessionRepository, Depends(get_anon_session_repo)],
) -> AuthService:
    return AuthService(user_repo, token_repo, anon_repo)

def get_usage_limit_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    doc_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    usage_repo: Annotated[UsageRepository, Depends(get_usage_repo)],
    anon_repo: Annotated[AnonymousSessionRepository, Depends(get_anon_session_repo)],
) -> UsageLimitService:
    return UsageLimitService(user_repo, doc_repo, usage_repo, anon_repo)

def get_document_service(
    doc_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    chunk_repo: Annotated[ChunkRepository, Depends(get_chunk_repo)],
    usage_svc: Annotated[UsageLimitService, Depends(get_usage_limit_service)],
) -> DocumentService:
    return DocumentService(doc_repo, chunk_repo, get_storage(), usage_svc)

def get_rag_pipeline(db: DbSession) -> RAGPipeline:
    return build_pipeline(session=db)


def get_conversation_service(
    conv_repo: Annotated[ConversationRepository, Depends(get_conversation_repo)],
    msg_repo: Annotated[MessageRepository, Depends(get_message_repo)],
    citation_repo: Annotated[CitationRepository, Depends(get_citation_repo)],
    doc_repo: Annotated[DocumentRepository, Depends(get_document_repo)],
    pipeline: Annotated[RAGPipeline, Depends(get_rag_pipeline)],
    usage_svc: Annotated[UsageLimitService, Depends(get_usage_limit_service)],
) -> ConversationService:
    return ConversationService(
        conv_repo=conv_repo,
        msg_repo=msg_repo,
        citation_repo=citation_repo,
        doc_repo=doc_repo,
        pipeline=pipeline,
        chat=get_chat(),
        usage_svc=usage_svc,
    )

def get_billing_service(
    sub_repo: Annotated[SubscriptionRepository, Depends(get_subscription_repo)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> BillingService:
    return BillingService(sub_repo, user_repo)

# ── Auth current-user deps ────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> User:
    """Require authenticated user. Raises 401 if missing/invalid."""
    if not credentials:
        raise AuthenticationError()
    payload = decode_access_token(credentials.credentials)
    user = await user_repo.get_by_id(payload["sub"])
    if not user or not user.is_active:
        raise InvalidTokenError()
    return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> User | None:
    """Return authenticated user or None for anonymous callers."""
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user = await user_repo.get_by_id(payload["sub"])
        return user if (user and user.is_active) else None
    except Exception:
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
