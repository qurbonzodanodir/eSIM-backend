from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, ModelMixin


class MontyBundle(Base, ModelMixin):
    __tablename__ = "monty_bundles"
    __table_args__ = (
        UniqueConstraint("bundle_guid", "currency_key"),
        Index("ix_monty_bundles_active_currency", "is_active", "currency_key"),
    )

    bundle_guid: Mapped[str] = mapped_column(String(100))
    bundle_code: Mapped[str] = mapped_column(String(100), index=True)
    bundle_name: Mapped[str] = mapped_column(String(500))
    currency_key: Mapped[str] = mapped_column(String(10))
    actual_currency: Mapped[str | None] = mapped_column(String(10), index=True)
    bundle_category: Mapped[str | None] = mapped_column(String(100), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    payload: Mapped[dict] = mapped_column(JSON)


class MontyBundleCountry(Base):
    __tablename__ = "monty_bundle_countries"

    bundle_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("monty_bundles.id", ondelete="CASCADE"), primary_key=True,
    )
    country_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("countries.country_code"), primary_key=True, index=True,
    )


class CatalogSyncState(Base):
    __tablename__ = "catalog_sync_state"

    name: Mapped[str] = mapped_column(String(30), primary_key=True)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(500))
