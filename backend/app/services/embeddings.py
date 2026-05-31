"""Pinecone vector store for sent-email embeddings via OpenRouter."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from pinecone import Pinecone, ServerlessSpec

from app.core.config import Settings, get_settings
from app.schemas.email import ThreadMessage
from app.services.openrouter import get_openrouter_client

logger = logging.getLogger(__name__)

_pinecone_client: Pinecone | None = None
_index = None

SENT_KIND = "sent"
_METADATA_BODY_MAX_CHARS = 2000


def _embedding_id(user_id: str, email_id: str) -> str:
    raw = f"{user_id}:{email_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


class EmbeddingService:
    """Generate embeddings through OpenRouter and store sent emails in Pinecone."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._client = get_openrouter_client()

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
                dimension=self._settings.openai_embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=self._settings.pinecone_cloud,
                    region=self._settings.pinecone_region,
                ),
            )

        _index = _pinecone_client.Index(index_name)
        return _index

    def embed_text(self, text: str) -> list[float]:
        if not self._settings.openai_api_key:
            logger.warning("OpenRouter API key not configured; skipping embedding")
            return []

        response = self._client.embeddings.create(
            model=self._settings.openai_embedding_model,
            input=text[:8000],
            dimensions=self._settings.openai_embedding_dimension,
        )
        vector = response.data[0].embedding
        expected = self._settings.openai_embedding_dimension
        if len(vector) != expected:
            logger.error(
                "Embedding dimension mismatch: got %s, expected %s",
                len(vector),
                expected,
            )
            return []
        return vector

    def upsert_sent_embedding(
        self,
        *,
        user_id: str,
        email_id: str,
        thread_id: str,
        subject: str | None,
        body: str,
        to: str | None = None,
    ) -> str | None:
        """Store a sent email embedding for tone/style retrieval."""
        index = self._ensure_index()
        if index is None:
            return None

        content = f"Subject: {subject or ''}\n\n{body}"
        vector = self.embed_text(content)
        if not vector:
            return None

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
                        "subject": (subject or "")[:500],
                        "body": body[:_METADATA_BODY_MAX_CHARS],
                        "to": (to or "")[:500],
                        "kind": SENT_KIND,
                        "createdAt": datetime.now(timezone.utc).isoformat(),
                    },
                }
            ]
        )
        return vector_id

    def search_similar_sent(
        self,
        *,
        user_id: str,
        query: str,
        top_k: int | None = None,
    ) -> list[dict]:
        index = self._ensure_index()
        if index is None:
            return []

        vector = self.embed_text(query)
        if not vector:
            return []

        effective_top_k = top_k or self._settings.style_context_top_k
        results = index.query(
            vector=vector,
            top_k=effective_top_k,
            include_metadata=True,
            filter={
                "userId": {"$eq": user_id},
                "kind": {"$eq": SENT_KIND},
            },
        )
        return [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata or {},
            }
            for match in results.matches
        ]

    def get_style_context(
        self,
        *,
        user_id: str,
        subject: str | None,
        thread_messages: list[ThreadMessage],
        top_k: int | None = None,
    ) -> list[dict]:
        """Retrieve relevant past sent emails to inform reply tone and style."""
        latest = thread_messages[-1] if thread_messages else None
        query_parts = [
            subject or "",
            latest.body if latest else "",
            latest.subject if latest else "",
        ]
        query = "\n".join(part.strip() for part in query_parts if part and part.strip())
        if not query:
            return []

        return self.search_similar_sent(
            user_id=user_id,
            query=query,
            top_k=top_k,
        )
