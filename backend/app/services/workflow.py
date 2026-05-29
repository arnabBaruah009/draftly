"""Approval workflow for AI-generated drafts."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.models.domain import AuditAction, DraftStatus, UserDocument
from app.repositories.audit import AuditRepository
from app.repositories.draft import DraftRepository
from app.schemas.email import DraftResponse, EditDraftRequest
from app.services.ai import AIService
from app.services.gmail import GmailService
from app.services.user import UserService


class WorkflowService:
    def __init__(
        self,
        draft_repo: DraftRepository,
        audit_repo: AuditRepository,
        user_service: UserService,
        ai_service: AIService,
    ):
        self._drafts = draft_repo
        self._audit = audit_repo
        self._users = user_service
        self._ai = ai_service

    async def get_draft(
        self, draft_id: str, user_id: str
    ) -> DraftResponse:
        draft = await self._drafts.find_by_id(draft_id, user_id)
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )
        return self._to_response(draft)

    async def list_drafts(
        self,
        user_id: str,
        *,
        status_filter: DraftStatus | None = None,
        limit: int = 50,
    ) -> list[DraftResponse]:
        drafts = await self._drafts.list_for_user(
            user_id, status=status_filter, limit=limit
        )
        return [self._to_response(d) for d in drafts]

    async def edit_draft(
        self,
        draft_id: str,
        user: UserDocument,
        payload: EditDraftRequest,
    ) -> DraftResponse:
        draft = await self._drafts.find_by_id(draft_id, user.id)
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )

        updated = await self._drafts.update_status(
            draft_id,
            user.id,
            draft.status,
            generated_body=payload.generated_body,
            generated_subject=payload.generated_subject,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )

        await self._audit.create(
            user_id=user.id,
            action=AuditAction.EDITED,
            draft_id=draft_id,
            email_id=draft.email_id,
            subject=updated.generated_subject,
            body_snapshot=payload.generated_body,
        )
        return self._to_response(updated)

    async def reject_draft(
        self, draft_id: str, user: UserDocument
    ) -> DraftResponse:
        draft = await self._drafts.find_by_id(draft_id, user.id)
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )

        updated = await self._drafts.update_status(
            draft_id, user.id, DraftStatus.REJECTED
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )

        await self._audit.create(
            user_id=user.id,
            action=AuditAction.REJECTED,
            draft_id=draft_id,
            email_id=draft.email_id,
            subject=draft.generated_subject,
            body_snapshot=draft.generated_body,
        )
        return self._to_response(updated)

    async def approve_and_send(
        self,
        draft_id: str,
        user: UserDocument,
        access_token: str,
    ) -> DraftResponse:
        draft = await self._drafts.find_by_id(draft_id, user.id)
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )

        if draft.status == DraftStatus.SENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Draft has already been sent.",
            )

        gmail = GmailService(access_token)
        await gmail.send_reply(
            thread_id=draft.thread_id,
            to=draft.to or "",
            subject=draft.generated_subject or "Re:",
            body=draft.generated_body,
            in_reply_to_message_id=draft.email_id,
        )

        await self._drafts.update_status(
            draft_id, user.id, DraftStatus.APPROVED
        )
        sent = await self._drafts.mark_sent(draft_id, user.id)
        if sent is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update draft status.",
            )

        await self._audit.create(
            user_id=user.id,
            action=AuditAction.APPROVED,
            draft_id=draft_id,
            email_id=draft.email_id,
            subject=draft.generated_subject,
            body_snapshot=draft.generated_body,
        )
        await self._audit.create(
            user_id=user.id,
            action=AuditAction.SENT,
            draft_id=draft_id,
            email_id=draft.email_id,
            subject=draft.generated_subject,
            body_snapshot=draft.generated_body,
        )
        return self._to_response(sent)

    async def regenerate(
        self,
        draft_id: str,
        user: UserDocument,
        access_token: str,
    ) -> DraftResponse:
        draft = await self._drafts.find_by_id(draft_id, user.id)
        if draft is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )

        gmail = GmailService(access_token)
        detail = await gmail.get_message_detail(draft.email_id)

        body = await self._ai.generate_reply(
            subject=detail.subject,
            thread_messages=detail.thread_messages,
            user_prompt=user.current_prompt,
            writing_style=user.writing_style,
        )

        updated = await self._drafts.update_status(
            draft_id,
            user.id,
            DraftStatus.PENDING,
            generated_body=body,
            generated_subject=detail.subject,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found.",
            )

        await self._audit.create(
            user_id=user.id,
            action=AuditAction.REGENERATED,
            draft_id=draft_id,
            email_id=draft.email_id,
            subject=updated.generated_subject,
            body_snapshot=body,
        )
        return self._to_response(updated)

    @staticmethod
    def _to_response(draft) -> DraftResponse:
        return DraftResponse(
            id=draft.id,
            user_id=draft.user_id,
            email_id=draft.email_id,
            thread_id=draft.thread_id,
            generated_body=draft.generated_body,
            generated_subject=draft.generated_subject,
            to=draft.to,
            status=draft.status,
            approved_at=draft.approved_at,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )
