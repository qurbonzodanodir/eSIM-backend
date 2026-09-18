"""Add local Monty catalog and synchronization state."""
from alembic import op
import sqlalchemy as sa

revision = "b714ce903a20"
down_revision = "8c42e6b1d903"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monty_bundles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bundle_guid", sa.String(100), nullable=False),
        sa.Column("bundle_code", sa.String(100), nullable=False),
        sa.Column("bundle_name", sa.String(500), nullable=False),
        sa.Column("currency_key", sa.String(10), nullable=False),
        sa.Column("actual_currency", sa.String(10)),
        sa.Column("bundle_category", sa.String(100)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint("bundle_guid", "currency_key"),
    )
    op.create_index("ix_monty_bundles_actual_currency", "monty_bundles", ["actual_currency"])
    op.create_index("ix_monty_bundles_bundle_code", "monty_bundles", ["bundle_code"])
    op.create_index("ix_monty_bundles_bundle_category", "monty_bundles", ["bundle_category"])
    op.create_index("ix_monty_bundles_active_currency", "monty_bundles", ["is_active", "currency_key"])
    op.create_table(
        "monty_bundle_countries",
        sa.Column("bundle_id", sa.Uuid(), sa.ForeignKey("monty_bundles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("country_code", sa.String(2), sa.ForeignKey("countries.country_code"), primary_key=True),
    )
    op.create_index("ix_monty_bundle_countries_country_code", "monty_bundle_countries", ["country_code"])
    op.create_table(
        "catalog_sync_state",
        sa.Column("name", sa.String(30), primary_key=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("error", sa.String(500)),
    )


def downgrade():
    op.drop_table("catalog_sync_state")
    op.drop_table("monty_bundle_countries")
    op.drop_table("monty_bundles")
