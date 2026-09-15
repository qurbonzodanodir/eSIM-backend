"""add Monty bundle guid to orders"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4a7d2f9c1e8"
down_revision: Union[str, None] = "9dc73156e1ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("bundle_guid", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_orders_bundle_guid",
        "orders",
        ["bundle_guid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_orders_bundle_guid", table_name="orders")
    op.drop_column("orders", "bundle_guid")
