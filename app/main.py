from fastapi import FastAPI
from sqlalchemy import text

from app._core.config import get_settings
from app._core.database import session_factory


def create_app() -> FastAPI:
    application = FastAPI(title=get_settings().app_name)

    @application.get("/health")
    async def health_check() -> dict[str, str]:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}

    return application


app = create_app()
