from collections.abc import Mapping
from typing import Any

import httpx

from app.core.config import get_settings


class MontyError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class MontyClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        if not settings.monty_tenant or not settings.monty_api_key:
            raise MontyError(503, "Monty integration is not configured")
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            timeout=settings.monty_timeout_seconds,
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_bundles(self, **filters: Any) -> Mapping[str, Any]:
        return await self._request(
            "GET",
            "/Bundle/get-all-basic/active",
            base_url=self._settings.monty_catalog_base_url,
            params=filters,
            api_key=True,
        )

    async def get_bundles_with_currency(
        self,
        currency_code: str,
        **filters: Any,
    ) -> Mapping[str, Any]:
        return await self._request(
            "GET",
            "/Bundle/get-all-with-currency/active",
            base_url=self._settings.monty_catalog_base_url,
            params={"currencyCode": currency_code, **filters},
            bearer=True,
        )

    async def create_order(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._request(
            "POST",
            "/order/create",
            base_url=self._settings.monty_core_base_url,
            json=dict(payload),
            api_key=True,
        )

    async def top_up(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return await self._request(
            "POST",
            "/order/topup",
            base_url=self._settings.monty_core_base_url,
            json=dict(payload),
            api_key=True,
        )

    async def get_compatible_topups(
        self,
        **filters: Any,
    ) -> Mapping[str, Any]:
        return await self._request(
            "GET",
            "/order/compatible-topup-with-currency",
            base_url=self._settings.monty_core_base_url,
            params=filters,
            api_key=True,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        base_url: str,
        api_key: bool = False,
        bearer: bool = False,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        headers = dict(kwargs.pop("headers", {}))
        headers["Tenant"] = self._settings.monty_tenant
        if api_key:
            headers["api-key"] = self._settings.monty_api_key
        if bearer and self._settings.monty_bearer_token:
            headers["Authorization"] = (
                f"Bearer {self._settings.monty_bearer_token}"
            )
        try:
            response = await self._client.request(
                method,
                f"{base_url.rstrip('/')}/{path.lstrip('/')}",
                headers=headers,
                **kwargs,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise MontyError(
                error.response.status_code,
                "Monty request failed",
            ) from error
        except httpx.HTTPError as error:
            raise MontyError(502, "Monty is unavailable") from error

        if response.status_code == 204:
            return {}
        try:
            data = response.json()
        except ValueError as error:
            raise MontyError(502, "Monty returned invalid JSON") from error
        if not isinstance(data, dict):
            raise MontyError(502, "Monty returned an unexpected response")
        return data
