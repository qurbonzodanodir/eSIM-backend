import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select, text

from app.core.config import get_settings
from app.core.database import session_factory
from app.integrations.monty import MontyClient
from app.reseller.catalog_models import CatalogSyncState, MontyBundle, MontyBundleCountry
from app.reseller.country_models import Country
from app.reseller.regions import region_for_country
from app.reseller.schemas import BundleResponse
from app.reseller.service import ResellerService

logger = logging.getLogger(__name__)
SYNC_LOCK = 724019385


def extract_category(item: dict) -> str | None:
    category = item.get("bundleCategoryTag")
    if category is None and isinstance(item.get("bundleCategory"), dict):
        category = item["bundleCategory"].get("tag")
    if category is not None and not isinstance(category, str):
        raise ValueError("Invalid bundle category tag")
    return category


async def download_catalog(client, currency: str, max_pages: int) -> list[dict]:
    result = []
    seen = set()
    expected_total = None
    for page in range(1, max_pages + 1):
        payload = await client.get_bundles(
            use_cache=False, page_number=page, page_size=100,
            **({"currency_code": currency} if currency else {}),
        )
        data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ValueError("Invalid Monty catalog page")
        total = data.get("totalRows")
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            raise ValueError("Missing or invalid Monty totalRows")
        if data.get("pageIndex") != page:
            raise ValueError("Unexpected Monty pageIndex")
        if expected_total is not None and total != expected_total:
            raise ValueError("Monty catalog changed during pagination")
        expected_total = total
        for item in data["items"]:
            if not isinstance(item, dict):
                raise ValueError("Invalid Monty bundle")
            normalized = BundleResponse.model_validate(ResellerService._normalize_bundle(item))
            if not normalized.bundle_guid or normalized.bundle_guid in seen:
                raise ValueError("Empty or duplicate Monty bundle GUID")
            seen.add(normalized.bundle_guid)
            if currency and (normalized.currency_code or "").upper() != currency:
                raise ValueError("Monty did not return the requested currency")
            countries = item.get("supportedCountries")
            if not isinstance(countries, list) or not countries:
                raise ValueError("Missing supported countries")
            country_map = {}
            for country in countries:
                if not isinstance(country, dict):
                    raise ValueError("Invalid country")
                code, name = country.get("isoCode"), country.get("name")
                if not isinstance(code, str) or len(code) != 2 or not isinstance(name, str) or not name:
                    raise ValueError("Invalid country code or name")
                country_map[code.upper()] = name
            result.append({
                "response": normalized.model_dump(mode="json"),
                "countries": country_map,
                "category": extract_category(item),
            })
        if len(result) == total:
            return result
        if len(result) > total or not data["items"]:
            raise ValueError("Incomplete or inconsistent Monty catalog")
    raise ValueError("Monty catalog exceeds configured page limit")


async def publish_catalog(session, snapshots: dict[str, list[dict]]) -> None:
    existing = {(b.bundle_guid, b.currency_key): b for b in await session.scalars(select(MontyBundle))}
    countries = {c.country_code: c for c in await session.scalars(select(Country))}
    for country in countries.values():
        if country.region == "other":
            country.region = region_for_country(country.country_code)
    for bundle in existing.values():
        bundle.is_active = False
    await session.execute(delete(MontyBundleCountry))
    for currency, items in snapshots.items():
        for item in items:
            payload = item["response"]
            key = (payload["bundle_guid"], currency)
            bundle = existing.get(key)
            if bundle is None:
                bundle = MontyBundle(bundle_guid=key[0], currency_key=currency)
                session.add(bundle)
                existing[key] = bundle
            bundle.bundle_code = payload["bundle_code"]
            bundle.bundle_name = payload["bundle_name"]
            bundle.bundle_category = item["category"]
            bundle.actual_currency = (payload["currency_code"] or "").upper() or None
            bundle.payload = payload
            bundle.is_active = True
            for code, name in item["countries"].items():
                if code not in countries:
                    countries[code] = Country(
                        country_code=code, country_name=name, region=region_for_country(code),
                        flag="", operators=[], is_active=True,
                    )
                    session.add(countries[code])
    await session.flush()
    for currency, items in snapshots.items():
        for item in items:
            bundle = existing[(item["response"]["bundle_guid"], currency)]
            session.add_all([
                MontyBundleCountry(bundle_id=bundle.id, country_code=code)
                for code in item["countries"]
            ])


async def synchronize(factory=session_factory, client_factory=MontyClient) -> bool:
    settings = get_settings()
    attempted = datetime.now(UTC)
    async with factory() as session:
        locked = await session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SYNC_LOCK})
        if not locked:
            logger.info("Catalog synchronization already running")
            return False
        try:
            async with asyncio.timeout(settings.monty_sync_timeout_seconds):
                client = client_factory()
                try:
                    currencies = list(dict.fromkeys(["", *[
                        c.strip().upper() for c in settings.monty_sync_currencies.split(",") if c.strip()
                    ]]))
                    snapshots = {
                        currency: await download_catalog(client, currency, settings.monty_max_bundle_pages)
                        for currency in currencies
                    }
                finally:
                    await client.close()
                if not snapshots[""]:
                    raise ValueError("Refusing to publish an empty Monty catalog")
                await publish_catalog(session, snapshots)
            state = await session.get(CatalogSyncState, "monty")
            if state is None:
                state = CatalogSyncState(name="monty")
                session.add(state)
            state.last_attempt_at = attempted
            state.last_success_at = datetime.now(UTC)
            state.error = None
            await session.commit()
            logger.info("Monty catalog synchronized: %s default bundles", len(snapshots[""]))
            return True
        except Exception as error:
            await session.rollback()
            locked = await session.scalar(
                text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SYNC_LOCK},
            )
            if not locked:
                raise
            state = await session.get(CatalogSyncState, "monty")
            if state is None:
                state = CatalogSyncState(name="monty", last_attempt_at=attempted)
                session.add(state)
            if state.last_attempt_at <= attempted:
                state.last_attempt_at = attempted
                state.error = type(error).__name__
            await session.commit()
            raise
