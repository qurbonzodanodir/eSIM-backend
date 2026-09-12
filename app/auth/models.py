from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app._core.models import Base, ModelMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.profile.models import User


class RefreshToken(Base, ModelMixin):
    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    def revoke(self) -> None:
        self.revoked_at = datetime.now(UTC)


class OtpRequest(Base, ModelMixin):
    __tablename__ = "otp_requests"

    request_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    code_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user: Mapped["User | None"] = relationship(back_populates="otp_requests")