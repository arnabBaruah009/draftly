"""User profile routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUserDep, get_user_service
from app.auth.google import GoogleCredentialsDep
from app.schemas.email import (
    UpdatePromptRequest,
    UserResponse,
    UserSyncRequest,
)
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/sync",
    response_model=UserResponse,
    summary="Sync user profile and store OAuth tokens",
)
async def sync_user(
    credentials: GoogleCredentialsDep,
    payload: UserSyncRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    user = await user_service.sync_user(
        credentials,
        refresh_token=payload.refresh_token,
        name=payload.name,
    )
    return UserService.to_response(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(user: CurrentUserDep) -> UserResponse:
    return UserService.to_response(user)


@router.patch(
    "/me/prompt",
    response_model=UserResponse,
    summary="Update response prompt and writing style",
)
async def update_prompt(
    user: CurrentUserDep,
    payload: UpdatePromptRequest,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    updated = await user_service.update_preferences(user.id, payload)
    return UserService.to_response(updated)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear stored OAuth tokens",
)
async def logout(
    user: CurrentUserDep,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await user_service.logout(user.id)
