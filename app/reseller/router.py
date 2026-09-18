from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_reseller_service
from app.profile.router import get_current_user_id
from app.reseller.schemas import (
    AssignBundleRequest,
    BundleFilters,
    OrderFilters,
    TopupFilters,
    BundleListResponse,
    OrderHistoryResponse,
    OrderResponse,
    PopularCountryListResponse,
    UpstreamResponse,
)
from app.reseller.service import ResellerService
from app.core.validation import Identifier


router = APIRouter(prefix="/reseller", tags=["reseller"])
countries_router = APIRouter(prefix="/countries", tags=["countries"])


@countries_router.get("", response_model=PopularCountryListResponse)
async def list_popular_countries(
    service: ResellerService = Depends(get_reseller_service),
    _: UUID = Depends(get_current_user_id),
) -> PopularCountryListResponse:
    return await service.list_countries()


@router.get("/bundles", response_model=BundleListResponse)
async def list_bundles(
    filters: Annotated[BundleFilters, Query()],
    service: ResellerService = Depends(get_reseller_service),
    _: UUID = Depends(get_current_user_id),
) -> BundleListResponse:
    return await service.list_bundles(filters.model_dump(exclude_none=True))


@router.post("/bundles/assign", response_model=OrderResponse)
async def assign_bundle(
    payload: AssignBundleRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: ResellerService = Depends(get_reseller_service),
) -> OrderResponse:
    return await service.assign_bundle(user_id, payload)


@router.get("/orders", response_model=OrderHistoryResponse)
async def get_orders(
    filters: Annotated[OrderFilters, Query()],
    service: ResellerService = Depends(get_reseller_service),
    user_id: UUID = Depends(get_current_user_id),
) -> OrderHistoryResponse:
    return await service.get_orders(user_id, filters.model_dump(exclude_none=True))


@router.get("/orders/consumption", response_model=UpstreamResponse)
async def get_consumption(
    order_id: Annotated[Identifier, Query()],
    service: ResellerService = Depends(get_reseller_service),
    user_id: UUID = Depends(get_current_user_id),
) -> UpstreamResponse:
    return await service.get_consumption(
        user_id,
        {"order_id": order_id},
    )


@router.get("/bundles/available-topup", response_model=UpstreamResponse)
async def get_available_topups(
    filters: Annotated[TopupFilters, Query()],
    service: ResellerService = Depends(get_reseller_service),
    user_id: UUID = Depends(get_current_user_id),
) -> UpstreamResponse:
    return await service.get_available_topups(user_id, filters.model_dump(exclude_none=True))
