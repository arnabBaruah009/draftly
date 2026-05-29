"""Google OAuth2 access-token authentication for FastAPI.

The frontend obtains a Google OAuth2 access token (e.g. via NextAuth's Google
provider) and sends it on every request in the standard ``Authorization``
header:

    Authorization: Bearer <google_access_token>

This module provides a FastAPI dependency that:

  1. Extracts the bearer token from the request.
  2. Optionally verifies the token against Google's ``tokeninfo`` endpoint.
  3. Confirms the token has the Gmail read-only scope.
  4. Returns a small ``GoogleCredentials`` object that downstream code uses
     to build a Gmail API client.

Notes on verification
---------------------
Verifying every request against ``tokeninfo`` adds a network round-trip. Two
mitigations are built in:

  * ``settings.verify_google_token`` lets ops disable the check entirely. When
    disabled, the Gmail API itself rejects bad tokens with 401, which is still
    safe - we just lose the nicer error responses and the scope check.
  * Verification responses are cached for the token's lifetime (minus a small
    safety buffer), keyed by the token itself, so repeated calls within the
    cache window are free.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.schemas.email import TokenInfo

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

# Subtract this many seconds from the token's reported lifetime when caching
# so we never hand out a token that's about to expire.
_TOKEN_CACHE_SAFETY_MARGIN_SECONDS = 30

# Module-level cache: token -> (token_info, expires_at_epoch_seconds).
# Acceptable for a single-process deployment; swap for Redis if you scale out.
_token_info_cache: dict[str, tuple[TokenInfo, float]] = {}


@dataclass(frozen=True)
class GoogleCredentials:
    """The verified Google credentials extracted from a request."""

    access_token: str
    token_info: TokenInfo | None  # None when verification is disabled


_bearer_scheme = HTTPBearer(
    bearerFormat="Google OAuth2 access token",
    description=(
        "Google OAuth2 access token (obtained on the frontend via the Google "
        "OAuth flow). Must have the gmail.modify scope."
    ),
    auto_error=True,
)


async def _fetch_token_info(access_token: str) -> TokenInfo:
    """Call Google's tokeninfo endpoint to validate an access token.

    Raises HTTPException(401) if the token is invalid or expired.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                GOOGLE_TOKENINFO_URL,
                params={"access_token": access_token},
            )
    except httpx.HTTPError as exc:
        # Network error reaching Google - treat as a 503 rather than a 401,
        # because we genuinely don't know if the token is valid.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach Google to verify access token.",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenInfo.model_validate(response.json())


async def _get_or_fetch_token_info(access_token: str) -> TokenInfo:
    """Return cached token info when fresh, otherwise fetch and cache."""
    now = time.monotonic()
    cached = _token_info_cache.get(access_token)
    if cached is not None:
        info, expires_at = cached
        if expires_at > now:
            return info
        # Stale - drop it.
        _token_info_cache.pop(access_token, None)

    info = await _fetch_token_info(access_token)

    lifetime = info.expires_in or 0
    if lifetime > _TOKEN_CACHE_SAFETY_MARGIN_SECONDS:
        _token_info_cache[access_token] = (
            info,
            now + lifetime - _TOKEN_CACHE_SAFETY_MARGIN_SECONDS,
        )

    return info


def _ensure_required_scope(info: TokenInfo, required_scope: str) -> None:
    granted = set((info.scope or "").split())
    if required_scope not in granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access token is missing the required '{required_scope}' "
                "scope."
            ),
        )


async def get_google_credentials(
    creds: Annotated[
        HTTPAuthorizationCredentials, Depends(_bearer_scheme)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> GoogleCredentials:
    """FastAPI dependency that returns verified Google credentials."""
    access_token = creds.credentials

    if not settings.verify_google_token:
        return GoogleCredentials(access_token=access_token, token_info=None)

    info = await _get_or_fetch_token_info(access_token)
    _ensure_required_scope(info, settings.required_gmail_scope)

    return GoogleCredentials(access_token=access_token, token_info=info)


GoogleCredentialsDep = Annotated[
    GoogleCredentials, Depends(get_google_credentials)
]
