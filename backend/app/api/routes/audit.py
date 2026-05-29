"""Audit log routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserDep, get_audit_repository
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
    subject: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> AuditSearchResponse:
    logs = await audit_repo.search(
        user.id,
        subject=subject,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
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
    )
