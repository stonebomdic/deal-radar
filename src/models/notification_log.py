from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class NotificationType(enum.Enum):
    new_promotion = "new_promotion"
    expiring_promotion = "expiring_promotion"
    new_card = "new_card"
    price_drop = "price_drop"
    target_price_reached = "target_price_reached"
    flash_deal_new = "flash_deal_new"


class NotificationChannel(enum.Enum):
    telegram = "telegram"
    discord = "discord"


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint(
            "notification_type",
            "reference_id",
            "channel",
            name="uq_notification_dedup",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel), nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog {self.notification_type.value} "
            f"ref={self.reference_id} via {self.channel.value}>"
        )
