"""FastAPI dependencies for repositories and services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.google import GoogleCredentials, GoogleCredentialsDep
from app.core.config import Settings, get_settings
from app.core.database import get_database
from app.models.domain import UserDocument
from app.repositories.audit import AuditRepository
from app.repositories.draft import DraftRepository
from app.repositories.email_record import EmailRecordRepository
from app.repositories.user import TokenStore, UserRepository
from app.services.ai import AIService
from app.services.user import UserService
from app.services.workflow import WorkflowService


def get_user_repository() -> UserRepository:
    return UserRepository(get_database())


def get_token_store() -> TokenStore:
    return TokenStore()


def get_draft_repository() -> DraftRepository:
    return DraftRepository(get_database())


def get_audit_repository() -> AuditRepository:
    return AuditRepository(get_database())


def get_user_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserService:
    return UserService(
        UserRepository(get_database()),
        TokenStore(),
        settings,
    )


def get_ai_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AIService:
    return AIService(settings)


def get_workflow_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkflowService:
    return WorkflowService(
        DraftRepository(get_database()),
        AuditRepository(get_database()),
        UserService(
            UserRepository(get_database()),
            TokenStore(),
            settings,
        ),
        AIService(settings),
    )


async def get_current_user(
    credentials: GoogleCredentialsDep,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserDocument:
    return await user_service.get_user_from_credentials(credentials)


CurrentUserDep = Annotated[UserDocument, Depends(get_current_user)]
