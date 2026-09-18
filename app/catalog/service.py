from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.catalog.models import Operator, PremiumNumber, Tariff
from app.catalog.schemas import (
    OperatorResponse,
    PremiumNumberResponse,
    TaglineResponse,
)


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_operators(self) -> list[OperatorResponse]:
        result = await self.session.scalars(
            select(Operator)
            .options(selectinload(Operator.tariffs.and_(Tariff.deleted_at.is_(None))))
            .where(Operator.deleted_at.is_(None))
            .order_by(Operator.popular.desc(), Operator.name),
        )
        return [
            self._operator_response(operator)
            for operator in result
        ]

    async def get_operator(self, operator_id: UUID) -> OperatorResponse:
        operator = await self.session.scalar(
            select(Operator)
            .options(selectinload(Operator.tariffs.and_(Tariff.deleted_at.is_(None))))
            .where(
                Operator.id == operator_id,
                Operator.deleted_at.is_(None),
            )
        )
        if operator is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operator not found",
            )
        return self._operator_response(operator)

    async def list_premium_numbers(
        self,
        operator_id: UUID,
        *,
        page_number: int = 1,
        page_size: int = 20,
    ) -> list[PremiumNumberResponse]:
        operator_exists = await self.session.scalar(
            select(Operator.id).where(
                Operator.id == operator_id,
                Operator.deleted_at.is_(None),
            )
        )
        if operator_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operator not found",
            )

        result = await self.session.scalars(
            select(PremiumNumber)
            .where(
                PremiumNumber.operator_id == operator_id,
                PremiumNumber.deleted_at.is_(None),
            )
            .order_by(PremiumNumber.surcharge.desc(), PremiumNumber.id.desc())
            .offset((page_number - 1) * page_size)
            .limit(page_size),
        )
        return [
            PremiumNumberResponse.model_validate(number)
            for number in result
        ]

    @staticmethod
    def _operator_response(operator: Operator) -> OperatorResponse:
        return OperatorResponse(
            id=operator.id,
            name=operator.name,
            abbr=operator.abbr,
            prefix=operator.prefix,
            popular=operator.popular,
            tagline=TaglineResponse(
                ru=operator.tagline_ru,
                tj=operator.tagline_tj,
                en=operator.tagline_en,
            ),
            tariffs=[
                tariff
                for tariff in operator.tariffs
                if tariff.deleted_at is None
            ],
        )