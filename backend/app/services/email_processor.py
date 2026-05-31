"""Email processing orchestration for background tasks."""

from __future__ import annotations

import logging
from datetime import datetime

from app.repositories.draft import DraftRepository
from app.repositories.email_record import EmailRecordRepository
from app.services.ai import AIService
from app.services.embeddings import EmbeddingService
from app.services.gmail import GmailService
from app.services.user import UserService

logger = logging.getLogger(__name__)


class EmailProcessor:
    """Fetch, filter, and generate drafts for new emails."""

    def __init__(
        self,
        user_service: UserService,
        email_repo: EmailRecordRepository,
        draft_repo: DraftRepository,
        ai_service: AIService,
        embedding_service: EmbeddingService,
    ):
        self._users = user_service
        self._emails = email_repo
        self._drafts = draft_repo
        self._ai = ai_service
        self._embeddings = embedding_service

    async def process_user_inbox(
        self,
        user_id: str,
        *,
        received_after: datetime | None = None,
    ) -> int:
        access_token = await self._users.get_valid_access_token(user_id)
        if not access_token:
            logger.warning("No valid access token for user %s", user_id)
            return 0

        user = await self._users.find_by_id(user_id)
        if user is None:
            return 0

        gmail = GmailService(access_token)
        messages = await gmail.list_relevant_unread(
            limit=50,
            received_after=received_after,
        )
        processed = 0

        for summary in messages:
            if await self._emails.exists(user_id, summary.id):
                continue
            if await self._drafts.find_by_email_id(user_id, summary.id):
                continue

            detail = await gmail.get_message_detail(summary.id)

            await self._emails.create(
                user_id=user_id,
                email_id=summary.id,
                thread_id=summary.thread_id,
                subject=summary.subject,
                from_address=summary.from_,
                snippet=summary.snippet,
                body=detail.body,
            )

            style_context = self._embeddings.get_style_context(
                user_id=user_id,
                subject=summary.subject,
                thread_messages=detail.thread_messages,
            )

            reply_body = self._ai.generate_reply(
                subject=summary.subject,
                thread_messages=detail.thread_messages,
                user_prompt=user.current_prompt,
                writing_style=user.writing_style,
                style_examples=style_context,
            )

            await self._drafts.create(
                user_id=user_id,
                email_id=summary.id,
                thread_id=summary.thread_id,
                generated_body=reply_body,
                generated_subject=summary.subject,
                to=GmailService.reply_recipient(summary.from_),
            )
            processed += 1

        return processed
