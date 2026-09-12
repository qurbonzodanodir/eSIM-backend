from uuid import UUID
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app._core.models import Base, ModelMixin
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