from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Draftly API"
    app_version: str = "0.1.0"
    debug: bool = False

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    verify_google_token: bool = True
    required_gmail_scope: str = (
        "https://www.googleapis.com/auth/gmail.modify"
    )

    default_message_limit: int = 10
    max_message_limit: int = 50
    max_sent_backfill: int = 500
    style_context_top_k: int = 5

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "draftly"

    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    email_poll_interval_seconds: int = 300
    email_sync_lookback_seconds: int = 360

    google_client_id: str = ""
    google_client_secret: str = ""

    pinecone_api_key: str = ""
    pinecone_index: str = "draftly-emails"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # OpenRouter (OpenAI-compatible). Use prefixed model slugs, e.g. openai/gpt-4o-mini
    openai_api_key: str = ""
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = "openai/gpt-4o-mini"
    openai_embedding_model: str = "openai/text-embedding-3-small"
    openai_embedding_dimension: int = 1024
    openrouter_site_url: str = "http://localhost:3000"
    openrouter_app_name: str = "Draftly"


@lru_cache
def get_settings() -> Settings:
    return Settings()
