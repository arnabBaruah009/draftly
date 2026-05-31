"""Background tasks for monitoring Gmail inboxes."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

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
    """Run async code in a Celery worker without leaking closed event loops.

    Motor and redis-py bind to the active asyncio loop. Celery tasks call
    ``asyncio.run`` per invocation, so module-level clients must be reset
    after each run or the next task hits ``RuntimeError: Event loop is closed``.
    """
    from app.core.database import close_database
    from app.core.redis import close_redis

    async def _wrapper():
        try:
            return await coro
        finally:
            await close_database()
            await close_redis()

    return asyncio.run(_wrapper())


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
def process_user_inbox(
    user_id: str,
    received_after_epoch: int | None = None,
) -> int:
    received_after = None
    if received_after_epoch is not None:
        received_after = datetime.fromtimestamp(
            received_after_epoch,
            tz=timezone.utc,
        )
    async def _process() -> int:
        processor = _build_processor()
        return await processor.process_user_inbox(
            user_id,
            received_after=received_after,
        )

    return _run_async(_process())


@celery_app.task(name="app.tasks.email_monitor.poll_all_user_inboxes")
def poll_all_user_inboxes() -> dict[str, int]:
    settings = get_settings()
    received_after = datetime.now(timezone.utc) - timedelta(
        seconds=settings.email_sync_lookback_seconds,
    )
    received_after_epoch = int(received_after.timestamp())

    async def _poll() -> dict[str, int]:
        db = get_database()
        user_repo = UserRepository(db)
        users = await user_repo.list_all()
        for user in users:
            process_user_inbox.delay(user.id, received_after_epoch)
        return {"users": len(users), "dispatched": len(users)}

    return _run_async(_poll())
