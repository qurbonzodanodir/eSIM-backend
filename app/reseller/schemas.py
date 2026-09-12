from datetime import datetime
from decimal import Decimal
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


class BundleResponse(BaseModel):
    bundle_code: str
    bundle_name: str
    reseller_retail_price: Decimal | None = None
    validity: str | None = None
    data_unit: str | None = None


class AssignBundleRequest(BaseModel):
    order_reference: str
    bundle_code: str
    email: str | None = None
    whatsapp: str | None = None


class BundleListResponse(BaseModel):
    bundles: list[BundleResponse]


class UpstreamResponse(BaseModel):
    data: dict