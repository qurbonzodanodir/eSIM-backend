from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_catalog_service
from app.catalog.schemas import OperatorResponse, PremiumNumberResponse
from app.catalog.service import CatalogService


router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/operators", response_model=list[OperatorResponse])
async def list_operators(
    service: CatalogService = Depends(get_catalog_service),
) -> list[OperatorResponse]:
    return await service.list_operators()


@router.get(
    "/operators/{operator_id}",
    response_model=OperatorResponse,
)
async def get_operator(
    operator_id: UUID,
    service: CatalogService = Depends(get_catalog_service),
) -> OperatorResponse:
    return await service.get_operator(operator_id)


@router.get(
    "/operators/{operator_id}/premium-numbers",
    response_model=list[PremiumNumberResponse],
)
async def list_premium_numbers(
    operator_id: UUID,
    service: CatalogService = Depends(get_catalog_service),
) -> list[PremiumNumberResponse]:
    return await service.list_premium_numbers(operator_id)