import asyncio
from decimal import Decimal

from sqlalchemy import delete, select

from app._core.database import session_factory
from app.catalog.models import Operator, PremiumNumber, Tariff
from app.enums.premium_number_tier import PremiumNumberTier


CATALOG = [
    {
        "name": "Tcell",
        "abbr": "TC",
        "prefix": "+992",
        "popular": True,
        "tagline_ru": "Надёжная связь каждый день",
        "tagline_tj": "Алоқаи боэътимод ҳар рӯз",
        "tagline_en": "Reliable connection every day",
        "tariffs": [
            {
                "name": "Start",
                "data": "5 GB",
                "minutes": 100,
                "sms": 50,
                "price": Decimal("25.00"),
                "best": False,
            },
            {
                "name": "Smart",
                "data": "15 GB",
                "minutes": 500,
                "sms": 200,
                "price": Decimal("55.00"),
                "best": True,
            },
        ],
        "premium_numbers": [
            {
                "msisdn": "+992900001111",
                "tier": PremiumNumberTier.GOLD,
                "surcharge": Decimal("100.00"),
            },
            {
                "msisdn": "+992900002222",
                "tier": PremiumNumberTier.SILVER,
                "surcharge": Decimal("50.00"),
            },
        ],
    },
    {
        "name": "MegaFon",
        "abbr": "MF",
        "prefix": "+992",
        "popular": True,
        "tagline_ru": "Больше возможностей для общения",
        "tagline_tj": "Имкониятҳои бештар барои муошират",
        "tagline_en": "More ways to stay connected",
        "tariffs": [
            {
                "name": "Easy",
                "data": "8 GB",
                "minutes": 200,
                "sms": 100,
                "price": Decimal("30.00"),
                "best": False,
            },
            {
                "name": "Max",
                "data": "30 GB",
                "minutes": 1000,
                "sms": 500,
                "price": Decimal("85.00"),
                "best": True,
            },
        ],
        "premium_numbers": [
            {
                "msisdn": "+992900003333",
                "tier": PremiumNumberTier.PLATINUM,
                "surcharge": Decimal("250.00"),
            },
            {
                "msisdn": "+992900004444",
                "tier": PremiumNumberTier.STANDARD,
                "surcharge": Decimal("20.00"),
            },
        ],
    },
    {
        "name": "Babilon-Mobile",
        "abbr": "BM",
        "prefix": "+992",
        "popular": False,
        "tagline_ru": "Связь для работы и дома",
        "tagline_tj": "Алоқа барои кор ва хона",
        "tagline_en": "Connection for work and home",
        "tariffs": [
            {
                "name": "Home",
                "data": "10 GB",
                "minutes": 300,
                "sms": 100,
                "price": Decimal("35.00"),
                "best": True,
            },
            {
                "name": "Family",
                "data": "25 GB",
                "minutes": 700,
                "sms": 300,
                "price": Decimal("70.00"),
                "best": False,
            },
        ],
        "premium_numbers": [
            {
                "msisdn": "+992900005555",
                "tier": PremiumNumberTier.GOLD,
                "surcharge": Decimal("120.00"),
            },
            {
                "msisdn": "+992900006666",
                "tier": PremiumNumberTier.STANDARD,
                "surcharge": Decimal("20.00"),
            },
        ],
    },
]


async def seed_catalog() -> None:
    async with session_factory() as session:
        example_operator = await session.scalar(
            select(Operator).where(Operator.abbr == "EX")
        )
        if example_operator is not None:
            await session.delete(example_operator)
            await session.flush()

        for operator_data in CATALOG:
            operator = await session.scalar(
                select(Operator).where(Operator.abbr == operator_data["abbr"])
            )
            if operator is None:
                operator = Operator(
                    name=operator_data["name"],
                    abbr=operator_data["abbr"],
                    prefix=operator_data["prefix"],
                    popular=operator_data["popular"],
                    tagline_ru=operator_data["tagline_ru"],
                    tagline_tj=operator_data["tagline_tj"],
                    tagline_en=operator_data["tagline_en"],
                )
                session.add(operator)
                await session.flush()
            else:
                for field in (
                    "name",
                    "prefix",
                    "popular",
                    "tagline_ru",
                    "tagline_tj",
                    "tagline_en",
                ):
                    setattr(operator, field, operator_data[field])
                operator.deleted_at = None

            for tariff_data in operator_data["tariffs"]:
                tariff = await session.scalar(
                    select(Tariff).where(
                        Tariff.operator_id == operator.id,
                        Tariff.name == tariff_data["name"],
                    )
                )
                if tariff is None:
                    session.add(Tariff(operator_id=operator.id, **tariff_data))
                else:
                    for field, value in tariff_data.items():
                        setattr(tariff, field, value)
                    tariff.deleted_at = None

            for number_data in operator_data["premium_numbers"]:
                number = await session.scalar(
                    select(PremiumNumber).where(
                        PremiumNumber.msisdn == number_data["msisdn"]
                    )
                )
                if number is None:
                    session.add(
                        PremiumNumber(
                            operator_id=operator.id,
                            **number_data,
                        )
                    )
                else:
                    number.operator_id = operator.id
                    for field, value in number_data.items():
                        setattr(number, field, value)
                    number.deleted_at = None

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed_catalog())
