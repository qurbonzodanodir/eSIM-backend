from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import Base, ModelMixin, SoftDeleteMixin
from app.enums.kyc_status import KycStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.auth.models import OtpRequest, RefreshToken
    from app.reseller.models import Order


class User(Base, ModelMixin, SoftDeleteMixin):
    __tablename__ = "users"

    phone: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    kyc_status: Mapped[KycStatus] = mapped_column(
        Enum(KycStatus, name="kyc_status"),
        default=KycStatus.NOT_VERIFIED,
        nullable=False,
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    otp_requests: Mapped[list["OtpRequest"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    numbers: Mapped[list["UserNumber"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserNumber(Base, ModelMixin, SoftDeleteMixin):
    __tablename__ = "user_numbers"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    msisdn: Mapped[str] = mapped_column(String(20), nullable=False)
    operator: Mapped[str] = mapped_column(String(100), nullable=False)
    product: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    user: Mapped["User"] = relationship(back_populates="numbers")