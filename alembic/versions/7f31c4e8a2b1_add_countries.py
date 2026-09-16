"""add countries metadata"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f31c4e8a2b1"
down_revision: Union[str, None] = "4a7d2f9c1e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COUNTRIES = (
    ("TR", "Turkey", "asia", "🇹🇷", ["Turkcell", "Vodafone TR"], 100, True, 1),
    ("AE", "United Arab Emirates", "middle_east", "🇦🇪", ["Etisalat", "du"], 90, True, 2),
    ("KZ", "Kazakhstan", "asia", "🇰🇿", ["Kcell", "Beeline KZ", "Tele2"], 80, True, 3),
    ("CN", "China", "asia", "🇨🇳", ["China Mobile", "China Unicom"], 70, True, 4),
    ("UZ", "Uzbekistan", "asia", "🇺🇿", ["Ucell", "Beeline UZ"], 60, True, 5),
    ("SA", "Saudi Arabia", "middle_east", "🇸🇦", ["STC", "Zain", "Mobily"], 50, True, 6),
    ("KG", "Kyrgyzstan", "asia", "🇰🇬", ["Beeline KG", "MegaCom"], 40, True, 7),
    ("QA", "Qatar", "middle_east", "🇶🇦", ["Ooredoo", "Vodafone QA"], 30, True, 8),
    ("DE", "Germany", "europe", "🇩🇪", ["Telekom", "Vodafone DE"], 20, True, 9),
    ("PL", "Poland", "europe", "🇵🇱", ["Orange", "Play"], 10, True, 10),
)


def upgrade() -> None:
    countries = op.create_table(
        "countries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("country_name", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=30), nullable=False),
        sa.Column("flag", sa.String(length=8), nullable=False),
        sa.Column("operators", sa.JSON(), nullable=False),
        sa.Column("popularity_score", sa.Integer(), nullable=False),
        sa.Column("is_popular", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("country_code"),
    )
    op.create_index("ix_countries_country_code", "countries", ["country_code"])

    countries_table = sa.table(
        "countries",
        sa.column("id", sa.Uuid()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("country_code", sa.String()),
        sa.column("country_name", sa.String()),
        sa.column("region", sa.String()),
        sa.column("flag", sa.String()),
        sa.column("operators", sa.JSON()),
        sa.column("popularity_score", sa.Integer()),
        sa.column("is_popular", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    from uuid import uuid4
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    op.bulk_insert(
        countries_table,
        [
            {
                "id": uuid4(),
                "created_at": now,
                "updated_at": now,
                "country_code": code,
                "country_name": name,
                "region": region,
                "flag": flag,
                "operators": operators,
                "popularity_score": score,
                "is_popular": popular,
                "sort_order": order,
                "is_active": True,
            }
            for code, name, region, flag, operators, score, popular, order
            in COUNTRIES
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_countries_country_code", table_name="countries")
    op.drop_table("countries")
