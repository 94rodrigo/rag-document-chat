from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from app.dependencies import CurrentUser, get_auth_service
from app.domain.auth.schemas import ChangePasswordRequest, UserResponse
from app.domain.auth.service import AuthService

router = APIRouter(prefix="/users", tags=["users"])

AuthSvc = Annotated[AuthService, Depends(get_auth_service)]


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    avatar_url: str | None = None
    notify_document_processing: bool | None = None
    notify_weekly_summary: bool | None = None
    notify_product_updates: bool | None = None


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: CurrentUser,
    svc: AuthSvc,
) -> UserResponse:
    user = await svc._users.update(
        current_user,
        **{k: v for k, v in body.model_dump().items() if v is not None},
    )
    return UserResponse.model_validate(user)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    svc: AuthSvc,
) -> None:
    from app.domain.auth.service import _verify_password, _hash_password
    from app.shared.exceptions import InvalidCredentialsError

    if not current_user.hashed_password:
        raise InvalidCredentialsError("No password set")
    if not _verify_password(body.current_password, current_user.hashed_password):
        raise InvalidCredentialsError()

    await svc._users.update(
        current_user,
        hashed_password=_hash_password(body.new_password),
    )


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(current_user: CurrentUser, svc: AuthSvc) -> None:
    await svc._users.deactivate(current_user.id)
    await svc._tokens.revoke_all_for_user(current_user.id)
