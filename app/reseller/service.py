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
from app.profile.models import User
from app.reseller.schemas import (
    AssignBundleRequest,
    BundleListResponse,
    BundleResponse,
    OrderResponse,
    OrderHistoryResponse,
    UpstreamResponse,
)


class ResellerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_bundles(self, filters: Mapping[str, Any]) -> BundleListResponse:
        client = await self._get_client()
        try:
            payload = await client.get_bundles(**filters)
        except MontyError as error:
            raise self._http_error(error) from error
        finally:
            await client.close()

        raw_bundles = payload.get("bundles", payload.get("data", []))
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
        return BundleListResponse(bundles=bundles)

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
                    "BundleGuid": request.bundle_code,
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
            bundle_code=request.bundle_code,
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
            "bundle_code": bundle.get("bundle_code", bundle.get("code")),
            "bundle_name": bundle.get("bundle_name", bundle.get("name")),
            "reseller_retail_price": bundle.get(
                "reseller_retail_price",
                bundle.get("price"),
            ),
            "validity": bundle.get("validity"),
            "data_unit": bundle.get("data_unit"),
        }

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