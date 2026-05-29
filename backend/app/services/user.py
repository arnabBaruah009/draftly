"""User profile and OAuth token management."""

from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.auth.google import GoogleCredentials
from app.core.config import Settings
from app.models.domain import UserDocument
from app.repositories.user import TokenStore, UserRepository
from app.schemas.email import TokenInfo, UpdatePromptRequest, UserResponse


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_store: TokenStore,
        settings: Settings,
    ):
        self._users = user_repo
        self._tokens = token_store
        self._settings = settings

    async def sync_user(
        self,
        credentials: GoogleCredentials,
        *,
        refresh_token: str | None = None,
        name: str | None = None,
    ) -> UserDocument:
        info = credentials.token_info
        if info is None or not info.email:
            info = await self._fetch_token_info(credentials.access_token)

        user = await self._users.upsert_from_google(
            email=info.email or "",
            name=name,
            google_sub=info.user_id,
        )

        # Keep the existing refresh token when the client doesn't send one.
        effective_refresh = refresh_token or user.refresh_token

        await self._persist_tokens(
            user.id,
            access_token=credentials.access_token,
            refresh_token=effective_refresh,
            expires_in=info.expires_in,
        )
        return await self._users.find_by_id(user.id) or user

    async def get_user_from_credentials(
        self, credentials: GoogleCredentials
    ) -> UserDocument:
        info = credentials.token_info
        if info is None or not info.email:
            info = await self._fetch_token_info(credentials.access_token)

        user = await self._users.find_by_email(info.email or "")
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found. Call POST /api/users/sync first.",
            )
        return user

    async def update_preferences(
        self, user_id: str, payload: UpdatePromptRequest
    ) -> UserDocument:
        user = await self._users.update_preferences(
            user_id,
            current_prompt=payload.current_prompt,
            writing_style=payload.writing_style,
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    async def logout(self, user_id: str) -> None:
        await self._tokens.delete_tokens(user_id)
        await self._users.clear_tokens(user_id)

    async def refresh_access_token(self, user_id: str) -> str | None:
        """Refresh Google access token using stored refresh token."""
        tokens = await self._get_stored_tokens(user_id)
        if tokens is None or not tokens.get("refresh_token"):
            return None

        if not self._settings.google_client_id:
            return tokens.get("access_token")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self._settings.google_client_id,
                    "client_secret": self._settings.google_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": tokens["refresh_token"],
                },
            )

        if response.status_code != 200:
            return tokens.get("access_token")

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            return None

        await self._persist_tokens(
            user_id,
            access_token=access_token,
            refresh_token=data.get("refresh_token")
            or tokens.get("refresh_token"),
            expires_in=data.get("expires_in"),
        )
        return access_token

    async def find_by_id(self, user_id: str) -> UserDocument | None:
        return await self._users.find_by_id(user_id)

    async def get_valid_access_token(self, user_id: str) -> str | None:
        tokens = await self._get_stored_tokens(user_id)
        if tokens is None:
            return None

        access_token = tokens.get("access_token")
        if access_token:
            if await self._is_access_token_valid(access_token):
                return access_token
            refreshed = await self.refresh_access_token(user_id)
            return refreshed or access_token

        return await self.refresh_access_token(user_id)

    async def _get_stored_tokens(self, user_id: str) -> dict | None:
        """Return tokens from Redis, falling back to MongoDB when cache expires."""
        cached = await self._tokens.get_tokens(user_id)
        if cached is not None:
            return cached

        user = await self._users.find_by_id(user_id)
        if user is None or not user.access_token:
            return None

        payload = {
            "access_token": user.access_token,
            "refresh_token": user.refresh_token,
        }
        # Warm Redis from the durable MongoDB copy.
        await self._tokens.save_tokens(
            user_id,
            access_token=user.access_token,
            refresh_token=user.refresh_token,
        )
        return payload

    async def _persist_tokens(
        self,
        user_id: str,
        *,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None = None,
    ) -> None:
        await self._tokens.save_tokens(
            user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )
        await self._users.update_tokens(
            user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def _is_access_token_valid(self, access_token: str) -> bool:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
            )
        return response.status_code == 200

    async def _fetch_token_info(self, access_token: str) -> TokenInfo:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token},
            )
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google access token.",
            )
        return TokenInfo.model_validate(response.json())

    @staticmethod
    def to_response(user: UserDocument) -> UserResponse:
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            current_prompt=user.current_prompt,
            writing_style=user.writing_style,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
