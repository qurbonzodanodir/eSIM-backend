from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app._core.database import get_session
from app.catalog.schemas import OperatorResponse, PremiumNumberResponse
from app.catalog.service import CatalogService


router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/operators", response_model=list[OperatorResponse])
async def list_operators(
    session: AsyncSession = Depends(get_session),
) -> list[OperatorResponse]:
    return await CatalogService(session).list_operators()


@router.get(
    "/operators/{operator_id}",
    response_model=OperatorResponse,
)
async def get_operator(
    operator_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> OperatorResponse:
    return await CatalogService(session).get_operator(operator_id)


@router.get(
    "/operators/{operator_id}/premium-numbers",
    response_model=list[PremiumNumberResponse],
)
async def list_premium_numbers(
    operator_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[PremiumNumberResponse]:
    return await CatalogService(session).list_premium_numbers(operator_id)