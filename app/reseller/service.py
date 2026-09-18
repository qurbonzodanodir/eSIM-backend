from collections.abc import Mapping
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, text, true
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.enums.order_status import OrderStatus
from app.integrations.monty import MontyClient, MontyError
from app.reseller.models import Order
from app.reseller.country_models import Country
from app.reseller.catalog_models import MontyBundle, MontyBundleCountry
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
        available = (
            select(MontyBundleCountry.bundle_id)
            .join(MontyBundle, MontyBundle.id == MontyBundleCountry.bundle_id)
            .where(
                MontyBundleCountry.country_code == Country.country_code,
                MontyBundle.is_active.is_(True),
            ).exists()
        )
        countries = await self.session.scalars(
            select(Country).where(available).order_by(
                Country.is_popular.desc(), Country.popularity_score.desc(),
                Country.country_name, Country.country_code,
            )
        )
        return PopularCountryListResponse(countries=[
            PopularCountryResponse(
                country_code=c.country_code,
                country_name=c.country_name,
                region=c.region if c.is_active else "other",
                flag=c.flag if c.is_active else "",
                operators=c.operators if c.is_active else [],
                popularity_score=c.popularity_score if c.is_active else 0,
                is_popular=c.is_popular if c.is_active else False,
            ) for c in countries
        ])

    async def list_bundles(self, filters: Mapping[str, Any]) -> BundleListResponse:
        conditions = [MontyBundle.is_active.is_(True)]
        currency = filters.get("currency_code")
        if currency:
            code = str(currency).upper()
            variant = aliased(MontyBundle)
            explicit_variant = select(variant.id).where(
                variant.bundle_guid == MontyBundle.bundle_guid,
                variant.currency_key == code, variant.is_active.is_(True),
            ).exists()
            conditions.append(or_(
                MontyBundle.currency_key == code,
                and_(MontyBundle.currency_key == "", MontyBundle.actual_currency == code,
                     ~explicit_variant),
            ))
        else:
            conditions.append(MontyBundle.currency_key == "")
        country = filters.get("country_code")
        if country:
            conditions.append(select(MontyBundleCountry.bundle_id).where(
                MontyBundleCountry.bundle_id == MontyBundle.id,
                MontyBundleCountry.country_code == str(country).upper(),
            ).exists())
        if filters.get("bundle_code"):
            conditions.append(MontyBundle.bundle_code == filters["bundle_code"])
        if filters.get("bundle_category"):
            conditions.append(MontyBundle.bundle_category == filters["bundle_category"])
        if filters.get("bundle_name"):
            conditions.append(MontyBundle.bundle_name.icontains(
                str(filters["bundle_name"]), autoescape=True,
            ))
        page = int(filters.get("page_number") or 1)
        size = int(filters.get("page_size") or 20)
        page_query = select(MontyBundle.payload, MontyBundle.bundle_guid).where(*conditions).order_by(
            MontyBundle.bundle_guid,
        ).offset((page - 1) * size).limit(size).subquery()
        count_query = select(func.count(MontyBundle.id).label("total")).where(
            *conditions,
        ).subquery()
        rows = (await self.session.execute(
            select(page_query.c.payload, count_query.c.total)
            .select_from(count_query.outerjoin(page_query, true()))
            .order_by(page_query.c.bundle_guid)
        )).all()
        return BundleListResponse(
            bundles=[BundleResponse.model_validate(row.payload) for row in rows if row.payload is not None],
            total=rows[0].total, page_number=page, page_size=size,
        )

    async def assign_bundle(
        self,
        user_id: UUID,
        request: AssignBundleRequest,
    ) -> OrderResponse:
        await self._ensure_user(user_id)
        locked = await self.session.scalar(
            text("SELECT pg_try_advisory_xact_lock(hashtextextended(:order_reference, 0))"),
            {"order_reference": request.order_reference},
        )
        if not locked:
            raise HTTPException(status_code=409, detail="Order is already being processed")
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
            if existing.bundle_guid != request.bundle_guid:
                raise HTTPException(status_code=409, detail="Order reference belongs to a different bundle")
            if existing.status == OrderStatus.PENDING:
                raise HTTPException(
                    status_code=409,
                    detail="Order is pending provider confirmation; do not submit another order",
                )
            return OrderResponse.model_validate(existing)
        else:
            order = Order(
                user_id=user_id,
                order_reference=request.order_reference,
                bundle_code=request.bundle_code or request.bundle_guid,
                bundle_guid=request.bundle_guid,
                status=OrderStatus.PENDING,
            )
            self.session.add(order)
            try:
                await self.session.flush()
            except IntegrityError:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Order reference is already being processed",
                ) from None

        await self.session.commit()

        client: MontyClient | None = None
        try:
            client = await self._get_client()
            payload = await client.create_order(
                self._without_none(
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
            )
        except MontyError as error:
            if client is None:
                order.status = OrderStatus.FAILED
                await self.session.commit()
            raise self._http_error(error) from error
        finally:
            if client is not None:
                await client.close()

        if payload.get("success") is False:
            order.status = OrderStatus.FAILED
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Monty rejected the order",
            )
        order.monty_order_id = self._value(
            payload,
            "order_id",
            "monty_order_id",
        )
        order.iccid = self._value(payload, "iccid")
        if order.monty_order_id is not None or order.iccid is not None:
            order.status = OrderStatus.COMPLETED
        await self.session.commit()
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
            .order_by(Order.created_at.desc(), Order.id.desc())
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
        client: MontyClient | None = None
        try:
            client = await self._get_client()
            payload = await getattr(client, method_name)(**filters)
        except MontyError as error:
            raise self._http_error(error) from error
        finally:
            if client is not None:
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
    def _without_none(payload: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in payload.items()
            if value is not None
        }

    @staticmethod
    def _http_error(error: MontyError) -> HTTPException:
        code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            else status.HTTP_504_GATEWAY_TIMEOUT
            if error.status_code == status.HTTP_504_GATEWAY_TIMEOUT
            else
            status.HTTP_502_BAD_GATEWAY
            if error.status_code >= 500
            else error.status_code
        )
        return HTTPException(status_code=code, detail=error.detail)