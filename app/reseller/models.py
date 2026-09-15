from uuid import UUID
from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import Base, ModelMixin
from app.enums.order_status import OrderStatus

if TYPE_CHECKING:
    from app.profile.models import User


class Order(Base, ModelMixin):
    __tablename__ = "orders"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_reference: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    bundle_code: Mapped[str] = mapped_column(String(100), nullable=False)
    bundle_guid: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    monty_order_id: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
    )
    iccid: Mapped[str | None] = mapped_column(
        String(30),
        unique=True,
        nullable=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    user: Mapped["User"] = relationship(back_populates="orders")


class ResellerSession(Base, ModelMixin):
    __tablename__ = "reseller_sessions"

    access_token: Mapped[str] = mapped_column(String(2048), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(2048))
    reseller_id: Mapped[str | None] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )