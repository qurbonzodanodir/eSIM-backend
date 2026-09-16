from uuid import UUID

from pydantic import BaseModel, Field
from pydantic import field_validator
import phonenumbers

from app.core.schemas import ApiSchema
from app.enums.kyc_status import KycStatus


class RequestOtpRequest(BaseModel):
    phone: str = Field(min_length=7, max_length=20)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("+"):
            raise ValueError("Phone number must use international format")
        try:
            parsed = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException as error:
            raise ValueError("Invalid phone number") from error
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number")
        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164,
        )


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

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        return RequestOtpRequest.normalize_phone(value)


class VerifyOtpResponse(BaseModel):
    tokens: TokenResponse
    profile: ProfileResponse