"""LLM-powered email reply generation."""

from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.schemas.email import ThreadMessage

logger = logging.getLogger(__name__)


class AIService:
    """Generate contextual email replies using configured LLM provider."""

    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

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

        provider = self._settings.llm_provider.lower()
        if provider == "anthropic":
            return self._generate_anthropic(system, user_content)
        if provider == "gemini":
            return self._generate_gemini(system, user_content)
        return self._generate_openai(system, user_content)

    def _generate_openai(self, system: str, user_content: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._settings.openai_api_key)
        response = client.chat.completions.create(
            model=self._settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
        )
        return (response.choices[0].message.content or "").strip()

    def _generate_anthropic(self, system: str, user_content: str) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)
        response = client.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        parts = [
            block.text
            for block in response.content
            if hasattr(block, "text")
        ]
        return "\n".join(parts).strip()

    def _generate_gemini(self, system: str, user_content: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self._settings.gemini_api_key)
        model = genai.GenerativeModel(
            model_name=self._settings.gemini_model,
            system_instruction=system,
        )
        response = model.generate_content(user_content)
        return (response.text or "").strip()
