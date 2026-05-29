"""Gmail-related HTTP routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserDep, get_draft_repository
from app.auth.google import GoogleCredentialsDep
from app.core.config import Settings, get_settings
from app.core.database import get_database
from app.repositories.draft import DraftRepository
from app.repositories.email_record import EmailRecordRepository
from app.repositories.user import TokenStore, UserRepository
from app.schemas.email import EmailDetail, MessagesResponse
from app.services.ai import AIService
from app.services.email_processor import EmailProcessor
from app.services.embeddings import EmbeddingService
from app.services.gmail import GmailService
from app.services.user import UserService

router = APIRouter(prefix="/gmail", tags=["gmail"])


def _build_email_processor(settings: Settings) -> EmailProcessor:
    db = get_database()
    return EmailProcessor(
        UserService(UserRepository(db), TokenStore(), settings),
        EmailRecordRepository(db),
        DraftRepository(db),
        AIService(settings),
        EmbeddingService(settings),
    )


@router.get(
    "/messages",
    response_model=MessagesResponse,
    summary="List the user's most recent Gmail messages",
)
async def list_messages(
    credentials: GoogleCredentialsDep,
    user: CurrentUserDep,
    settings: Annotated[Settings, Depends(get_settings)],
    draft_repo: Annotated[DraftRepository, Depends(get_draft_repository)],
    limit: int = Query(default=None, ge=1),
) -> MessagesResponse:
    effective_limit = min(
        limit or settings.default_message_limit,
        settings.max_message_limit,
    )

    service = GmailService(access_token=credentials.access_token)
    messages = await service.list_latest_messages(
        limit=effective_limit,
        draft_repo=draft_repo,
        user_id=user.id,
    )

    return MessagesResponse(count=len(messages), messages=messages)


@router.get(
    "/messages/{message_id}",
    response_model=EmailDetail,
    summary="Get full message detail with thread history",
)
async def get_message(
    message_id: str,
    credentials: GoogleCredentialsDep,
) -> EmailDetail:
    service = GmailService(access_token=credentials.access_token)
    return await service.get_message_detail(message_id)


@router.post(
    "/sync",
    summary="Trigger inbox processing for the current user",
)
async def sync_inbox(
    user: CurrentUserDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, int | str]:
    processor = _build_email_processor(settings)
    count = await processor.process_user_inbox(user.id)
    return {"status": "ok", "processed": count}
