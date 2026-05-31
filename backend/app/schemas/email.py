"""Pydantic schemas for API request/response payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.domain import AuditAction, DraftStatus


class EmailSummary(BaseModel):
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
    draft_id: str | None = Field(
        None, description="Associated AI draft ID if one exists"
    )
    draft_status: DraftStatus | None = Field(
        None, description="Status of the associated draft"
    )

    model_config = {"populate_by_name": True}


class EmailDetail(EmailSummary):
    body: str | None = None
    thread_messages: list["ThreadMessage"] = Field(default_factory=list)


class ThreadMessage(BaseModel):
    id: str
    from_: str | None = Field(None, alias="from")
    to: str | None = None
    subject: str | None = None
    body: str | None = None
    date: datetime | None = None

    model_config = {"populate_by_name": True}


class MessagesResponse(BaseModel):
    count: int = Field(..., description="Number of messages returned")
    messages: list[EmailSummary]
    next_page_token: str | None = Field(
        None, description="Gmail page token for the next page"
    )
    has_more: bool = Field(
        False, description="True when more messages can be loaded"
    )


class TokenInfo(BaseModel):
    email: str | None = None
    scope: str | None = None
    expires_in: int | None = Field(None, alias="expires_in")
    audience: str | None = None
    user_id: str | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class UserSyncRequest(BaseModel):
    refresh_token: str | None = None
    name: str | None = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    current_prompt: str
    writing_style: str | None = None
    created_at: datetime
    updated_at: datetime


class UpdatePromptRequest(BaseModel):
    current_prompt: str = Field(..., min_length=1, max_length=4000)
    writing_style: str | None = Field(None, max_length=2000)


class DraftResponse(BaseModel):
    id: str
    user_id: str
    email_id: str
    thread_id: str
    generated_body: str
    generated_subject: str | None = None
    to: str | None = None
    status: DraftStatus
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DraftListResponse(BaseModel):
    count: int
    drafts: list[DraftResponse]
    next_cursor: str | None = None
    has_more: bool = False


class DraftCountResponse(BaseModel):
    count: int


class EditDraftRequest(BaseModel):
    generated_body: str = Field(..., min_length=1)
    generated_subject: str | None = None


class AuditLogResponse(BaseModel):
    id: str
    user_id: str
    draft_id: str | None = None
    email_id: str | None = None
    action: AuditAction
    subject: str | None = None
    body_snapshot: str | None = None
    created_at: datetime


class AuditSearchResponse(BaseModel):
    count: int
    logs: list[AuditLogResponse]
    next_cursor: str | None = None
    has_more: bool = False
