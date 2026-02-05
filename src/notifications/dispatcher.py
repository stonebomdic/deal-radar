from __future__ import annotations

from typing import Any, Dict, List

from loguru import logger
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.notification_log import (
    NotificationChannel,
    NotificationLog,
    NotificationType,
)
from src.notifications.discord import DiscordSender
from src.notifications.telegram import TelegramSender


class NotificationDispatcher:
    """Dispatches notifications to all configured channels with dedup."""

    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()

    def _already_sent(
        self,
        notification_type: NotificationType,
        reference_id: int,
        channel: NotificationChannel,
    ) -> bool:
        """Check if this notification was already sent."""
        exists = (
            self.session.query(NotificationLog)
            .filter_by(
                notification_type=notification_type,
                reference_id=reference_id,
                channel=channel,
            )
            .first()
        )
        return exists is not None

    def _log_sent(
        self,
        notification_type: NotificationType,
        reference_id: int,
        channel: NotificationChannel,
    ) -> None:
        """Record that a notification was sent."""
        log = NotificationLog(
            notification_type=notification_type,
            reference_id=reference_id,
            channel=channel,
        )
        self.session.add(log)
        self.session.commit()

    def dispatch(
        self,
        notification_type: NotificationType,
        reference_ids: List[int],
        message: Dict[str, Any],
    ) -> Dict[str, int]:
        """Dispatch notifications to all configured channels.

        Args:
            notification_type: Type of notification (new_promotion, etc.).
            reference_ids: List of model IDs (promotion or card IDs).
            message: Dict with "telegram" (str) and "discord_embeds" (list) keys.

        Returns:
            Dict with channel names as keys and count of sent notifications as values.
        """
        if not self.settings.notification_enabled:
            logger.info("Notifications are disabled, skipping dispatch")
            return {}

        results: Dict[str, int] = {}

        # Telegram
        if TelegramSender.is_configured():
            unsent_ids = [
                ref_id
                for ref_id in reference_ids
                if not self._already_sent(
                    notification_type, ref_id, NotificationChannel.telegram
                )
            ]
            if unsent_ids and message.get("telegram"):
                sender = TelegramSender()
                success = sender.send(message["telegram"])
                if success:
                    for ref_id in unsent_ids:
                        self._log_sent(
                            notification_type, ref_id, NotificationChannel.telegram
                        )
                    results["telegram"] = len(unsent_ids)
                    logger.info(
                        f"Telegram: sent {notification_type.value} "
                        f"for {len(unsent_ids)} items"
                    )
                else:
                    logger.error(f"Telegram: failed to send {notification_type.value}")
            else:
                logger.debug(
                    f"Telegram: nothing new to send for {notification_type.value}"
                )

        # Discord
        if DiscordSender.is_configured():
            unsent_ids = [
                ref_id
                for ref_id in reference_ids
                if not self._already_sent(
                    notification_type, ref_id, NotificationChannel.discord
                )
            ]
            if unsent_ids and message.get("discord_embeds"):
                sender = DiscordSender()
                # Filter embeds to only unsent ones (embeds correspond to reference_ids by index)
                unsent_set = set(unsent_ids)
                embeds_to_send = [
                    embed
                    for ref_id, embed in zip(reference_ids, message["discord_embeds"])
                    if ref_id in unsent_set
                ]
                # Discord allows max 10 embeds per message; batch if needed
                for i in range(0, len(embeds_to_send), 10):
                    batch = embeds_to_send[i : i + 10]
                    success = sender.send("", embeds=batch)
                    if not success:
                        logger.error(
                            f"Discord: failed to send batch {i // 10 + 1} "
                            f"for {notification_type.value}"
                        )
                        break
                else:
                    # All batches sent successfully
                    for ref_id in unsent_ids:
                        self._log_sent(
                            notification_type, ref_id, NotificationChannel.discord
                        )
                    results["discord"] = len(unsent_ids)
                    logger.info(
                        f"Discord: sent {notification_type.value} "
                        f"for {len(unsent_ids)} items"
                    )
            else:
                logger.debug(
                    f"Discord: nothing new to send for {notification_type.value}"
                )

        return results
