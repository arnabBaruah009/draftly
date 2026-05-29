"""Draft email persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pymongo import ReturnDocument
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import DraftDocument, DraftStatus

DRAFTS_COLLECTION = "draft_emails"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_draft(doc: dict) -> DraftDocument:
    doc["_id"] = str(doc["_id"])
    return DraftDocument.model_validate(doc)


class DraftRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db[DRAFTS_COLLECTION]

    async def create(
        self,
        *,
        user_id: str,
        email_id: str,
        thread_id: str,
        generated_body: str,
        generated_subject: str | None,
        to: str | None,
    ) -> DraftDocument:
        now = _utcnow()
        doc = {
            "_id": str(uuid4()),
            "user_id": user_id,
            "email_id": email_id,
            "thread_id": thread_id,
            "generated_body": generated_body,
            "generated_subject": generated_subject,
            "to": to,
            "status": DraftStatus.PENDING.value,
            "approved_at": None,
            "created_at": now,
            "updated_at": now,
        }
        await self._collection.insert_one(doc)
        return _serialize_draft(doc)

    async def find_by_id(
        self, draft_id: str, user_id: str | None = None
    ) -> DraftDocument | None:
        query: dict = {"_id": draft_id}
        if user_id is not None:
            query["user_id"] = user_id
        doc = await self._collection.find_one(query)
        if doc is None:
            return None
        return _serialize_draft(doc)

    async def find_by_email_id(
        self, user_id: str, email_id: str
    ) -> DraftDocument | None:
        doc = await self._collection.find_one(
            {"user_id": user_id, "email_id": email_id}
        )
        if doc is None:
            return None
        return _serialize_draft(doc)

    async def list_for_user(
        self,
        user_id: str,
        *,
        status: DraftStatus | None = None,
        limit: int = 50,
    ) -> list[DraftDocument]:
        query: dict = {"user_id": user_id}
        if status is not None:
            query["status"] = status.value
        cursor = (
            self._collection.find(query)
            .sort("created_at", -1)
            .limit(limit)
        )
        return [_serialize_draft(doc) async for doc in cursor]

    async def update_status(
        self,
        draft_id: str,
        user_id: str,
        status: DraftStatus,
        *,
        generated_body: str | None = None,
        generated_subject: str | None = None,
    ) -> DraftDocument | None:
        updates: dict = {
            "status": status.value,
            "updated_at": _utcnow(),
        }
        if generated_body is not None:
            updates["generated_body"] = generated_body
        if generated_subject is not None:
            updates["generated_subject"] = generated_subject
        if status == DraftStatus.APPROVED:
            updates["approved_at"] = _utcnow()

        result = await self._collection.find_one_and_update(
            {"_id": draft_id, "user_id": user_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            return None
        return _serialize_draft(result)

    async def mark_sent(self, draft_id: str, user_id: str) -> DraftDocument | None:
        return await self.update_status(
            draft_id, user_id, DraftStatus.SENT
        )
