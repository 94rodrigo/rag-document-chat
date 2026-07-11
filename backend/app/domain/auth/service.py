from __future__ import annotations

import uuid
from datetime import UTC, timedelta

import bcrypt
import structlog

from app.config import get_settings
from app.domain.auth.models import AnonymousSession, Plan, RefreshToken, User
from app.domain.auth.repository import (
    AnonymousSessionRepository,
    RefreshTokenRepository,
    UserRepository,
)
from app.domain.auth.schemas import AuthResponse, TokenResponse, UserResponse
from app.shared.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
    RateLimitExceededError,
)
from app.shared.utils import generate_token, hash_token, utc_now

log = structlog.get_logger(__name__)
settings = get_settings()

_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_WINDOW_SECONDS = 900   # 15 minutes
_LOCKOUT_KEY_PREFIX = "auth:lockout:"


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _lockout_key(email: str) -> str:
    import hashlib
    return _LOCKOUT_KEY_PREFIX + hashlib.sha256(email.lower().encode()).hexdigest()[:32]


async def _check_lockout(email: str) -> None:
    """Raise RateLimitExceededError if the account is temporarily locked."""
    from redis.asyncio import Redis
    from app.infrastructure.redis import get_pool, CacheService
    client: Redis = Redis(connection_pool=get_pool())
    cache = CacheService(client)
    try:
        count = await cache.get_int(_lockout_key(email))
        if count >= _MAX_FAILED_ATTEMPTS:
            ttl = await cache.ttl(_lockout_key(email))
            raise RateLimitExceededError(
                f"Too many failed login attempts. Try again in {max(ttl, 1)} seconds."
            )
    finally:
        await client.aclose()


async def _record_failed_login(email: str) -> None:
    from redis.asyncio import Redis
    from app.infrastructure.redis import get_pool, CacheService
    client: Redis = Redis(connection_pool=get_pool())
    cache = CacheService(client)
    try:
        await cache.increment(_lockout_key(email), ttl=_LOCKOUT_WINDOW_SECONDS)
    finally:
        await client.aclose()


async def _clear_lockout(email: str) -> None:
    from redis.asyncio import Redis
    from app.infrastructure.redis import get_pool, CacheService
    client: Redis = Redis(connection_pool=get_pool())
    cache = CacheService(client)
    try:
        await cache.delete(_lockout_key(email))
    finally:
        await client.aclose()


def _create_access_token(user_id: str, email: str, plan: str) -> tuple[str, int]:
    from jose import jwt

    now = utc_now()
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "plan": plan,
        "jti": str(uuid.uuid4()),   # enables per-token revocation
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_access_token_expire_minutes * 60


def decode_access_token(token: str) -> dict:
    from jose import JWTError, jwt
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise InvalidTokenError()
        return payload
    except JWTError as e:
        raise InvalidTokenError() from e


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        anon_repo: AnonymousSessionRepository,
    ) -> None:
        self._users = user_repo
        self._tokens = token_repo
        self._anon = anon_repo

    async def register(self, name: str, email: str, password: str) -> AuthResponse:
        existing = await self._users.get_by_email(email)
        if existing:
            raise EmailAlreadyRegisteredError()

        user = await self._users.create(
            name=name,
            email=email.lower(),
            hashed_password=_hash_password(password),
            plan=Plan.free,
        )
        log.info("auth.register", user_id=user.id)
        return await self._issue_tokens(user)

    async def login(self, email: str, password: str) -> AuthResponse:
        await _check_lockout(email)

        user = await self._users.get_by_email(email)

        # Always run bcrypt verify to prevent timing-based user enumeration
        dummy_hash = "$2b$12$UbLbjER8qpWANMJk1MJBaumL7bTvLMtQ.HIbP2tg19sPUOLdOknvC"
        candidate_hash = user.hashed_password if (user and user.hashed_password) else dummy_hash
        password_ok = _verify_password(password, candidate_hash)

        if not user or not password_ok or not user.is_active:
            await _record_failed_login(email)
            log.warning("auth.login_failed", email=email[:3] + "***")
            raise InvalidCredentialsError()

        await _clear_lockout(email)
        log.info("auth.login", user_id=user.id)
        return await self._issue_tokens(user)

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        token_hash = hash_token(raw_refresh_token)
        record = await self._tokens.get_by_hash(token_hash)
        if not record or not record.is_valid:
            raise InvalidTokenError()

        user = await self._users.get_by_id(record.user_id)
        if not user or not user.is_active:
            raise InvalidTokenError()

        await self._tokens.revoke(record.id)
        access_token, expires_in = _create_access_token(user.id, user.email, user.plan)
        new_refresh = await self._create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh,
            expires_in=expires_in,
        )

    async def logout(self, raw_refresh_token: str | None, user_id: str) -> None:
        if raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            record = await self._tokens.get_by_hash(token_hash)
            if record:
                await self._tokens.revoke(record.id)
        log.info("auth.logout", user_id=user_id)

    async def create_anonymous_session(
        self, ip_address: str | None = None
    ) -> tuple[str, AnonymousSession]:
        raw_token = generate_token(32)
        token_hash = hash_token(raw_token)
        expires_at = utc_now() + timedelta(days=settings.anon_session_ttl_days)
        session = await self._anon.create(
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
        )
        return raw_token, session

    async def get_anonymous_session(self, raw_token: str) -> AnonymousSession | None:
        return await self._anon.get_by_hash(hash_token(raw_token))

    async def _issue_tokens(self, user: User) -> AuthResponse:
        access_token, expires_in = _create_access_token(user.id, user.email, user.plan)
        raw_refresh = await self._create_refresh_token(user.id)
        return AuthResponse(
            user=UserResponse.model_validate(user),
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=raw_refresh,
                expires_in=expires_in,
            ),
        )

    async def _create_refresh_token(self, user_id: str) -> str:
        raw = generate_token(48)
        hashed = hash_token(raw)
        expires_at = utc_now() + timedelta(days=settings.jwt_refresh_token_expire_days)
        await self._tokens.create(
            user_id=user_id,
            token_hash=hashed,
            expires_at=expires_at,
        )
        return raw
