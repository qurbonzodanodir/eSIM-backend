"""Index order history and active premium-number pagination."""
from alembic import op
import sqlalchemy as sa

revision = "c821de014b31"
down_revision = "b714ce903a20"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_orders_user_created_id", "orders",
        ["user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_premium_numbers_operator_price_id", "premium_numbers",
        ["operator_id", sa.text("surcharge DESC"), sa.text("id DESC")],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade():
    op.drop_index("ix_premium_numbers_operator_price_id", table_name="premium_numbers")
    op.drop_index("ix_orders_user_created_id", table_name="orders")
