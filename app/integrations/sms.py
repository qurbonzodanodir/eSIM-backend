import asyncio
from typing import Protocol

import httpx

from app.core.config import get_settings


class SmsSender(Protocol):
    async def send_otp(self, phone: str, code: str) -> None:
        ...


class DevelopmentSmsSender:
    async def send_otp(self, phone: str, code: str) -> None:
        return None


class SmsProviderError(Exception):
    pass


class SmsCenterSender:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.sms_api_url or not settings.sms_api_key:
            raise SmsProviderError("SMS Center is not configured")
        self.api_url = settings.sms_api_url
        self.api_key = settings.sms_api_key
        self.source_addr = settings.sms_sender_name
        self.timeout = settings.sms_timeout_seconds

    async def send_otp(self, phone: str, code: str) -> None:
        settings = get_settings()
        message = settings.sms_otp_template.format(code=code)
        payload = {
            "phone_number": phone,
            "message": message,
            "source_addr": self.source_addr,
        }
        try:
            async with asyncio.timeout(self.timeout):
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.api_url,
                        headers={
                            "accept": "application/json",
                            "X-API-Key": self.api_key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
        except (httpx.HTTPError, TimeoutError) as error:
            raise SmsProviderError("SMS provider request failed") from error


def get_sms_sender() -> SmsSender:
    if get_settings().sms_provider == "development":
        return DevelopmentSmsSender()
    return SmsCenterSender()