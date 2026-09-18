import argparse
import asyncio
import logging

from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.reseller.sync import synchronize

logger = logging.getLogger(__name__)


async def run(once: bool) -> None:
    try:
        while True:
            try:
                await synchronize()
            except Exception:
                logger.exception("Catalog synchronization failed; previous snapshot retained")
                if once:
                    raise
            if once:
                return
            await asyncio.sleep(get_settings().monty_sync_interval_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run with python -m app.reseller.worker [--once].")
    parser.add_argument("--once", action="store_true")
    configure_logging()
    asyncio.run(run(parser.parse_args().once))
