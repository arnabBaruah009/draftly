"""Shared OpenRouter client (OpenAI-compatible API)."""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from app.core.config import get_settings


@lru_cache
def get_openrouter_client() -> OpenAI:
    """Return a cached OpenAI SDK client pointed at OpenRouter."""
    cfg = get_settings()
    default_headers: dict[str, str] = {}
    if cfg.openrouter_site_url:
        default_headers["HTTP-Referer"] = cfg.openrouter_site_url
    if cfg.openrouter_app_name:
        default_headers["X-OpenRouter-Title"] = cfg.openrouter_app_name

    return OpenAI(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        default_headers=default_headers or None,
    )
