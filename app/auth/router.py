from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app._core.database import get_session
from app.auth.schemas import (
    RequestOtpRequest,
    RequestOtpResponse,
    RefreshTokenRequest,
    LogoutRequest,
    TokenResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.auth.service import AuthService
from app.integrations.sms import get_sms_sender


router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    return AuthService(session, get_sms_sender())


@router.post("/request-otp", response_model=RequestOtpResponse)
async def request_otp(
    payload: RequestOtpRequest,
    service: AuthService = Depends(get_auth_service),
) -> RequestOtpResponse:
    return await service.request_otp(payload.phone)


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    payload: VerifyOtpRequest,
    service: AuthService = Depends(get_auth_service),
) -> VerifyOtpResponse:
    return await service.verify_otp(payload.phone, payload.code)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshTokenRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    payload: LogoutRequest,
    service: AuthService = Depends(get_auth_service),
) -> None:
    await service.logout(payload.refresh_token)