from typing import Protocol
from uuid import UUID


class PaymentService(Protocol):
    async def is_card_linked(self, user_id: UUID) -> bool:
        ...


class DevelopmentPaymentService:
    async def is_card_linked(self, user_id: UUID) -> bool:
        return False
