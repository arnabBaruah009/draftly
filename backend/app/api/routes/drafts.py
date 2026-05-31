"""Draft approval workflow routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserDep, get_draft_repository, get_workflow_service
from app.auth.google import GoogleCredentialsDep
from app.core.config import Settings, get_settings
from app.models.domain import DraftStatus
from app.repositories.draft import DraftRepository
from app.schemas.email import (
    DraftCountResponse,
    DraftListResponse,
    DraftResponse,
    EditDraftRequest,
)
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/drafts", tags=["drafts"])


@router.get(
    "",
    response_model=DraftListResponse,
    summary="List AI-generated draft replies",
)
async def list_drafts(
    user: CurrentUserDep,
    workflow: Annotated[WorkflowService, Depends(get_workflow_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    status_filter: DraftStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=None, ge=1),
    cursor: str | None = Query(default=None),
) -> DraftListResponse:
    effective_limit = min(
        limit or settings.default_page_size,
        settings.max_page_size,
    )
    drafts, next_cursor, has_more = await workflow.list_drafts(
        user.id,
        status_filter=status_filter,
        limit=effective_limit,
        cursor=cursor,
    )
    return DraftListResponse(
        count=len(drafts),
        drafts=drafts,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get(
    "/count",
    response_model=DraftCountResponse,
    summary="Count drafts for the current user",
)
async def count_drafts(
    user: CurrentUserDep,
    draft_repo: Annotated[DraftRepository, Depends(get_draft_repository)],
    status_filter: DraftStatus | None = Query(default=None, alias="status"),
) -> DraftCountResponse:
    count = await draft_repo.count_for_user(
        user.id, status=status_filter
    )
    return DraftCountResponse(count=count)


@router.get(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Get a single draft",
)
async def get_draft(
    draft_id: str,
    user: CurrentUserDep,
    workflow: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> DraftResponse:
    return await workflow.get_draft(draft_id, user.id)


@router.put(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Edit a draft before sending",
)
async def edit_draft(
    draft_id: str,
    payload: EditDraftRequest,
    user: CurrentUserDep,
    workflow: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> DraftResponse:
    return await workflow.edit_draft(draft_id, user, payload)


@router.post(
    "/{draft_id}/approve",
    response_model=DraftResponse,
    summary="Approve and send the draft via Gmail",
)
async def approve_draft(
    draft_id: str,
    user: CurrentUserDep,
    credentials: GoogleCredentialsDep,
    workflow: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> DraftResponse:
    return await workflow.approve_and_send(
        draft_id, user, credentials.access_token
    )


@router.post(
    "/{draft_id}/reject",
    response_model=DraftResponse,
    summary="Reject the generated draft",
)
async def reject_draft(
    draft_id: str,
    user: CurrentUserDep,
    workflow: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> DraftResponse:
    return await workflow.reject_draft(draft_id, user)


@router.post(
    "/{draft_id}/regenerate",
    response_model=DraftResponse,
    summary="Regenerate a new AI reply for a rejected draft",
)
async def regenerate_draft(
    draft_id: str,
    user: CurrentUserDep,
    credentials: GoogleCredentialsDep,
    workflow: Annotated[WorkflowService, Depends(get_workflow_service)],
) -> DraftResponse:
    return await workflow.regenerate(
        draft_id, user, credentials.access_token
    )
