from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Annotated, Self

from pydantic import AliasChoices, AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.enums.order_status import OrderStatus
from app.core.validation import (
    BundleGuid, CountryCode, CurrencyCode, Identifier, PageNumber, PageSize, PhoneNumber, SearchText,
)


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
    order_reference: Identifier
    bundle_guid: BundleGuid
    bundle_code: Identifier | None = None
    email: Annotated[EmailStr, Field(max_length=254)] | None = None
    name: SearchText | None = None
    payment_method: Identifier | None = None
    currency_code: CurrencyCode | None = None
    whatsapp_number: PhoneNumber | None = Field(
        default=None,
        validation_alias=AliasChoices("whatsapp_number", "whatsapp"),
    )


class BundleFilters(BaseModel):
    country_code: CountryCode | None = None
    bundle_category: Identifier | None = None
    bundle_name: SearchText | None = None
    bundle_code: Identifier | None = None
    currency_code: CurrencyCode | None = None
    page_number: PageNumber = 1
    page_size: PageSize = 20


class OrderFilters(BaseModel):
    order_id: Identifier | None = None
    order_reference: Identifier | None = None
    start_date: AwareDatetime | None = Field(default=None, alias="startDate")
    end_date: AwareDatetime | None = Field(default=None, alias="endDate")
    page_number: PageNumber = 1
    page_size: PageSize = 50

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("startDate must be before or equal to endDate")
        return self


class TopupFilters(BaseModel):
    bundle_code: Identifier
    country_code: CountryCode | None = None
    currency_code: CurrencyCode | None = None


class BundleListResponse(BaseModel):
    bundles: list[BundleResponse]
    total: int
    page_number: int
    page_size: int


class PopularCountryResponse(BaseModel):
    country_code: str
    country_name: str
    region: str
    flag: str
    operators: list[str]
    popularity_score: int
    is_popular: bool = True


class PopularCountryListResponse(BaseModel):
    countries: list[PopularCountryResponse]


class UpstreamResponse(BaseModel):
    data: dict