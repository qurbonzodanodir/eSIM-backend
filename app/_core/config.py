from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    app_name: str = "eSIM Reseller Service"
    database_url: str = "postgresql+asyncpg://nodir@localhost:5432/esim_db"
    jwt_secret_key: str = "development-only-secret"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
