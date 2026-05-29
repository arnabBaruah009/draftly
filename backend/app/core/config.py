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

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "draftly"

    redis_url: str = "redis://localhost:6379/0"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    email_poll_interval_seconds: int = 120

    google_client_id: str = ""
    google_client_secret: str = ""

    pinecone_api_key: str = ""
    pinecone_index: str = "draftly-emails"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_embedding_model: str = "text-embedding-3-small"


@lru_cache
def get_settings() -> Settings:
    return Settings()
