"""Processed email metadata persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.domain import EmailRecordDocument

EMAILS_COLLECTION = "email_records"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_email(doc: dict) -> EmailRecordDocument:
    doc["_id"] = str(doc["_id"])
    return EmailRecordDocument.model_validate(doc)


class EmailRecordRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db[EMAILS_COLLECTION]

    async def exists(self, user_id: str, email_id: str) -> bool:
        doc = await self._collection.find_one(
            {"user_id": user_id, "email_id": email_id}
        )
        return doc is not None

    async def create(
        self,
        *,
        user_id: str,
        email_id: str,
        thread_id: str,
        subject: str | None,
        from_address: str | None,
        snippet: str | None,
        body: str | None,
    ) -> EmailRecordDocument:
        now = _utcnow()
        doc = {
            "_id": str(uuid4()),
            "user_id": user_id,
            "email_id": email_id,
            "thread_id": thread_id,
            "subject": subject,
            "from_address": from_address,
            "snippet": snippet,
            "body": body,
            "created_at": now,
        }
        await self._collection.insert_one(doc)
        return _serialize_email(doc)

    async def find_by_email_id(
        self, user_id: str, email_id: str
    ) -> EmailRecordDocument | None:
        doc = await self._collection.find_one(
            {"user_id": user_id, "email_id": email_id}
        )
        if doc is None:
            return None
        return _serialize_email(doc)
