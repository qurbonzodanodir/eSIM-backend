from fastapi import FastAPI
from sqlalchemy import text

from app._core.config import get_settings
from app._core.database import session_factory
from app.auth.router import router as auth_router
from app.catalog.router import router as catalog_router
from app.profile.router import router as profile_router


def create_app() -> FastAPI:
    application = FastAPI(title=get_settings().app_name)
    application.include_router(auth_router)
    application.include_router(catalog_router)
    application.include_router(profile_router)

    @application.get("/health")
    async def health_check() -> dict[str, str]:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}

    return application


app = create_app()
