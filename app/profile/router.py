from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app._core.database import get_session
from app._core.security import decode_access_token
from app.integrations.payment import DevelopmentPaymentService
from app.profile.schemas import ProfileResponse
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