from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base
from src.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.models.price_history import PriceHistory


class TrackedProduct(Base, TimestampMixin):
    __tablename__ = "tracked_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # pchome / momo
    product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    target_price: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    price_history: Mapped[List["PriceHistory"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<TrackedProduct {self.platform}:{self.name}>"
