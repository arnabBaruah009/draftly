"""Draft approval workflow routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserDep, get_workflow_service
from app.auth.google import GoogleCredentialsDep
from app.models.domain import DraftStatus
from app.schemas.email import (
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
    status_filter: DraftStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
) -> DraftListResponse:
    drafts = await workflow.list_drafts(
        user.id, status_filter=status_filter, limit=limit
    )
    return DraftListResponse(count=len(drafts), drafts=drafts)


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
