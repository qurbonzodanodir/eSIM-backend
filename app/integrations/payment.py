from typing import Protocol
from uuid import UUID

from fastapi import HTTPException, status

from app.core.config import get_settings


class PaymentService(Protocol):
    async def is_card_linked(self, user_id: UUID) -> bool:
        ...


class DevelopmentPaymentService:
    async def is_card_linked(self, user_id: UUID) -> bool:
        return False


def get_payment_service() -> PaymentService:
    provider = get_settings().payment_provider
    if provider == "development":
        return DevelopmentPaymentService()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            f"Payment provider '{provider}' is not configured. "
            "Configure a payment adapter before enabling it."
        ),
    )
