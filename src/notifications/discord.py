from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from src.config import get_settings

SEND_MESSAGE_TIMEOUT = 10  # seconds


class DiscordSender:
    """Send messages via Discord Webhook."""

    def __init__(self):
        settings = get_settings()
        self.webhook_url = settings.discord_webhook_url

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Discord webhook URL is set."""
        settings = get_settings()
        return bool(settings.discord_webhook_url)

    def send(self, text: str, embeds: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Send a message to the configured Discord webhook.

        Args:
            text: Plain text content.
            embeds: Optional list of Discord embed objects.

        Returns:
            True if sent successfully, False otherwise.
        """
        payload: Dict[str, Any] = {}
        if text:
            payload["content"] = text
        if embeds:
            payload["embeds"] = embeds

        if not payload:
            logger.warning("Discord send called with no content")
            return False

        try:
            with httpx.Client(timeout=SEND_MESSAGE_TIMEOUT) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()

            logger.info("Discord webhook message sent")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Discord webhook error: {e.response.status_code} - {e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"Discord webhook request failed: {e}")
            return False
