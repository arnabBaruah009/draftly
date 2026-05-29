"""Domain models for MongoDB documents."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DraftStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class AuditAction(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    SENT = "sent"
    REGENERATED = "regenerated"


class UserDocument(BaseModel):
    id: str = Field(alias="_id")
    email: str
    name: str | None = None
    google_sub: str | None = None
    push_token: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    current_prompt: str = (
        "Reply professionally and concisely. Match the tone of the conversation."
    )
    writing_style: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class DraftDocument(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    email_id: str
    thread_id: str
    generated_body: str
    generated_subject: str | None = None
    to: str | None = None
    status: DraftStatus = DraftStatus.PENDING
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class AuditLogDocument(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    draft_id: str | None = None
    email_id: str | None = None
    action: AuditAction
    subject: str | None = None
    body_snapshot: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"populate_by_name": True}


class EmailRecordDocument(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    email_id: str
    thread_id: str
    subject: str | None = None
    from_address: str | None = None
    snippet: str | None = None
    body: str | None = None
    created_at: datetime

    model_config = {"populate_by_name": True}
