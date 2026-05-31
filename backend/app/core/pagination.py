"""Cursor helpers for stable keyset pagination."""

from __future__ import annotations

import base64
import json
from datetime import datetime


def encode_cursor(created_at: datetime, doc_id: str) -> str:
    payload = {"t": created_at.isoformat(), "id": doc_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        payload = json.loads(
            base64.urlsafe_b64decode(cursor.encode()).decode()
        )
        return datetime.fromisoformat(payload["t"]), payload["id"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid pagination cursor.") from exc


def cursor_filter(cursor: str) -> dict:
    """MongoDB filter for descending (created_at, _id) pagination."""
    cursor_date, cursor_id = decode_cursor(cursor)
    return {
        "$or": [
            {"created_at": {"$lt": cursor_date}},
            {"created_at": cursor_date, "_id": {"$lt": cursor_id}},
        ]
    }
