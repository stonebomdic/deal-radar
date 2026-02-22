from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base
from src.models.base import TimestampMixin


class FlashDeal(Base, TimestampMixin):
    __tablename__ = "flash_deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_url: Mapped[str] = mapped_column(String(500), nullable=False)
    sale_price: Mapped[int] = mapped_column(Integer, nullable=False)
    original_price: Mapped[Optional[int]] = mapped_column(Integer)
    discount_rate: Mapped[Optional[float]] = mapped_column(Float)
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<FlashDeal {self.platform}:{self.product_name}>"
