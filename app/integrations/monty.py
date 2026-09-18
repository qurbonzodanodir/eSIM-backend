import asyncio
from collections.abc import Mapping
from copy import deepcopy
from time import monotonic
from typing import Any

import httpx

from app.core.config import get_settings


class MontyError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class MontyClient:
    _bundles_cache: dict[
        tuple[tuple[str, Any], ...],
        tuple[float, Mapping[str, Any]],
    ] = {}

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

    async def get_bundles(self, *, use_cache: bool = True, **filters: Any) -> Mapping[str, Any]:
        params = {
            key: value
            for key, value in {
                "pageSize": filters.get("page_size"),
                "pageIndex": filters.get("page_number"),
                "CurrencyCode": filters.get("currency_code"),
                "BundleCode": filters.get("bundle_code"),
                "BundleCategoryTag": filters.get("bundle_category"),
                "Search": filters.get("bundle_name"),
            }.items()
            if value is not None
        }
        cache_key = tuple(sorted(params.items()))
        cached = self._bundles_cache.get(cache_key) if use_cache else None
        now = monotonic()
        if cached is not None:
            expires_at, payload = cached
            if expires_at > now:
                return deepcopy(payload)
            self._bundles_cache.pop(cache_key, None)

        payload = await self._request(
            "GET",
            "/Bundle/get-all-basic/active",
            base_url=self._settings.monty_catalog_base_url,
            params=params,
            api_key=True,
        )
        if use_cache:
            for key, (expires_at, _) in list(self._bundles_cache.items()):
                if expires_at <= monotonic():
                    self._bundles_cache.pop(key, None)
            if len(self._bundles_cache) >= 256:
                self._bundles_cache.pop(next(iter(self._bundles_cache)))
            self._bundles_cache[cache_key] = (
                now + self._settings.monty_bundles_cache_ttl_seconds,
                deepcopy(payload),
            )
        return payload

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
            async with asyncio.timeout(self._settings.monty_timeout_seconds):
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
        except (httpx.TimeoutException, TimeoutError) as error:
            raise MontyError(504, "Monty request timed out") from error
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
        if data.get("success") is False:
            detail = data.get("message") or data.get("error") or "Monty request failed"
            raise MontyError(502, str(detail))
        return data
