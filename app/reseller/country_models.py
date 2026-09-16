from sqlalchemy import Boolean, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, ModelMixin


class Country(Base, ModelMixin):
    __tablename__ = "countries"

    country_code: Mapped[str] = mapped_column(
        String(2),
        unique=True,
        nullable=False,
    )
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(30), nullable=False)
    flag: Mapped[str] = mapped_column(String(8), nullable=False)
    operators: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    popularity_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    is_popular: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
