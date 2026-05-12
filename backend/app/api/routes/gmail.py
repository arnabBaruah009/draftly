"""Gmail-related HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.google import GoogleCredentialsDep
from app.core.config import Settings, get_settings
from app.schemas.email import MessagesResponse
from app.services.gmail import GmailService

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.get(
    "/messages",
    response_model=MessagesResponse,
    summary="List the user's most recent Gmail messages",
    responses={
        401: {"description": "Missing or invalid Google access token"},
        403: {"description": "Token does not have the gmail.readonly scope"},
        502: {"description": "Failed to reach Gmail"},
    },
)
async def list_messages(
    credentials: GoogleCredentialsDep,
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(
        default=None,
        ge=1,
        description=(
            "Number of messages to return (1..max_message_limit). "
            "Defaults to the configured default_message_limit."
        ),
    ),
) -> MessagesResponse:
    """Return the latest messages from the authenticated user's inbox.

    The caller authenticates with their Google OAuth2 access token via the
    standard ``Authorization: Bearer <token>`` header. The token must include
    the ``gmail.readonly`` scope.
    """
    effective_limit = min(
        limit or settings.default_message_limit,
        settings.max_message_limit,
    )

    service = GmailService(access_token=credentials.access_token)
    messages = await service.list_latest_messages(limit=effective_limit)

    return MessagesResponse(count=len(messages), messages=messages)
