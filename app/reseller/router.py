from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_reseller_service
from app.profile.router import get_current_user_id
from app.reseller.schemas import (
    AssignBundleRequest,
    BundleListResponse,
    OrderHistoryResponse,
    OrderResponse,
    UpstreamResponse,
)
from app.reseller.service import ResellerService


router = APIRouter(prefix="/reseller", tags=["reseller"])


@router.get("/bundles", response_model=BundleListResponse)
async def list_bundles(
    country_code: str | None = Query(default=None),
    bundle_category: str | None = Query(default=None),
    bundle_name: str | None = Query(default=None),
    bundle_code: str | None = Query(default=None),
    currency_code: str | None = Query(default=None),
    page_number: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    service: ResellerService = Depends(get_reseller_service),
    _: UUID = Depends(get_current_user_id),
) -> BundleListResponse:
    filters = {
        key: value
        for key, value in {
            "country_code": country_code,
            "bundle_category": bundle_category,
            "bundle_name": bundle_name,
            "bundle_code": bundle_code,
            "currency_code": currency_code,
            "page_number": page_number,
            "page_size": page_size,
        }.items()
        if value is not None
    }
    return await service.list_bundles(filters)


@router.post("/bundles/assign", response_model=OrderResponse)
async def assign_bundle(
    payload: AssignBundleRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ResellerService = Depends(get_reseller_service),
) -> OrderResponse:
    return await service.assign_bundle(user_id, payload)


@router.get("/orders", response_model=OrderHistoryResponse)
async def get_orders(
    order_id: str | None = Query(default=None),
    order_reference: str | None = Query(default=None),
    startDate: datetime | None = Query(default=None),
    endDate: datetime | None = Query(default=None),
    page_number: int | None = Query(default=None, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    service: ResellerService = Depends(get_reseller_service),
    user_id: UUID = Depends(get_current_user_id),
) -> OrderHistoryResponse:
    filters = {
        key: value
        for key, value in {
            "order_id": order_id,
            "order_reference": order_reference,
            "start_date": startDate,
            "end_date": endDate,
            "page_number": page_number,
            "page_size": page_size,
        }.items()
        if value is not None
    }
    return await service.get_orders(user_id, filters)


@router.get("/orders/consumption", response_model=UpstreamResponse)
async def get_consumption(
    order_id: str = Query(min_length=1),
    service: ResellerService = Depends(get_reseller_service),
    user_id: UUID = Depends(get_current_user_id),
) -> UpstreamResponse:
    return await service.get_consumption(
        user_id,
        {"order_id": order_id},
    )


@router.get("/bundles/available-topup", response_model=UpstreamResponse)
async def get_available_topups(
    bundle_code: str = Query(min_length=1),
    country_code: str | None = Query(default=None),
    currency_code: str | None = Query(default=None),
    service: ResellerService = Depends(get_reseller_service),
    user_id: UUID = Depends(get_current_user_id),
) -> UpstreamResponse:
    filters = {
        key: value
        for key, value in {
            "bundle_code": bundle_code,
            "country_code": country_code,
            "currency_code": currency_code,
        }.items()
        if value is not None
    }
    return await service.get_available_topups(user_id, filters)