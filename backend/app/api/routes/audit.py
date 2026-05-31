"""Audit log routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserDep, get_audit_repository
from app.core.config import Settings, get_settings
from app.repositories.audit import AuditRepository
from app.schemas.email import AuditLogResponse, AuditSearchResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    response_model=AuditSearchResponse,
    summary="Search audit logs by date and subject",
)
async def search_audit_logs(
    user: CurrentUserDep,
    audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    subject: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=None, ge=1),
    cursor: str | None = Query(default=None),
) -> AuditSearchResponse:
    effective_limit = min(
        limit or settings.default_page_size,
        settings.max_page_size,
    )
    logs, next_cursor, has_more = await audit_repo.search(
        user.id,
        subject=subject,
        start_date=start_date,
        end_date=end_date,
        limit=effective_limit,
        cursor=cursor,
    )
    return AuditSearchResponse(
        count=len(logs),
        logs=[
            AuditLogResponse(
                id=log.id,
                user_id=log.user_id,
                draft_id=log.draft_id,
                email_id=log.email_id,
                action=log.action,
                subject=log.subject,
                body_snapshot=log.body_snapshot,
                created_at=log.created_at,
            )
            for log in logs
        ],
        next_cursor=next_cursor,
        has_more=has_more,
    )
