"""remove redundant countries index"""

from typing import Sequence, Union

from alembic import op


revision: str = "8c42e6b1d903"
down_revision: Union[str, None] = "7f31c4e8a2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_countries_country_code", table_name="countries")


def downgrade() -> None:
    op.create_index(
        "ix_countries_country_code",
        "countries",
        ["country_code"],
        unique=False,
    )
