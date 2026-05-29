"""Background tasks for monitoring Gmail inboxes."""

from __future__ import annotations

import asyncio
import logging

from app.core.config import get_settings
from app.core.database import get_database
from app.repositories.draft import DraftRepository
from app.repositories.email_record import EmailRecordRepository
from app.repositories.user import TokenStore, UserRepository
from app.services.ai import AIService
from app.services.email_processor import EmailProcessor
from app.services.embeddings import EmbeddingService
from app.services.user import UserService
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    return asyncio.run(coro)


def _build_processor() -> EmailProcessor:
    settings = get_settings()
    db = get_database()
    return EmailProcessor(
        UserService(UserRepository(db), TokenStore(), settings),
        EmailRecordRepository(db),
        DraftRepository(db),
        AIService(settings),
        EmbeddingService(settings),
    )


@celery_app.task(name="app.tasks.email_monitor.process_user_inbox")
def process_user_inbox(user_id: str) -> int:
    processor = _build_processor()
    return _run_async(processor.process_user_inbox(user_id))


@celery_app.task(name="app.tasks.email_monitor.poll_all_user_inboxes")
def poll_all_user_inboxes() -> dict[str, int]:
    async def _poll() -> dict[str, int]:
        db = get_database()
        user_repo = UserRepository(db)
        users = await user_repo.list_all()
        total = 0
        for user in users:
            try:
                count = await _build_processor().process_user_inbox(user.id)
                total += count
            except Exception:
                logger.exception("Failed to process inbox for user %s", user.id)
        return {"users": len(users), "processed": total}

    return _run_async(_poll())
