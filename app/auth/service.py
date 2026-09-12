from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app._core.config import get_settings
from app._core.security import (
    create_access_token,
    generate_otp,
    generate_refresh_token,
    hash_otp,
    hash_token,
    verify_otp,
)
from app.auth.models import OtpRequest, RefreshToken
from app.auth.schemas import (
    ProfileResponse,
    RequestOtpResponse,
    TokenResponse,
    VerifyOtpResponse,
)
from app.integrations.sms import SmsSender
from app.profile.models import User


class AuthService:
    def __init__(self, session: AsyncSession, sms_sender: SmsSender) -> None:
        self.session = session
        self.sms_sender = sms_sender
        self.settings = get_settings()

    async def request_otp(self, phone: str) -> RequestOtpResponse:
        now = datetime.now(UTC)
        window_start = now - timedelta(
            seconds=self.settings.otp_rate_limit_window_seconds,
        )
        recent_requests = await self.session.scalar(
            select(func.count(OtpRequest.id)).where(
                OtpRequest.phone == phone,
                OtpRequest.created_at >= window_start,
            )
        )
        if recent_requests >= self.settings.otp_max_requests_per_window:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests",
            )
        active_requests = await self.session.scalars(
            select(OtpRequest).where(
                OtpRequest.phone == phone,
                OtpRequest.used_at.is_(None),
            )
        )
        for request in active_requests:
            request.used_at = now

        code = generate_otp()
        request = OtpRequest(
            request_id=uuid4(),
            phone=phone,
            code_hash=hash_otp(code),
            expires_at=now
            + timedelta(minutes=self.settings.otp_expire_minutes),
        )
        self.session.add(request)
        await self.session.commit()
        await self.sms_sender.send_otp(phone, code)
        return RequestOtpResponse(
            request_id=request.request_id,
            ttl=self.settings.otp_expire_minutes * 60,
        )

    async def verify_otp(self, phone: str, code: str) -> VerifyOtpResponse:
        now = datetime.now(UTC)
        request = await self.session.scalar(
            select(OtpRequest)
            .where(
                OtpRequest.phone == phone,
                OtpRequest.used_at.is_(None),
                OtpRequest.expires_at > now,
            )
            .order_by(OtpRequest.created_at.desc())
        )
        if request is None or not verify_otp(code, request.code_hash):
            if request is not None:
                request.failed_attempts += 1
                if request.failed_attempts >= self.settings.otp_max_attempts:
                    request.used_at = now
                await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
                if request is not None
                and request.failed_attempts >= self.settings.otp_max_attempts
                else status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP",
            )

        request.used_at = now
        user = await self.session.scalar(
            select(User).where(User.phone == phone, User.deleted_at.is_(None))
        )
        if user is None:
            user = User(phone=phone)
            self.session.add(user)
            await self.session.flush()

        refresh_token = generate_refresh_token()
        refresh_expires_at = now + timedelta(
            days=self.settings.refresh_token_expire_days,
        )
        self.session.add(
            RefreshToken(
                token_hash=hash_token(refresh_token),
                user_id=user.id,
                expires_at=refresh_expires_at,
            )
        )
        await self.session.commit()
        return VerifyOtpResponse(
            tokens=TokenResponse(
                access_token=create_access_token(user.id),
                refresh_token=refresh_token,
            ),
            profile=ProfileResponse(
                id=user.id,
                phone=user.phone,
                full_name=user.full_name,
                kyc_status=user.kyc_status,
            ),
        )

    async def refresh(self, raw_token: str) -> TokenResponse:
        now = datetime.now(UTC)
        token = await self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(raw_token),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = await self.session.scalar(
            select(User).where(
                User.id == token.user_id,
                User.deleted_at.is_(None),
            )
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not available",
            )

        token.revoke()
        new_refresh_token = generate_refresh_token()
        self.session.add(
            RefreshToken(
                token_hash=hash_token(new_refresh_token),
                user_id=user.id,
                expires_at=now
                + timedelta(days=self.settings.refresh_token_expire_days),
            )
        )
        await self.session.commit()
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=new_refresh_token,
        )

    async def logout(self, raw_token: str) -> None:
        token = await self.session.scalar(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(raw_token),
                RefreshToken.revoked_at.is_(None),
            )
        )
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        token.revoke()
        await self.session.commit()