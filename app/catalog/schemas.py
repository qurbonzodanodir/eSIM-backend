from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums.premium_number_tier import PremiumNumberTier


class TaglineResponse(BaseModel):
    ru: str
    tj: str
    en: str


class TariffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    data: str
    minutes: int
    sms: int
    price: Decimal
    best: bool


class PremiumNumberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    msisdn: str
    tier: PremiumNumberTier
    surcharge: Decimal


class OperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    abbr: str
    prefix: str
    popular: bool
    tagline: TaglineResponse
    tariffs: list[TariffResponse]