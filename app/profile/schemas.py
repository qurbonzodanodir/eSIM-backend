from uuid import UUID

from app.core.schemas import ApiSchema
from app.enums.kyc_status import KycStatus


class ProfileResponse(ApiSchema):
    id: UUID
    phone: str
    full_name: str | None
    kyc_status: KycStatus
    card_linked: bool
    numbers: list["UserNumberResponse"]


class UserNumberResponse(ApiSchema):
    id: UUID
    msisdn: str
    operator: str
    product: str
    active: bool



class KycMockResultRequest(ApiSchema):
    status: KycStatus