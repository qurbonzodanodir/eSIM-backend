from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app._core.database import get_session
from app._core.config import get_settings
from app._core.security import decode_access_token
from app.enums.kyc_status import KycStatus
from app.integrations.payment import DevelopmentPaymentService
from app.profile.schemas import KycMockResultRequest, ProfileResponse
from app.profile.service import ProfileService


router = APIRouter(tags=["profile"])
bearer_scheme = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> UUID:
    return decode_access_token(credentials.credentials)


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    return await ProfileService(
        session,
        DevelopmentPaymentService(),
    ).get_profile(user_id)


@router.post("/profile/kyc/request", response_model=ProfileResponse)
async def request_kyc(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    service = ProfileService(session, DevelopmentPaymentService())
    await service.update_kyc_status(user_id, KycStatus.PENDING)
    return await service.get_profile(user_id)


@router.post("/profile/kyc/mock-result", response_model=ProfileResponse)
async def set_mock_kyc_result(
    payload: KycMockResultRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    if get_settings().environment != "development":
        raise HTTPException(
            status_code=404,
            detail="Mock KYC endpoint is available only in development",
        )
    if payload.status not in {KycStatus.VERIFIED, KycStatus.NOT_VERIFIED}:
        raise HTTPException(
            status_code=400,
            detail="Mock KYC result must be VERIFIED or NOT_VERIFIED",
        )
    service = ProfileService(session, DevelopmentPaymentService())
    await service.update_kyc_status(user_id, payload.status)
    return await service.get_profile(user_id)