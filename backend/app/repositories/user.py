"""User persistence and OAuth token storage."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from pymongo import ReturnDocument

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.redis import get_redis
from app.models.domain import UserDocument

USERS_COLLECTION = "users"
OAUTH_KEY_PREFIX = "oauth:"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_user(doc: dict) -> UserDocument:
    doc["_id"] = str(doc["_id"])
    return UserDocument.model_validate(doc)


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._collection = db[USERS_COLLECTION]

    async def find_by_email(self, email: str) -> UserDocument | None:
        doc = await self._collection.find_one({"email": email.lower()})
        if doc is None:
            return None
        return _serialize_user(doc)

    async def find_by_id(self, user_id: str) -> UserDocument | None:
        doc = await self._collection.find_one({"_id": user_id})
        if doc is None:
            return None
        return _serialize_user(doc)

    async def upsert_from_google(
        self,
        *,
        email: str,
        name: str | None,
        google_sub: str | None,
    ) -> UserDocument:
        now = _utcnow()
        email_lower = email.lower()
        existing = await self._collection.find_one({"email": email_lower})

        if existing is None:
            user_id = google_sub or email_lower
            doc = {
                "_id": user_id,
                "email": email_lower,
                "name": name,
                "google_sub": google_sub,
                "push_token": None,
                "access_token": None,
                "refresh_token": None,
                "current_prompt": (
                    "Reply professionally and concisely. "
                    "Match the tone of the conversation."
                ),
                "writing_style": None,
                "created_at": now,
                "updated_at": now,
            }
            await self._collection.insert_one(doc)
            return _serialize_user(doc)

        updates: dict = {"updated_at": now}
        if name and name != existing.get("name"):
            updates["name"] = name
        if google_sub and google_sub != existing.get("google_sub"):
            updates["google_sub"] = google_sub

        if len(updates) > 1:
            await self._collection.update_one(
                {"_id": existing["_id"]}, {"$set": updates}
            )
            existing.update(updates)

        return _serialize_user(existing)

    async def update_preferences(
        self,
        user_id: str,
        *,
        current_prompt: str | None = None,
        writing_style: str | None = None,
    ) -> UserDocument | None:
        updates: dict = {"updated_at": _utcnow()}
        if current_prompt is not None:
            updates["current_prompt"] = current_prompt
        if writing_style is not None:
            updates["writing_style"] = writing_style

        result = await self._collection.find_one_and_update(
            {"_id": user_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            return None
        return _serialize_user(result)

    async def update_tokens(
        self,
        user_id: str,
        *,
        access_token: str,
        refresh_token: str | None = None,
    ) -> UserDocument | None:
        updates: dict = {
            "access_token": access_token,
            "updated_at": _utcnow(),
        }
        if refresh_token is not None:
            updates["refresh_token"] = refresh_token

        result = await self._collection.find_one_and_update(
            {"_id": user_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            return None
        return _serialize_user(result)

    async def clear_tokens(self, user_id: str) -> None:
        await self._collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "access_token": None,
                    "refresh_token": None,
                    "updated_at": _utcnow(),
                }
            },
        )

    async def list_all(self) -> list[UserDocument]:
        cursor = self._collection.find({})
        return [_serialize_user(doc) async for doc in cursor]


class TokenStore:
    """Store OAuth tokens in Redis keyed by user ID."""

    @staticmethod
    def _key(user_id: str) -> str:
        return f"{OAUTH_KEY_PREFIX}{user_id}"

    async def save_tokens(
        self,
        user_id: str,
        *,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None = None,
    ) -> None:
        redis_client = await get_redis()
        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
        }
        ttl = expires_in or 3600
        await redis_client.setex(
            self._key(user_id),
            max(ttl, 300),
            json.dumps(payload),
        )

    async def get_tokens(self, user_id: str) -> dict | None:
        redis_client = await get_redis()
        raw = await redis_client.get(self._key(user_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def delete_tokens(self, user_id: str) -> None:
        redis_client = await get_redis()
        await redis_client.delete(self._key(user_id))
