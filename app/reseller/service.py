from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

from app.enums.order_status import OrderStatus
from app.integrations.monty import MontyClient, MontyError
from app.reseller.models import Order
from app.reseller.country_models import Country
from app.profile.models import User
from app.reseller.schemas import (
    AssignBundleRequest,
    BundleListResponse,
    BundleResponse,
    OrderResponse,
    OrderHistoryResponse,
    PopularCountryListResponse,
    PopularCountryResponse,
    UpstreamResponse,
)


class ResellerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_countries(self) -> PopularCountryListResponse:
        client = await self._get_client()
        countries: dict[str, dict[str, Any]] = {}
        page_size = 100
        page_number = 1
        try:
            while True:
                payload = await client.get_bundles(
                    page_number=page_number,
                    page_size=page_size,
                )
                data = payload.get("data")
                if not isinstance(data, dict):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Monty returned an invalid bundles response",
                    )
                items = data.get("items", [])
                if not isinstance(items, list):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Monty returned an invalid bundles response",
                    )
                for bundle in items:
                    if not isinstance(bundle, dict):
                        continue
                    supported_countries = bundle.get("supportedCountries", [])
                    if not isinstance(supported_countries, list):
                        continue
                    for country in supported_countries:
                        if not isinstance(country, dict):
                            continue
                        code = country.get("isoCode")
                        name = country.get("name")
                        if code and name:
                            countries.setdefault(
                                str(code).upper(),
                                {
                                    "country_code": str(code).upper(),
                                    "country_name": str(name),
                                },
                            )
                total = int(data.get("totalRows", 0) or 0)
                if not items or page_number * page_size >= total:
                    break
                page_number += 1
        except MontyError as error:
            raise self._http_error(error) from error
        finally:
            await client.close()

        codes = list(countries)
        metadata_rows = await self.session.scalars(
            select(Country).where(
                Country.country_code.in_(codes),
                Country.is_active.is_(True),
            )
        )
        metadata_by_code = {
            country.country_code: country for country in metadata_rows
        }
        result = []
        for code, country in countries.items():
            metadata = metadata_by_code.get(code)
            result.append(
                PopularCountryResponse(
                    country_code=code,
                    country_name=(
                        metadata.country_name
                        if metadata is not None
                        else country["country_name"]
                    ),
                    region=metadata.region if metadata is not None else "other",
                    flag=metadata.flag if metadata is not None else "",
                    operators=metadata.operators if metadata is not None else [],
                    popularity_score=(
                        metadata.popularity_score if metadata is not None else 0
                    ),
                    is_popular=(
                        metadata.is_popular if metadata is not None else False
                    ),
                )
            )
        result.sort(
            key=lambda country: (
                not country.is_popular,
                -country.popularity_score,
                country.country_name,
            )
        )
        return PopularCountryListResponse(
            countries=result,
        )

    async def list_bundles(self, filters: Mapping[str, Any]) -> BundleListResponse:
        client = await self._get_client()
        try:
            country_code = filters.get("country_code")
            if country_code is None:
                payload = await client.get_bundles(**filters)
            else:
                payload = await self._get_bundles_for_country(
                    client,
                    country_code=str(country_code),
                    filters=filters,
                )
        except MontyError as error:
            raise self._http_error(error) from error
        finally:
            await client.close()

        data = payload.get("data")
        raw_bundles = (
            data.get("items", [])
            if isinstance(data, dict)
            else payload.get("bundles", [])
        )
        try:
            bundles = [
                BundleResponse.model_validate(self._normalize_bundle(bundle))
                for bundle in raw_bundles
            ]
        except (ValidationError, TypeError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Monty returned an invalid bundles response",
            ) from error
        requested_page = int(filters.get("page_number") or 1)
        requested_size = int(filters.get("page_size") or len(bundles) or 1)
        if country_code is not None:
            start = (requested_page - 1) * requested_size
            bundles = bundles[start : start + requested_size]
        total = (
            data.get("totalRows", len(bundles))
            if isinstance(data, dict)
            else len(bundles)
        )
        return BundleListResponse(
            bundles=bundles,
            total=int(total),
            page_number=int(
                data.get("pageIndex", requested_page)
                if isinstance(data, dict)
                else requested_page
            ),
            page_size=requested_size,
        )

    async def _get_bundles_for_country(
        self,
        client: MontyClient,
        *,
        country_code: str,
        filters: Mapping[str, Any],
    ) -> dict[str, Any]:
        all_items: list[dict[str, Any]] = []
        page_number = 1
        page_size = 100
        normalized_code = country_code.upper()
        while True:
            payload = await client.get_bundles(
                page_number=page_number,
                page_size=page_size,
                **{
                    key: value
                    for key, value in filters.items()
                    if key not in {"country_code", "page_number", "page_size"}
                },
            )
            data = payload.get("data")
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Monty returned an invalid bundles response",
                )
            for item in data["items"]:
                if not isinstance(item, dict):
                    continue
                countries = item.get("supportedCountries", [])
                if not isinstance(countries, list):
                    continue
                if any(
                    isinstance(country, dict)
                    and str(country.get("isoCode", "")).upper() == normalized_code
                    for country in countries
                ):
                    all_items.append(item)
            total = int(data.get("totalRows", 0) or 0)
            if not data["items"] or page_number * page_size >= total:
                break
            page_number += 1
        return {"data": {"items": all_items, "totalRows": len(all_items)}}

    async def assign_bundle(
        self,
        user_id: UUID,
        request: AssignBundleRequest,
    ) -> OrderResponse:
        existing = await self.session.scalar(
            select(Order).where(
                Order.order_reference == request.order_reference,
            )
        )
        if existing is not None:
            if existing.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Order reference is already in use",
                )
            return OrderResponse.model_validate(existing)

        client = await self._get_client()
        try:
            payload = await client.create_order(
                {
                    "ServiceTag": "ESIM",
                    "BundleGuid": request.bundle_guid,
                    "UniqueIdentifier": request.order_reference,
                    "PhoneNumber": request.whatsapp_number,
                    "ClientName": request.name,
                    "Email": request.email,
                    "PaymentMethod": request.payment_method,
                    "CurrencyCode": request.currency_code,
                }
            )
        except MontyError as error:
            raise self._http_error(error) from error
        finally:
            await client.close()

        order = Order(
            user_id=user_id,
            order_reference=request.order_reference,
            bundle_code=request.bundle_code or request.bundle_guid,
            bundle_guid=request.bundle_guid,
            monty_order_id=self._value(payload, "order_id", "monty_order_id"),
            iccid=self._value(payload, "iccid"),
            status=OrderStatus.COMPLETED,
        )
        self.session.add(order)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.session.scalar(
                select(Order).where(
                    Order.order_reference == request.order_reference,
                )
            )
            if existing is None:
                raise
            if existing.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Order reference is already in use",
                )
            return OrderResponse.model_validate(existing)
        await self.session.refresh(order)
        return OrderResponse.model_validate(order)

    async def get_orders(
        self,
        user_id: UUID,
        filters: Mapping[str, Any],
    ) -> OrderHistoryResponse:
        await self._ensure_user(user_id)
        conditions = [Order.user_id == user_id]
        order_id = filters.get("order_id")
        order_reference = filters.get("order_reference")
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")
        if order_id is not None:
            conditions.append(Order.monty_order_id == order_id)
        if order_reference is not None:
            conditions.append(Order.order_reference == order_reference)
        if start_date is not None:
            conditions.append(Order.created_at >= start_date)
        if end_date is not None:
            conditions.append(Order.created_at <= end_date)

        total = await self.session.scalar(
            select(func.count(Order.id)).where(*conditions)
        )
        page_number = int(filters.get("page_number") or 1)
        page_size = int(filters.get("page_size") or 50)
        orders = await self.session.scalars(
            select(Order)
            .where(*conditions)
            .order_by(Order.created_at.desc())
            .offset((page_number - 1) * page_size)
            .limit(page_size)
        )
        return OrderHistoryResponse(
            orders=[OrderResponse.model_validate(order) for order in orders],
            total=total or 0,
            page_number=page_number,
            page_size=page_size,
        )

    async def get_consumption(
        self,
        user_id: UUID,
        filters: Mapping[str, Any],
    ) -> UpstreamResponse:
        await self._ensure_user(user_id)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Monty consumption is not documented in the current API",
        )

    async def get_available_topups(
        self,
        user_id: UUID,
        filters: Mapping[str, Any],
    ) -> UpstreamResponse:
        await self._ensure_user(user_id)
        return await self._proxy("get_compatible_topups", filters)

    async def _proxy(
        self,
        method_name: str,
        filters: Mapping[str, Any],
    ) -> UpstreamResponse:
        client = await self._get_client()
        try:
            payload = await getattr(client, method_name)(**filters)
        except MontyError as error:
            raise self._http_error(error) from error
        finally:
            await client.close()
        return UpstreamResponse(data=dict(payload))

    async def _ensure_user(self, user_id: UUID) -> None:
        user = await self.session.scalar(
            select(User.id).where(
                User.id == user_id,
                User.deleted_at.is_(None),
            )
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )

    async def _get_client(self) -> MontyClient:
        return MontyClient()

    @staticmethod
    def _normalize_bundle(bundle: Any) -> dict[str, Any]:
        if not isinstance(bundle, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Monty returned an invalid bundle",
            )
        return {
            "bundle_guid": bundle.get("recordGuid"),
            "bundle_code": (
                bundle.get("bundleInfo", {}).get("bundleCode")
                if isinstance(bundle.get("bundleInfo"), dict)
                else bundle.get("bundle_code", bundle.get("code"))
            ),
            "bundle_name": bundle.get(
                "bundleDisplayName",
                bundle.get("bundle_name", bundle.get("name")),
            ),
            "country_code": ResellerService._nested_value(
                bundle.get("supportedCountries"),
                "isoCode",
            ),
            "country_name": ResellerService._nested_value(
                bundle.get("supportedCountries"),
                "name",
            ),
            "provider_name": ResellerService._nested_value(
                [bundle.get("provider")],
                "name",
            ),
            "data_amount": (
                bundle.get("bundleInfo", {}).get("gprsLimit")
                if isinstance(bundle.get("bundleInfo"), dict)
                else None
            ),
            "price": bundle.get("price"),
            "currency_code": (
                bundle.get("currency", {}).get("currencyCode")
                if isinstance(bundle.get("currency"), dict)
                else None
            ),
            "validity": ResellerService._nested_value(
                bundle.get("validityPeriodCycle", {}).get("details", [])
                if isinstance(bundle.get("validityPeriodCycle"), dict)
                else [],
                "name",
            ),
            "data_unit": (
                bundle.get("bundleInfo", {}).get("dataUnit")
                if isinstance(bundle.get("bundleInfo"), dict)
                else None
            ),
            "support_topup": (
                bundle.get("bundleInfo", {}).get("supportTopup")
                if isinstance(bundle.get("bundleInfo"), dict)
                else None
            ),
        }

    @staticmethod
    def _nested_value(items: Any, key: str) -> Any:
        if not isinstance(items, list) or not items:
            return None
        item = items[0]
        return item.get(key) if isinstance(item, dict) else None

    @staticmethod
    def _value(payload: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _http_error(error: MontyError) -> HTTPException:
        code = (
            status.HTTP_502_BAD_GATEWAY
            if error.status_code >= 500
            else error.status_code
        )
        return HTTPException(status_code=code, detail=error.detail)