from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums.order_status import OrderStatus


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    order_reference: str
    bundle_code: str
    monty_order_id: str | None
    iccid: str | None
    status: OrderStatus
    created_at: datetime