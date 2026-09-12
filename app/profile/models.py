from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app._core.models import Base, ModelMixin, SoftDeleteMixin
from app.enums.kyc_status import KycStatus

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.auth.models import OtpRequest, RefreshToken


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