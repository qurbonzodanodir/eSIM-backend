from uuid import UUID

from pydantic import BaseModel, Field

from app._core.schemas import ApiSchema
from app.enums.kyc_status import KycStatus


class RequestOtpRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=20)


class RequestOtpResponse(ApiSchema):
    request_id: UUID
    ttl: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(RefreshTokenRequest):
    pass


class ProfileResponse(ApiSchema):
    id: UUID
    phone: str
    full_name: str | None
    kyc_status: KycStatus


class VerifyOtpRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=20)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class VerifyOtpResponse(BaseModel):
    tokens: TokenResponse
    profile: ProfileResponse