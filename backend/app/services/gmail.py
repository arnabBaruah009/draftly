"""Gmail API service.

Wraps the synchronous ``google-api-python-client`` so the rest of the app can
talk to Gmail using a single async-friendly entry point.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any

from fastapi import HTTPException, status
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

from app.models.domain import DraftStatus
from app.repositories.draft import DraftRepository
from app.schemas.email import EmailDetail, EmailSummary, ThreadMessage

logger = logging.getLogger(__name__)

_METADATA_HEADERS = ["Subject", "From", "To", "Date", "Message-ID"]

# Exclude promotional, social, and spam emails from AI processing.
RELEVANT_EMAIL_QUERY = (
    "in:inbox is:unread "
    "-category:promotions -category:social -label:spam"
)

SENT_EMAIL_QUERY = (
    "in:sent -category:promotions -category:social -label:spam"
)


def build_relevant_email_query(*, received_after: datetime | None = None) -> str:
    """Build Gmail search query, optionally scoped to messages after a timestamp.

    Gmail's ``after:`` operator accepts Unix seconds for sub-day precision
    (see https://developers.google.com/workspace/gmail/api/guides/filtering).
    """
    if received_after is None:
        return RELEVANT_EMAIL_QUERY
    after_ts = int(received_after.timestamp())
    return f"{RELEVANT_EMAIL_QUERY} after:{after_ts}"


def _build_gmail_service(access_token: str):
    credentials = Credentials(token=access_token)
    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def _header_value(headers: list[dict[str, str]], name: str) -> str | None:
    target = name.lower()
    for header in headers:
        if header.get("name", "").lower() == target:
            return header.get("value")
    return None


def _parse_datetime(internal_date_ms: str | None) -> datetime | None:
    if internal_date_ms is None:
        return None
    try:
        return datetime.fromtimestamp(
            int(internal_date_ms) / 1000, tz=timezone.utc
        )
    except (TypeError, ValueError):
        return None


def _extract_body(payload: dict[str, Any]) -> str:
    """Extract plain-text body from a Gmail message payload."""
    if not payload:
        return ""

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    parts = payload.get("parts") or []
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode(
                    "utf-8", errors="replace"
                )

    for part in parts:
        nested = _extract_body(part)
        if nested:
            return nested

    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
    return ""


def _is_filtered_label(label_ids: list[str]) -> bool:
    blocked = {
        "CATEGORY_PROMOTIONS",
        "CATEGORY_SOCIAL",
        "SPAM",
        "TRASH",
    }
    return bool(blocked.intersection(set(label_ids)))


def _parse_message(
    message: dict[str, Any],
    *,
    draft_id: str | None = None,
    draft_status: DraftStatus | None = None,
) -> EmailSummary:
    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    label_ids: list[str] = message.get("labelIds", []) or []

    return EmailSummary(
        id=message["id"],
        thread_id=message.get("threadId", ""),
        subject=_header_value(headers, "Subject"),
        **{"from": _header_value(headers, "From")},
        to=_header_value(headers, "To"),
        snippet=message.get("snippet"),
        date=_parse_datetime(message.get("internalDate")),
        label_ids=label_ids,
        is_unread="UNREAD" in label_ids,
        draft_id=draft_id,
        draft_status=draft_status,
    )


def _parse_thread_message(message: dict[str, Any]) -> ThreadMessage:
    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    return ThreadMessage(
        id=message["id"],
        **{"from": _header_value(headers, "From")},
        to=_header_value(headers, "To"),
        subject=_header_value(headers, "Subject"),
        body=_extract_body(payload),
        date=_parse_datetime(message.get("internalDate")),
    )


def _list_and_fetch_messages_sync(
    access_token: str,
    limit: int,
    query: str | None = None,
) -> list[dict[str, Any]]:
    service = _build_gmail_service(access_token)

    list_kwargs: dict[str, Any] = {"userId": "me", "maxResults": limit}
    if query:
        list_kwargs["q"] = query

    list_response = service.users().messages().list(**list_kwargs).execute()
    message_refs = list_response.get("messages", []) or []
    if not message_refs:
        return []

    order = {ref["id"]: index for index, ref in enumerate(message_refs)}
    fetched: dict[str, dict[str, Any]] = {}
    errors: list[HttpError] = []

    def _on_response(
        request_id: str,
        response: dict[str, Any] | None,
        exception: HttpError | None,
    ) -> None:
        if exception is not None:
            errors.append(exception)
            return
        if response is not None:
            fetched[request_id] = response

    batch: BatchHttpRequest = service.new_batch_http_request(
        callback=_on_response
    )
    for ref in message_refs:
        message_id = ref["id"]
        batch.add(
            service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=_METADATA_HEADERS,
            ),
            request_id=message_id,
        )

    batch.execute()

    if errors and not fetched:
        raise errors[0]

    return [
        fetched[message_id]
        for message_id in sorted(fetched, key=lambda mid: order.get(mid, 0))
    ]


def _list_message_ids_paginated_sync(
    access_token: str,
    *,
    query: str,
    max_messages: int,
) -> list[str]:
    service = _build_gmail_service(access_token)
    message_ids: list[str] = []
    page_token: str | None = None

    while len(message_ids) < max_messages:
        page_size = min(500, max_messages - len(message_ids))
        list_kwargs: dict[str, Any] = {
            "userId": "me",
            "maxResults": page_size,
            "q": query,
        }
        if page_token:
            list_kwargs["pageToken"] = page_token

        list_response = service.users().messages().list(**list_kwargs).execute()
        refs = list_response.get("messages", []) or []
        message_ids.extend(ref["id"] for ref in refs)

        page_token = list_response.get("nextPageToken")
        if not page_token or not refs:
            break

    return message_ids[:max_messages]


def _batch_get_messages_full_sync(
    access_token: str,
    message_ids: list[str],
    *,
    batch_size: int = 50,
) -> list[dict[str, Any]]:
    if not message_ids:
        return []

    service = _build_gmail_service(access_token)
    fetched: dict[str, dict[str, Any]] = {}
    errors: list[HttpError] = []

    for offset in range(0, len(message_ids), batch_size):
        chunk = message_ids[offset : offset + batch_size]

        def _on_response(
            request_id: str,
            response: dict[str, Any] | None,
            exception: HttpError | None,
        ) -> None:
            if exception is not None:
                errors.append(exception)
                return
            if response is not None:
                fetched[request_id] = response

        batch: BatchHttpRequest = service.new_batch_http_request(
            callback=_on_response
        )
        for message_id in chunk:
            batch.add(
                service.users().messages().get(
                    userId="me",
                    id=message_id,
                    format="full",
                ),
                request_id=message_id,
            )
        batch.execute()

    if errors and not fetched:
        raise errors[0]

    return [fetched[message_id] for message_id in message_ids if message_id in fetched]


def _get_message_full_sync(access_token: str, message_id: str) -> dict[str, Any]:
    service = _build_gmail_service(access_token)
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


def _get_thread_sync(access_token: str, thread_id: str) -> dict[str, Any]:
    service = _build_gmail_service(access_token)
    return (
        service.users()
        .threads()
        .get(userId="me", id=thread_id, format="full")
        .execute()
    )


def _send_reply_sync(
    access_token: str,
    *,
    thread_id: str,
    to: str,
    subject: str,
    body: str,
    in_reply_to_message_id: str,
) -> dict[str, Any]:
    service = _build_gmail_service(access_token)

    reply_subject = subject
    if not reply_subject.lower().startswith("re:"):
        reply_subject = f"Re: {subject}"

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = reply_subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": raw,
                "threadId": thread_id,
            },
        )
        .execute()
    )


def _extract_email_address(raw: str | None) -> str:
    if not raw:
        return ""
    match = re.search(r"<([^>]+)>", raw)
    if match:
        return match.group(1)
    return raw.strip()


class GmailService:
    """High-level Gmail operations used by the API layer."""

    def __init__(self, access_token: str):
        self._access_token = access_token

    async def _run_sync(self, func, *args, **kwargs):
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except HttpError as exc:
            self._raise_http_error(exc)

    def _raise_http_error(self, exc: HttpError) -> None:
        logger.warning(
            "Gmail API error (status=%s): %s",
            getattr(exc.resp, "status", "?"),
            exc,
        )
        http_status = int(getattr(exc.resp, "status", 0) or 0)
        if http_status == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google rejected the access token.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        if http_status == 403:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access token lacks permission for Gmail.",
            ) from exc
        if http_status == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Gmail API rate limit exceeded.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with Gmail.",
        ) from exc

    async def list_latest_messages(
        self,
        limit: int,
        *,
        draft_repo: DraftRepository | None = None,
        user_id: str | None = None,
    ) -> list[EmailSummary]:
        raw_messages = await self._run_sync(
            _list_and_fetch_messages_sync,
            self._access_token,
            limit,
            None,
        )

        summaries: list[EmailSummary] = []
        for message in raw_messages:
            label_ids = message.get("labelIds", []) or []
            if _is_filtered_label(label_ids):
                continue

            draft_id = None
            draft_status = None
            if draft_repo and user_id:
                draft = await draft_repo.find_by_email_id(
                    user_id, message["id"]
                )
                if draft:
                    draft_id = draft.id
                    draft_status = draft.status

            summaries.append(
                _parse_message(
                    message,
                    draft_id=draft_id,
                    draft_status=draft_status,
                )
            )
        return summaries

    async def list_relevant_unread(
        self,
        limit: int = 20,
        *,
        received_after: datetime | None = None,
    ) -> list[EmailSummary]:
        query = build_relevant_email_query(received_after=received_after)
        raw_messages = await self._run_sync(
            _list_and_fetch_messages_sync,
            self._access_token,
            limit,
            query,
        )
        return [
            _parse_message(msg)
            for msg in raw_messages
            if not _is_filtered_label(msg.get("labelIds", []) or [])
        ]

    async def list_sent_for_indexing(self, limit: int = 500) -> list[EmailDetail]:
        """Fetch sent messages with bodies, ready for vector indexing."""
        message_ids = await self._run_sync(
            _list_message_ids_paginated_sync,
            self._access_token,
            query=SENT_EMAIL_QUERY,
            max_messages=limit,
        )
        raw_messages = await self._run_sync(
            _batch_get_messages_full_sync,
            self._access_token,
            message_ids,
        )

        details: list[EmailDetail] = []
        for message in raw_messages:
            label_ids = message.get("labelIds", []) or []
            if _is_filtered_label(label_ids):
                continue
            if "SENT" not in label_ids:
                continue

            payload = message.get("payload", {}) or {}
            summary = _parse_message(message)
            details.append(
                EmailDetail(
                    **summary.model_dump(by_alias=True),
                    body=_extract_body(payload),
                    thread_messages=[],
                )
            )
        return details

    async def get_message_detail(self, message_id: str) -> EmailDetail:
        message = await self._run_sync(
            _get_message_full_sync, self._access_token, message_id
        )
        thread_id = message.get("threadId", "")
        thread = await self._run_sync(
            _get_thread_sync, self._access_token, thread_id
        )
        thread_messages = [
            _parse_thread_message(msg)
            for msg in thread.get("messages", []) or []
        ]

        payload = message.get("payload", {}) or {}
        summary = _parse_message(message)
        return EmailDetail(
            **summary.model_dump(by_alias=True),
            body=_extract_body(payload),
            thread_messages=thread_messages,
        )

    async def send_reply(
        self,
        *,
        thread_id: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to_message_id: str,
    ) -> dict[str, Any]:
        recipient = _extract_email_address(to)
        return await self._run_sync(
            _send_reply_sync,
            self._access_token,
            thread_id=thread_id,
            to=recipient,
            subject=subject,
            body=body,
            in_reply_to_message_id=in_reply_to_message_id,
        )

    @staticmethod
    def reply_recipient(from_header: str | None) -> str:
        return _extract_email_address(from_header)
