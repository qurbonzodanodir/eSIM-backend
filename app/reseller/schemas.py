from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.enums.order_status import OrderStatus


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    order_reference: str
    bundle_code: str
    bundle_guid: str | None
    monty_order_id: str | None
    iccid: str | None
    status: OrderStatus
    created_at: datetime


class OrderHistoryResponse(BaseModel):
    orders: list[OrderResponse]
    total: int
    page_number: int
    page_size: int


class BundleResponse(BaseModel):
    bundle_guid: str
    bundle_code: str
    bundle_name: str
    country_code: str | None = None
    country_name: str | None = None
    provider_name: str | None = None
    data_amount: Decimal | None = None
    price: Decimal | None = None
    currency_code: str | None = None
    validity: str | None = None
    data_unit: str | None = None
    support_topup: bool | None = None


class AssignBundleRequest(BaseModel):
    order_reference: str
    bundle_guid: str
    bundle_code: str | None = None
    email: str | None = None
    name: str | None = None
    payment_method: str | None = None
    currency_code: str | None = None
    whatsapp_number: str | None = Field(
        default=None,
        validation_alias=AliasChoices("whatsapp_number", "whatsapp"),
    )


class BundleListResponse(BaseModel):
    bundles: list[BundleResponse]
    total: int
    page_number: int
    page_size: int


class PopularCountryResponse(BaseModel):
    country_code: str
    country_name: str
    flag: str
    operators: list[str]
    popularity_score: int
    is_popular: bool = True


class PopularCountryListResponse(BaseModel):
    countries: list[PopularCountryResponse]


class UpstreamResponse(BaseModel):
    data: dict