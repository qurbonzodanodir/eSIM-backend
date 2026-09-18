from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.payment import PaymentService
from app.enums.kyc_status import KycStatus
from app.profile.models import User
from app.profile.schemas import ProfileResponse


ALLOWED_KYC_TRANSITIONS: dict[KycStatus, frozenset[KycStatus]] = {
    KycStatus.NOT_VERIFIED: frozenset({KycStatus.PENDING}),
    KycStatus.PENDING: frozenset(
        {KycStatus.NOT_VERIFIED, KycStatus.VERIFIED}
    ),
    KycStatus.VERIFIED: frozenset(),
}


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

    async def update_kyc_status(
        self,
        user_id: UUID,
        new_status: KycStatus,
    ) -> User:
        user = await self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.deleted_at.is_(None),
            ).with_for_update()
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found",
            )

        if new_status not in ALLOWED_KYC_TRANSITIONS[user.kyc_status]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Invalid KYC transition: "
                    f"{user.kyc_status} -> {new_status}"
                ),
            )

        user.kyc_status = new_status
        await self.session.commit()
        await self.session.refresh(user)
        return user