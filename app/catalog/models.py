from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import Base, ModelMixin, SoftDeleteMixin
from app.enums.premium_number_tier import PremiumNumberTier


class Operator(Base, ModelMixin, SoftDeleteMixin):
    __tablename__ = "operators"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    abbr: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    popular: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tagline_ru: Mapped[str] = mapped_column(Text, nullable=False)
    tagline_tj: Mapped[str] = mapped_column(Text, nullable=False)
    tagline_en: Mapped[str] = mapped_column(Text, nullable=False)
    tariffs: Mapped[list["Tariff"]] = relationship(
        back_populates="operator",
        cascade="all, delete-orphan",
    )
    premium_numbers: Mapped[list["PremiumNumber"]] = relationship(
        back_populates="operator",
        cascade="all, delete-orphan",
    )


class Tariff(Base, ModelMixin, SoftDeleteMixin):
    __tablename__ = "tariffs"

    operator_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("operators.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    data: Mapped[str] = mapped_column(String(50), nullable=False)
    minutes: Mapped[int] = mapped_column(nullable=False)
    sms: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    best: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    operator: Mapped["Operator"] = relationship(back_populates="tariffs")


class PremiumNumber(Base, ModelMixin, SoftDeleteMixin):
    __tablename__ = "premium_numbers"

    operator_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("operators.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    msisdn: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )
    tier: Mapped[PremiumNumberTier] = mapped_column(
        Enum(PremiumNumberTier, name="premium_number_tier"),
        nullable=False,
    )
    surcharge: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    operator: Mapped["Operator"] = relationship(back_populates="premium_numbers")

Index(
    "ix_premium_numbers_operator_price_id",
    PremiumNumber.operator_id, PremiumNumber.surcharge.desc(), PremiumNumber.id.desc(),
    postgresql_where=PremiumNumber.deleted_at.is_(None),
)
