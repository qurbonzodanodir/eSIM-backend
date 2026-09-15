from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.catalog.service import CatalogService
from app.core.database import get_session
from app.integrations.payment import (
    DevelopmentPaymentService,
    PaymentService,
)
from app.integrations.sms import SmsSender, get_sms_sender
from app.profile.service import ProfileService
from app.reseller.service import ResellerService


def get_auth_sms_sender() -> SmsSender:
    return get_sms_sender()


def get_profile_service(
    session: AsyncSession = Depends(get_session),
) -> ProfileService:
    return ProfileService(session, DevelopmentPaymentService())


def get_catalog_service(
    session: AsyncSession = Depends(get_session),
) -> CatalogService:
    return CatalogService(session)


def get_reseller_service(
    session: AsyncSession = Depends(get_session),
) -> ResellerService:
    return ResellerService(session)
