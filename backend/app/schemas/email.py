from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EmailSummary(BaseModel):
    """Lightweight representation of a Gmail message.

    Only the fields needed to render an inbox list. Heavier fields like the
    full body are intentionally omitted to keep the payload small; a separate
    endpoint can be added later to fetch a single message's full content.
    """

    id: str = Field(..., description="Gmail message ID")
    thread_id: str = Field(..., description="Gmail thread ID")
    subject: str | None = Field(None, description="Message subject")
    from_: str | None = Field(
        None,
        alias="from",
        description="Sender (as returned in the 'From' header)",
    )
    to: str | None = Field(None, description="Recipient (the 'To' header)")
    snippet: str | None = Field(
        None, description="Short preview of the message body"
    )
    date: datetime | None = Field(
        None, description="Internal date the message was received"
    )
    label_ids: list[str] = Field(
        default_factory=list,
        description="Gmail label IDs attached to the message",
    )
    is_unread: bool = Field(
        False, description="True when the UNREAD label is set"
    )

    model_config = {"populate_by_name": True}


class MessagesResponse(BaseModel):
    """Response payload for the messages list endpoint."""

    count: int = Field(..., description="Number of messages returned")
    messages: list[EmailSummary]


class TokenInfo(BaseModel):
    """Subset of fields returned by Google's tokeninfo endpoint."""

    email: str | None = None
    scope: str | None = None
    expires_in: int | None = Field(None, alias="expires_in")
    audience: str | None = None
    user_id: str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}
