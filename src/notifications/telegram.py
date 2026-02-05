from __future__ import annotations

import re

import httpx
from loguru import logger

from src.config import get_settings

# Telegram MarkdownV2 requires escaping these characters
_TELEGRAM_ESCAPE_CHARS = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")

TELEGRAM_API_BASE = "https://api.telegram.org"
SEND_MESSAGE_TIMEOUT = 10  # seconds


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format."""
    return _TELEGRAM_ESCAPE_CHARS.sub(r"\\\1", text)


class TelegramSender:
    """Send messages via Telegram Bot API."""

    def __init__(self):
        settings = get_settings()
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Telegram credentials are set."""
        settings = get_settings()
        return bool(settings.telegram_bot_token and settings.telegram_chat_id)

    def send(self, text: str) -> bool:
        """Send a message to the configured Telegram chat.

        Args:
            text: Message text in MarkdownV2 format.

        Returns:
            True if sent successfully, False otherwise.
        """
        url = f"{TELEGRAM_API_BASE}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        }

        try:
            with httpx.Client(timeout=SEND_MESSAGE_TIMEOUT) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()

            logger.info(f"Telegram message sent to chat {self.chat_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Telegram API error: {e.response.status_code} - {e.response.text}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"Telegram request failed: {e}")
            return False
