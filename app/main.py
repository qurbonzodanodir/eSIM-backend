from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException, RequestValidationError
from sqlalchemy import text

from app.core.database import session_factory
from app.core.config import get_settings
from app.core.errors import (
    http_exception_handler,
    integrity_error_handler,
    request_validation_error_handler,
    validation_error_handler,
)
from app.core.logging import configure_logging
from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.profile.router import router as profile_router
from app.reseller.router import countries_router, router as reseller_router
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(title=get_settings().app_name)
    settings = get_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip()
            for origin in settings.cors_allowed_origins.split(",")
            if origin.strip()
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_exception_handler(ValidationError, validation_error_handler)
    application.add_exception_handler(HTTPException, http_exception_handler)
    application.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,
    )
    application.add_exception_handler(IntegrityError, integrity_error_handler)
    api_prefix = "/api/v1"
    application.include_router(auth_router, prefix=api_prefix)
    application.include_router(catalog_router, prefix=api_prefix)
    application.include_router(profile_router, prefix=api_prefix)
    application.include_router(countries_router, prefix=api_prefix)
    application.include_router(reseller_router, prefix=api_prefix)

    @application.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/ready")
    async def readiness_check() -> dict[str, str]:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}

    return application


app = create_app()
