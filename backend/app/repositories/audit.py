"""Audit log persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.pagination import cursor_filter, encode_cursor
from app.models.domain import AuditAction, AuditLogDocument

AUDIT_COLLECTION = "audit_logs"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_log(doc: dict) -> AuditLogDocument:
    doc["_id"] = str(doc["_id"])
    return AuditLogDocument.model_validate(doc)


class AuditRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db[AUDIT_COLLECTION]

    async def create(
        self,
        *,
        user_id: str,
        action: AuditAction,
        draft_id: str | None = None,
        email_id: str | None = None,
        subject: str | None = None,
        body_snapshot: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLogDocument:
        now = _utcnow()
        doc = {
            "_id": str(uuid4()),
            "user_id": user_id,
            "draft_id": draft_id,
            "email_id": email_id,
            "action": action.value,
            "subject": subject,
            "body_snapshot": body_snapshot,
            "metadata": metadata or {},
            "created_at": now,
        }
        await self._collection.insert_one(doc)
        return _serialize_log(doc)

    async def search(
        self,
        user_id: str,
        *,
        subject: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 25,
        cursor: str | None = None,
    ) -> tuple[list[AuditLogDocument], str | None, bool]:
        query: dict = {"user_id": user_id}
        if subject:
            query["subject"] = {"$regex": subject, "$options": "i"}
        if start_date or end_date:
            date_filter: dict = {}
            if start_date:
                date_filter["$gte"] = start_date
            if end_date:
                date_filter["$lte"] = end_date
            query["created_at"] = date_filter
        if cursor:
            query.update(cursor_filter(cursor))

        fetch_limit = limit + 1
        db_cursor = (
            self._collection.find(query)
            .sort([("created_at", -1), ("_id", -1)])
            .limit(fetch_limit)
        )
        docs = [_serialize_log(doc) async for doc in db_cursor]

        has_more = len(docs) > limit
        if has_more:
            docs = docs[:limit]

        next_cursor = None
        if has_more and docs:
            last = docs[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return docs, next_cursor, has_more
