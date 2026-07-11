from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.dependencies import CurrentUser, OptionalUser, get_auth_service
from app.domain.auth.schemas import (
    AnonymousSessionResponse,
    AuthResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.domain.auth.service import AuthService
from app.shared.utils import utc_now
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, svc: AuthSvc) -> AuthResponse:
    return await svc.register(body.name, body.email, body.password)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, svc: AuthSvc) -> AuthResponse:
    return await svc.login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshTokenRequest, svc: AuthSvc) -> TokenResponse:
    return await svc.refresh(body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshTokenRequest,
    current_user: CurrentUser,
    svc: AuthSvc,
) -> None:
    await svc.logout(body.refresh_token, current_user.id)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post("/anonymous", response_model=AnonymousSessionResponse)
async def create_anonymous_session(request: Request, svc: AuthSvc) -> AnonymousSessionResponse:
    """Create an anonymous session for unauthenticated usage."""
    ip = request.client.host if request.client else None
    raw_token, session = await svc.create_anonymous_session(ip_address=ip)
    queries_remaining = max(0, settings.anon_session_max_queries - session.query_count)
    return AnonymousSessionResponse(
        session_token=raw_token,
        queries_remaining=queries_remaining,
        expires_at=session.expires_at,
    )
