from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "eSIM Reseller Service"
    environment: Literal["development", "staging", "production"] = "development"
    database_url: str = "postgresql+asyncpg://nodir@localhost:5432/esim_db"
    jwt_secret_key: str = "development-only-secret-key-32-bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    otp_expire_minutes: int = 5
    monty_catalog_base_url: str = (
        "https://apis.montytelecom.com/catalog/api/reseller/v1"
    )
    monty_core_base_url: str = "https://mm-hub-api.montytelecom.com/core/api/v1"
    monty_tenant: str | None = None
    monty_api_key: str | None = None
    monty_bearer_token: str | None = None
    monty_timeout_seconds: float = 10.0
    sms_provider: str = "development"
    sms_api_url: str | None = None
    sms_api_key: str | None = None
    sms_sender_name: str | None = None
    sms_timeout_seconds: float = 10.0
    sms_otp_template: str = "Your verification code is {code}"
    payment_provider: str = "development"
    otp_max_requests_per_window: int = 3
    otp_rate_limit_window_seconds: int = 900
    otp_max_attempts: int = 5
    cors_allowed_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.environment == "production":
            if len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
            if self.jwt_secret_key in {
                "development-only-secret-key-32-bytes",
                "change-me-in-development-key-32",
            }:
                raise ValueError("JWT_SECRET_KEY must be changed in production")
            if self.sms_provider == "development":
                raise ValueError("SMS_PROVIDER must use a real provider in production")
            if not self.sms_api_url or not self.sms_api_key or not self.sms_sender_name:
                raise ValueError(
                    "SMS_API_URL, SMS_API_KEY and SMS_SENDER_NAME are required"
                )
            if self.payment_provider == "development":
                raise ValueError(
                    "PAYMENT_PROVIDER must use a real provider in production"
                )
            if not self.monty_tenant or not self.monty_api_key:
                raise ValueError(
                    "MONTY_TENANT and MONTY_API_KEY are required in production"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
