"""Pinecone vector store for email embeddings."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_pinecone_client: Pinecone | None = None
_index = None


def _embedding_id(user_id: str, email_id: str) -> str:
    raw = f"{user_id}:{email_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


class EmbeddingService:
    """Generate embeddings and store them in Pinecone."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._openai = OpenAI(api_key=self._settings.openai_api_key)

    def _ensure_index(self):
        global _pinecone_client, _index
        if not self._settings.pinecone_api_key:
            logger.warning("Pinecone API key not configured; skipping embeddings")
            return None

        if _index is not None:
            return _index

        _pinecone_client = Pinecone(api_key=self._settings.pinecone_api_key)
        index_name = self._settings.pinecone_index

        existing = {idx.name for idx in _pinecone_client.list_indexes()}
        if index_name not in existing:
            _pinecone_client.create_index(
                name=index_name,
                dimension=1536,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=self._settings.pinecone_cloud,
                    region=self._settings.pinecone_region,
                ),
            )

        _index = _pinecone_client.Index(index_name)
        return _index

    def embed_text(self, text: str) -> list[float]:
        response = self._openai.embeddings.create(
            model=self._settings.openai_embedding_model,
            input=text[:8000],
        )
        return response.data[0].embedding

    def upsert_email_embedding(
        self,
        *,
        user_id: str,
        email_id: str,
        thread_id: str,
        subject: str | None,
        body: str,
    ) -> str | None:
        index = self._ensure_index()
        if index is None:
            return None

        content = f"Subject: {subject or ''}\n\n{body}"
        vector = self.embed_text(content)
        vector_id = _embedding_id(user_id, email_id)

        index.upsert(
            vectors=[
                {
                    "id": vector_id,
                    "values": vector,
                    "metadata": {
                        "userId": user_id,
                        "emailId": email_id,
                        "threadId": thread_id,
                        "subject": subject or "",
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                    },
                }
            ]
        )
        return vector_id

    def search_similar(
        self,
        *,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        index = self._ensure_index()
        if index is None:
            return []

        vector = self.embed_text(query)
        results = index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter={"userId": {"$eq": user_id}},
        )
        return [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata or {},
            }
            for match in results.matches
        ]
