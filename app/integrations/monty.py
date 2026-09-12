from collections.abc import Mapping
from typing import Any

import httpx

from app._core.config import get_settings


class MontyError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class MontyClient:
    def __init__(
        self,
        access_token: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        if not settings.monty_base_url:
            raise MontyError(503, "Monty integration is not configured")
        self.access_token = access_token
        self._client = client or httpx.AsyncClient(
            base_url=settings.monty_base_url.rstrip("/"),
            timeout=settings.monty_timeout_seconds,
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def login(self) -> Mapping[str, Any]:
        settings = get_settings()
        if not settings.monty_username or not settings.monty_password:
            raise MontyError(503, "Monty credentials are not configured")
        return await self._request(
            "POST",
            "/Agent/login",
            json={
                "username": settings.monty_username,
                "password": settings.monty_password,
            },
            authenticated=False,
        )

    async def get_bundles(self, **filters: Any) -> Mapping[str, Any]:
        return await self._request("GET", "/Bundles", params=filters)

    async def assign_bundle(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._request("POST", "/Bundles", json=dict(payload))

    async def get_orders(self, **filters: Any) -> Mapping[str, Any]:
        return await self._request("GET", "/Orders", params=filters)

    async def get_consumption(self, **filters: Any) -> Mapping[str, Any]:
        return await self._request(
            "GET",
            "/Orders/Consumption",
            params=filters,
        )

    async def get_available_topups(self, **filters: Any) -> Mapping[str, Any]:
        return await self._request(
            "GET",
            "/Bundles/AvailableTopup",
            params=filters,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        headers = dict(kwargs.pop("headers", {}))
        if authenticated and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        try:
            response = await self._client.request(
                method,
                path,
                headers=headers,
                **kwargs,
            )
        except httpx.HTTPError as error:
            raise MontyError(502, "Monty is unavailable") from error

        if response.status_code == 204:
            return {}
        if response.status_code >= 400:
            raise MontyError(response.status_code, "Monty request failed")
        try:
            data = response.json()
        except ValueError as error:
            raise MontyError(502, "Monty returned invalid JSON") from error
        if not isinstance(data, dict):
            raise MontyError(502, "Monty returned an unexpected response")
        return data