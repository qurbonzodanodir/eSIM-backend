from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.payment import PaymentService
from app.profile.models import User
from app.profile.schemas import ProfileResponse


class ProfileService:
    def __init__(
        self,
        session: AsyncSession,
        payment_service: PaymentService,
    ) -> None:
        self.session = session
        self.payment_service = payment_service

    async def get_profile(self, user_id: UUID) -> ProfileResponse:
        user = await self.session.scalar(
            select(User)
            .options(selectinload(User.numbers))
            .where(User.id == user_id, User.deleted_at.is_(None))
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )
        card_linked = await self.payment_service.is_card_linked(user.id)
        return ProfileResponse(
            id=user.id,
            phone=user.phone,
            full_name=user.full_name,
            kyc_status=user.kyc_status,
            card_linked=card_linked,
            numbers=[
                {
                    "id": number.id,
                    "msisdn": number.msisdn,
                    "operator": number.operator,
                    "product": number.product,
                    "active": number.active,
                }
                for number in user.numbers
                if number.deleted_at is None
            ],
        )