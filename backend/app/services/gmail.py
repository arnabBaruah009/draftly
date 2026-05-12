"""Gmail API service.

Wraps the synchronous ``google-api-python-client`` so the rest of the app can
talk to Gmail using a single async-friendly entry point. Two things to note:

  * The Google client is synchronous; calls are dispatched via
    ``asyncio.to_thread`` so they don't block the event loop.
  * Per-message fetches are issued as a single ``BatchHttpRequest`` rather
    than N sequential GETs - this turns ``list + N gets`` into roughly two
    HTTP round-trips to Google instead of ``N + 1``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

from app.schemas.email import EmailSummary

logger = logging.getLogger(__name__)

# Only the headers we actually need - keeps the response small and fast.
_METADATA_HEADERS = ["Subject", "From", "To", "Date"]


def _build_gmail_service(access_token: str):
    """Build a Gmail v1 service client from a bare access token."""
    credentials = Credentials(token=access_token)
    # cache_discovery=False avoids a noisy warning and stops the client from
    # writing the discovery document to disk on every cold start.
    return build(
        "gmail",
        "v1",
        credentials=credentials,
        cache_discovery=False,
    )


def _header_value(headers: list[dict[str, str]], name: str) -> str | None:
    """Case-insensitive lookup for a single header value."""
    target = name.lower()
    for header in headers:
        if header.get("name", "").lower() == target:
            return header.get("value")
    return None


def _parse_message(message: dict[str, Any]) -> EmailSummary:
    """Convert a Gmail API message resource into our ``EmailSummary``."""
    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []

    internal_date_ms = message.get("internalDate")
    received_at: datetime | None = None
    if internal_date_ms is not None:
        try:
            received_at = datetime.fromtimestamp(
                int(internal_date_ms) / 1000, tz=timezone.utc
            )
        except (TypeError, ValueError):
            received_at = None

    label_ids: list[str] = message.get("labelIds", []) or []

    return EmailSummary(
        id=message["id"],
        thread_id=message.get("threadId", ""),
        subject=_header_value(headers, "Subject"),
        **{"from": _header_value(headers, "From")},
        to=_header_value(headers, "To"),
        snippet=message.get("snippet"),
        date=received_at,
        label_ids=label_ids,
        is_unread="UNREAD" in label_ids,
    )


def _list_and_fetch_messages_sync(
    access_token: str, limit: int
) -> list[EmailSummary]:
    """Synchronous worker: list the latest ``limit`` messages, then batch-fetch
    each one's metadata. Runs inside ``asyncio.to_thread``.
    """
    service = _build_gmail_service(access_token)

    list_response = (
        service.users()
        .messages()
        .list(userId="me", maxResults=limit)
        .execute()
    )
    message_refs = list_response.get("messages", []) or []
    if not message_refs:
        return []

    # Gmail returns refs already sorted newest-first. Preserve that order in
    # the final response by remembering each ID's position.
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
        # Every sub-request failed - surface the first error.
        raise errors[0]

    return [
        _parse_message(fetched[message_id])
        for message_id in sorted(fetched, key=lambda mid: order.get(mid, 0))
    ]


class GmailService:
    """High-level Gmail operations used by the API layer."""

    def __init__(self, access_token: str):
        self._access_token = access_token

    async def list_latest_messages(self, limit: int) -> list[EmailSummary]:
        """Return the ``limit`` most recent messages for the authenticated user.

        Maps Gmail API errors onto sensible HTTP responses for the client.
        """
        try:
            return await asyncio.to_thread(
                _list_and_fetch_messages_sync,
                self._access_token,
                limit,
            )
        except HttpError as exc:
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
                    detail=(
                        "Access token lacks permission to read Gmail "
                        "messages."
                    ),
                ) from exc
            if http_status == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Gmail API rate limit exceeded.",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch messages from Gmail.",
            ) from exc
