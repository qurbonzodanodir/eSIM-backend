from typing import Protocol


class SmsSender(Protocol):
    async def send_otp(self, phone: str, code: str) -> None:
        ...


class DevelopmentSmsSender:
    async def send_otp(self, phone: str, code: str) -> None:
        return None