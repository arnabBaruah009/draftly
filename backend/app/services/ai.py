"""LLM-powered email reply generation via OpenRouter."""

from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.schemas.email import ThreadMessage
from app.services.openrouter import get_openrouter_client

logger = logging.getLogger(__name__)


class AIService:
    """Generate contextual email replies using OpenRouter."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._client = get_openrouter_client()

    def _format_thread(self, messages: list[ThreadMessage]) -> str:
        parts: list[str] = []
        for msg in messages:
            header = f"From: {msg.from_ or 'Unknown'}"
            if msg.date:
                header += f" ({msg.date.isoformat()})"
            parts.append(f"{header}\n{msg.body or msg.subject or ''}")
        return "\n\n---\n\n".join(parts)

    def _build_system_prompt(
        self, user_prompt: str, writing_style: str | None
    ) -> str:
        style = writing_style or "Professional, clear, and friendly."
        return (
            "You are an AI email assistant. Generate a reply draft for the user.\n"
            f"User instructions: {user_prompt}\n"
            f"Writing style: {style}\n"
            "Return only the email body text. Do not include subject lines "
            "or meta commentary."
        )

    def generate_reply(
        self,
        *,
        subject: str | None,
        thread_messages: list[ThreadMessage],
        user_prompt: str,
        writing_style: str | None = None,
    ) -> str:
        system = self._build_system_prompt(user_prompt, writing_style)
        thread_text = self._format_thread(thread_messages)
        user_content = (
            f"Subject: {subject or '(no subject)'}\n\n"
            f"Conversation thread:\n{thread_text}\n\n"
            "Write a reply to the most recent message."
        )

        if not self._settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add your OpenRouter API key to .env."
            )

        response = self._client.chat.completions.create(
            model=self._settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
        )
        return (response.choices[0].message.content or "").strip()
