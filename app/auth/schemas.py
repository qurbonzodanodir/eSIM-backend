from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas import ApiSchema
from app.core.validation import PhoneNumber
from app.enums.kyc_status import KycStatus


class RequestOtpRequest(BaseModel):
    phone: PhoneNumber


class RequestOtpResponse(ApiSchema):
    request_id: UUID
    ttl: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=512, pattern=r"^\S+$")


class LogoutRequest(RefreshTokenRequest):
    pass


class ProfileResponse(ApiSchema):
    id: UUID
    phone: str
    full_name: str | None
    kyc_status: KycStatus


class VerifyOtpRequest(BaseModel):
    phone: PhoneNumber
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


class VerifyOtpResponse(BaseModel):
    tokens: TokenResponse
    profile: ProfileResponse