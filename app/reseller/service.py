from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

from app._core.config import get_settings
from app.enums.order_status import OrderStatus
from app.integrations.monty import MontyClient, MontyError
from app.reseller.models import Order, ResellerSession
from app.profile.models import User
from app.reseller.schemas import (
    AssignBundleRequest,
    BundleListResponse,
    BundleResponse,
    OrderResponse,
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
            payload = await client.assign_bundle(
                {
                    "bundle_code": request.bundle_code,
                    "email": request.email,
                    "whatsapp": request.whatsapp,
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
    ) -> UpstreamResponse:
        await self._ensure_user(user_id)
        return await self._proxy("get_orders", filters)

    async def get_consumption(
        self,
        user_id: UUID,
        filters: Mapping[str, Any],
    ) -> UpstreamResponse:
        await self._ensure_user(user_id)
        return await self._proxy("get_consumption", filters)

    async def get_available_topups(
        self,
        user_id: UUID,
        filters: Mapping[str, Any],
    ) -> UpstreamResponse:
        await self._ensure_user(user_id)
        return await self._proxy("get_available_topups", filters)

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
        now = datetime.now(UTC)
        session = await self.session.scalar(
            select(ResellerSession).order_by(
                ResellerSession.created_at.desc()
            )
        )
        if session is not None and session.expires_at > now:
            return MontyClient(access_token=session.access_token)

        client = MontyClient()
        try:
            payload = await client.login()
        except Exception:
            await client.close()
            raise
        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise MontyError(502, "Monty login returned no access token")
        client.access_token = access_token
        expires_in = payload.get("expires_in")
        if not isinstance(expires_in, int) or expires_in <= 0:
            expires_in = get_settings().monty_session_expire_seconds
        values = {
            "access_token": access_token,
            "refresh_token": self._value(payload, "refresh_token"),
            "reseller_id": self._value(payload, "reseller_id"),
            "expires_at": now + timedelta(seconds=expires_in),
        }
        if session is None:
            self.session.add(ResellerSession(**values))
        else:
            for field, value in values.items():
                setattr(session, field, value)
        await self.session.commit()
        return client

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