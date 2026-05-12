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

    # CORS - comma-separated list of allowed origins
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # Whether to explicitly verify the incoming Google access token against
    # Google's tokeninfo endpoint. When False, the Gmail API itself acts as
    # the verifier (it will reject invalid tokens with 401), saving a network
    # round-trip per request.
    verify_google_token: bool = True

    # Required scope the access token must include in order to read Gmail.
    required_gmail_scope: str = (
        "https://www.googleapis.com/auth/gmail.readonly"
    )

    # Default number of messages returned by the /gmail/messages endpoint.
    default_message_limit: int = 10
    max_message_limit: int = 50


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Cached so the .env file is read only once per process.
    """
    return Settings()
