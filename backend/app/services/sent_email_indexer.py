"""Index sent Gmail messages into Pinecone for tone/style retrieval."""

from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.services.embeddings import EmbeddingService
from app.services.gmail import GmailService

logger = logging.getLogger(__name__)


class SentEmailIndexer:
    """Fetch past sent emails and store embeddings in Pinecone."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        settings: Settings | None = None,
    ):
        self._embeddings = embedding_service
        self._settings = settings or get_settings()

    async def index_user_sent_emails(
        self,
        *,
        user_id: str,
        access_token: str,
        limit: int | None = None,
    ) -> dict[str, int]:
        gmail = GmailService(access_token)
        effective_limit = limit or self._settings.max_sent_backfill
        sent_messages = await gmail.list_sent_for_indexing(limit=effective_limit)

        embedded = 0
        skipped = 0

        for message in sent_messages:
            body = (message.body or message.snippet or "").strip()
            if not body:
                skipped += 1
                continue

            vector_id = self._embeddings.upsert_sent_embedding(
                user_id=user_id,
                email_id=message.id,
                thread_id=message.thread_id,
                subject=message.subject,
                body=body,
                to=message.to,
            )
            if vector_id:
                embedded += 1
            else:
                skipped += 1

        logger.info(
            "Indexed sent emails for user %s: embedded=%s skipped=%s total=%s",
            user_id,
            embedded,
            skipped,
            len(sent_messages),
        )
        return {
            "total": len(sent_messages),
            "embedded": embedded,
            "skipped": skipped,
        }
