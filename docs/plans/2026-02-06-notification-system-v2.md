# Notification System (Simplified) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Send Telegram and Discord notifications when new promotions/cards are found or promotions are about to expire.

**Architecture:** Scheduler jobs detect changes, format messages, and dispatch to configured channels (Telegram Bot API, Discord Webhook) with dedup via NotificationLog table. All sync -- no async needed since scheduler runs in a separate thread.

**Tech Stack:** Python 3.9+, FastAPI, SQLAlchemy, httpx, APScheduler, pytest

---

## Task 1: Config + NotificationLog Model

### Files to create/modify
- Modify `src/config.py`
- Create `src/models/notification_log.py`
- Modify `src/models/__init__.py`
- Create `tests/test_models_notification_log.py`

### Implementation

**`src/config.py`** -- Modify existing:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/credit_cards.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Crawler
    crawler_delay_min: int = 2
    crawler_delay_max: int = 5
    crawler_max_retries: int = 3

    # Notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""
    notification_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**`src/models/notification_log.py`** -- New file:

```python
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class NotificationType(enum.Enum):
    new_promotion = "new_promotion"
    expiring_promotion = "expiring_promotion"
    new_card = "new_card"


class NotificationChannel(enum.Enum):
    telegram = "telegram"
    discord = "discord"


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        UniqueConstraint(
            "notification_type", "reference_id", "channel",
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
```

**`src/models/__init__.py`** -- Modify existing:

```python
from src.models.bank import Bank
from src.models.card import CreditCard
from src.models.notification_log import NotificationLog, NotificationChannel, NotificationType
from src.models.promotion import Promotion

__all__ = [
    "Bank",
    "CreditCard",
    "NotificationLog",
    "NotificationChannel",
    "NotificationType",
    "Promotion",
]
```

**`tests/test_models_notification_log.py`** -- New file:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models.notification_log import (
    NotificationChannel,
    NotificationLog,
    NotificationType,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_create_notification_log(db_session):
    log = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=1,
        channel=NotificationChannel.telegram,
    )
    db_session.add(log)
    db_session.commit()

    assert log.id is not None
    assert log.notification_type == NotificationType.new_promotion
    assert log.reference_id == 1
    assert log.channel == NotificationChannel.telegram
    assert log.sent_at is not None


def test_notification_log_repr(db_session):
    log = NotificationLog(
        notification_type=NotificationType.expiring_promotion,
        reference_id=42,
        channel=NotificationChannel.discord,
    )
    db_session.add(log)
    db_session.commit()

    assert "expiring_promotion" in repr(log)
    assert "42" in repr(log)
    assert "discord" in repr(log)


def test_notification_log_dedup_constraint(db_session):
    """Same (notification_type, reference_id, channel) should raise IntegrityError."""
    log1 = NotificationLog(
        notification_type=NotificationType.new_card,
        reference_id=10,
        channel=NotificationChannel.telegram,
    )
    db_session.add(log1)
    db_session.commit()

    log2 = NotificationLog(
        notification_type=NotificationType.new_card,
        reference_id=10,
        channel=NotificationChannel.telegram,
    )
    db_session.add(log2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_notification_log_different_channel_allowed(db_session):
    """Same type+reference but different channel should be allowed."""
    log1 = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=5,
        channel=NotificationChannel.telegram,
    )
    log2 = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=5,
        channel=NotificationChannel.discord,
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    assert log1.id is not None
    assert log2.id is not None
    assert log1.id != log2.id


def test_notification_log_different_type_allowed(db_session):
    """Same reference+channel but different type should be allowed."""
    log1 = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=5,
        channel=NotificationChannel.telegram,
    )
    log2 = NotificationLog(
        notification_type=NotificationType.expiring_promotion,
        reference_id=5,
        channel=NotificationChannel.telegram,
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    assert log1.id is not None
    assert log2.id is not None
```

### Verification
```bash
pytest tests/test_models_notification_log.py -v
ruff check src/config.py src/models/notification_log.py src/models/__init__.py
```

---

## Task 2: Telegram + Discord Senders

### Files to create/modify
- Create `src/notifications/__init__.py`
- Create `src/notifications/telegram.py`
- Create `src/notifications/discord.py`
- Create `tests/test_notifications_telegram.py`
- Create `tests/test_notifications_discord.py`

### Implementation

**`src/notifications/__init__.py`** -- New file:

```python
"""Notification senders for Telegram and Discord."""
```

**`src/notifications/telegram.py`** -- New file:

```python
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
```

**`src/notifications/discord.py`** -- New file:

```python
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
```

**`tests/test_notifications_telegram.py`** -- New file:

```python
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.notifications.telegram import TelegramSender, escape_markdown_v2


class TestEscapeMarkdownV2:
    def test_escape_special_chars(self):
        text = "Hello_World! Price: $100.00 (50% off)"
        escaped = escape_markdown_v2(text)
        assert escaped == r"Hello\_World\! Price: \$100\.00 \(50% off\)"

    def test_escape_brackets(self):
        text = "[link](url)"
        escaped = escape_markdown_v2(text)
        assert escaped == r"\[link\]\(url\)"

    def test_no_escape_needed(self):
        text = "Hello World"
        escaped = escape_markdown_v2(text)
        assert escaped == "Hello World"


class TestTelegramSender:
    @patch("src.notifications.telegram.get_settings")
    def test_is_configured_true(self, mock_settings):
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="456",
        )
        assert TelegramSender.is_configured() is True

    @patch("src.notifications.telegram.get_settings")
    def test_is_configured_false_no_token(self, mock_settings):
        mock_settings.return_value = MagicMock(
            telegram_bot_token="",
            telegram_chat_id="456",
        )
        assert TelegramSender.is_configured() is False

    @patch("src.notifications.telegram.get_settings")
    def test_is_configured_false_no_chat_id(self, mock_settings):
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="",
        )
        assert TelegramSender.is_configured() is False

    @patch("src.notifications.telegram.get_settings")
    def test_send_success(self, mock_settings):
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="456",
        )
        sender = TelegramSender()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = sender.send("Hello")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "456" == call_args.kwargs["json"]["chat_id"]
        assert "MarkdownV2" == call_args.kwargs["json"]["parse_mode"]

    @patch("src.notifications.telegram.get_settings")
    def test_send_http_error(self, mock_settings):
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="456",
        )
        sender = TelegramSender()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)

            mock_request = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 403
            mock_response.text = "Forbidden"
            mock_client.post.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Forbidden", request=mock_request, response=mock_response
            )
            mock_client_cls.return_value = mock_client

            result = sender.send("Hello")

        assert result is False

    @patch("src.notifications.telegram.get_settings")
    def test_send_request_error(self, mock_settings):
        mock_settings.return_value = MagicMock(
            telegram_bot_token="123:ABC",
            telegram_chat_id="456",
        )
        sender = TelegramSender()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.RequestError("Connection failed")
            mock_client_cls.return_value = mock_client

            result = sender.send("Hello")

        assert result is False
```

**`tests/test_notifications_discord.py`** -- New file:

```python
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.notifications.discord import DiscordSender


class TestDiscordSender:
    @patch("src.notifications.discord.get_settings")
    def test_is_configured_true(self, mock_settings):
        mock_settings.return_value = MagicMock(
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        assert DiscordSender.is_configured() is True

    @patch("src.notifications.discord.get_settings")
    def test_is_configured_false(self, mock_settings):
        mock_settings.return_value = MagicMock(
            discord_webhook_url="",
        )
        assert DiscordSender.is_configured() is False

    @patch("src.notifications.discord.get_settings")
    def test_send_text_success(self, mock_settings):
        mock_settings.return_value = MagicMock(
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        sender = DiscordSender()

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = sender.send("Hello Discord")

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args.kwargs["json"]["content"] == "Hello Discord"

    @patch("src.notifications.discord.get_settings")
    def test_send_with_embeds(self, mock_settings):
        mock_settings.return_value = MagicMock(
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        sender = DiscordSender()

        embeds = [{"title": "Test", "description": "Test embed", "color": 0x00FF00}]

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            result = sender.send("", embeds=embeds)

        assert result is True
        call_args = mock_client.post.call_args
        assert call_args.kwargs["json"]["embeds"] == embeds

    @patch("src.notifications.discord.get_settings")
    def test_send_empty_content_returns_false(self, mock_settings):
        mock_settings.return_value = MagicMock(
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        sender = DiscordSender()
        result = sender.send("")
        assert result is False

    @patch("src.notifications.discord.get_settings")
    def test_send_http_error(self, mock_settings):
        mock_settings.return_value = MagicMock(
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        sender = DiscordSender()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)

            mock_request = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limited"
            mock_client.post.return_value = mock_response
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Rate limited", request=mock_request, response=mock_response
            )
            mock_client_cls.return_value = mock_client

            result = sender.send("Hello")

        assert result is False

    @patch("src.notifications.discord.get_settings")
    def test_send_request_error(self, mock_settings):
        mock_settings.return_value = MagicMock(
            discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        )
        sender = DiscordSender()

        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = httpx.RequestError("Timeout")
            mock_client_cls.return_value = mock_client

            result = sender.send("Hello")

        assert result is False
```

### Verification
```bash
pytest tests/test_notifications_telegram.py tests/test_notifications_discord.py -v
ruff check src/notifications/
```

---

## Task 3: Message Formatter + Dispatcher

### Files to create/modify
- Create `src/notifications/formatter.py`
- Create `src/notifications/dispatcher.py`
- Create `tests/test_notifications_formatter.py`
- Create `tests/test_notifications_dispatcher.py`

### Implementation

**`src/notifications/formatter.py`** -- New file:

```python
from __future__ import annotations

from typing import Any, Dict, List

from src.models import CreditCard, Promotion
from src.notifications.telegram import escape_markdown_v2

# Discord embed colors by notification type
COLOR_NEW_PROMOTION = 0x00CC66  # green
COLOR_EXPIRING_PROMOTION = 0xFF9900  # orange
COLOR_NEW_CARD = 0x3399FF  # blue


def format_new_promotions(promotions: List[Promotion]) -> Dict[str, Any]:
    """Format new promotions for all channels.

    Returns:
        dict with keys "telegram" (str) and "discord_embeds" (list).
    """
    if not promotions:
        return {"telegram": "", "discord_embeds": []}

    # Telegram MarkdownV2
    lines = [escape_markdown_v2("--- 新優惠通知 ---"), ""]
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        lines.append(
            f"*{escape_markdown_v2(promo.title)}*"
        )
        lines.append(
            f"{escape_markdown_v2(bank_name)} / {escape_markdown_v2(card_name)}"
        )
        if promo.reward_rate is not None:
            lines.append(
                f"{escape_markdown_v2('回饋率:')} {escape_markdown_v2(f'{promo.reward_rate}%')}"
            )
        if promo.end_date:
            lines.append(
                f"{escape_markdown_v2('截止日:')} {escape_markdown_v2(str(promo.end_date))}"
            )
        lines.append("")
    telegram_text = "\n".join(lines).strip()

    # Discord embeds
    discord_embeds = []
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        fields = [
            {"name": "Bank", "value": bank_name, "inline": True},
            {"name": "Card", "value": card_name, "inline": True},
        ]
        if promo.reward_rate is not None:
            fields.append(
                {"name": "Reward Rate", "value": f"{promo.reward_rate}%", "inline": True}
            )
        if promo.end_date:
            fields.append(
                {"name": "Expires", "value": str(promo.end_date), "inline": True}
            )
        if promo.description:
            fields.append(
                {"name": "Details", "value": promo.description[:200], "inline": False}
            )
        embed = {
            "title": promo.title,
            "color": COLOR_NEW_PROMOTION,
            "fields": fields,
            "footer": {"text": f"{bank_name} - {card_name}"},
        }
        discord_embeds.append(embed)

    return {"telegram": telegram_text, "discord_embeds": discord_embeds}


def format_expiring_promotions(promotions: List[Promotion]) -> Dict[str, Any]:
    """Format expiring promotions for all channels.

    Returns:
        dict with keys "telegram" (str) and "discord_embeds" (list).
    """
    if not promotions:
        return {"telegram": "", "discord_embeds": []}

    # Telegram MarkdownV2
    lines = [escape_markdown_v2("--- 即將到期優惠提醒 ---"), ""]
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        lines.append(
            f"*{escape_markdown_v2(promo.title)}*"
        )
        lines.append(
            f"{escape_markdown_v2(bank_name)} / {escape_markdown_v2(card_name)}"
        )
        if promo.end_date:
            lines.append(
                f"{escape_markdown_v2('到期日:')} {escape_markdown_v2(str(promo.end_date))}"
            )
        lines.append("")
    telegram_text = "\n".join(lines).strip()

    # Discord embeds
    discord_embeds = []
    for promo in promotions:
        card_name = promo.card.name if promo.card else "Unknown"
        bank_name = promo.card.bank.name if promo.card and promo.card.bank else "Unknown"
        fields = [
            {"name": "Bank", "value": bank_name, "inline": True},
            {"name": "Card", "value": card_name, "inline": True},
        ]
        if promo.end_date:
            fields.append(
                {"name": "Expires", "value": str(promo.end_date), "inline": True}
            )
        embed = {
            "title": f"[Expiring] {promo.title}",
            "color": COLOR_EXPIRING_PROMOTION,
            "fields": fields,
            "footer": {"text": f"{bank_name} - {card_name}"},
        }
        discord_embeds.append(embed)

    return {"telegram": telegram_text, "discord_embeds": discord_embeds}


def format_new_cards(cards: List[CreditCard]) -> Dict[str, Any]:
    """Format new credit cards for all channels.

    Returns:
        dict with keys "telegram" (str) and "discord_embeds" (list).
    """
    if not cards:
        return {"telegram": "", "discord_embeds": []}

    # Telegram MarkdownV2
    lines = [escape_markdown_v2("--- 新信用卡通知 ---"), ""]
    for card in cards:
        bank_name = card.bank.name if card.bank else "Unknown"
        lines.append(f"*{escape_markdown_v2(card.name)}*")
        lines.append(f"{escape_markdown_v2(bank_name)}")
        if card.card_type:
            lines.append(
                f"{escape_markdown_v2('卡別:')} {escape_markdown_v2(card.card_type)}"
            )
        if card.annual_fee is not None:
            fee_str = "免年費" if card.annual_fee == 0 else f"${card.annual_fee}"
            lines.append(
                f"{escape_markdown_v2('年費:')} {escape_markdown_v2(fee_str)}"
            )
        if card.base_reward_rate is not None:
            lines.append(
                f"{escape_markdown_v2('基本回饋:')} "
                f"{escape_markdown_v2(f'{card.base_reward_rate}%')}"
            )
        lines.append("")
    telegram_text = "\n".join(lines).strip()

    # Discord embeds
    discord_embeds = []
    for card in cards:
        bank_name = card.bank.name if card.bank else "Unknown"
        fields = [
            {"name": "Bank", "value": bank_name, "inline": True},
        ]
        if card.card_type:
            fields.append(
                {"name": "Card Type", "value": card.card_type, "inline": True}
            )
        if card.annual_fee is not None:
            fee_str = "Free" if card.annual_fee == 0 else f"${card.annual_fee}"
            fields.append(
                {"name": "Annual Fee", "value": fee_str, "inline": True}
            )
        if card.base_reward_rate is not None:
            fields.append(
                {"name": "Base Reward", "value": f"{card.base_reward_rate}%", "inline": True}
            )
        if card.annual_fee_waiver:
            fields.append(
                {"name": "Fee Waiver", "value": card.annual_fee_waiver, "inline": False}
            )
        embed = {
            "title": card.name,
            "color": COLOR_NEW_CARD,
            "fields": fields,
            "footer": {"text": bank_name},
        }
        if card.apply_url:
            embed["url"] = card.apply_url
        discord_embeds.append(embed)

    return {"telegram": telegram_text, "discord_embeds": discord_embeds}
```

**`src/notifications/dispatcher.py`** -- New file:

```python
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
```

**`tests/test_notifications_formatter.py`** -- New file:

```python
from unittest.mock import MagicMock

from src.notifications.formatter import (
    COLOR_EXPIRING_PROMOTION,
    COLOR_NEW_CARD,
    COLOR_NEW_PROMOTION,
    format_expiring_promotions,
    format_new_cards,
    format_new_promotions,
)


def _make_promotion(title, card_name, bank_name, reward_rate=None, end_date=None, description=None):
    """Create a mock Promotion with nested card/bank."""
    bank = MagicMock()
    bank.name = bank_name

    card = MagicMock()
    card.name = card_name
    card.bank = bank

    promo = MagicMock()
    promo.title = title
    promo.card = card
    promo.reward_rate = reward_rate
    promo.end_date = end_date
    promo.description = description
    promo.id = 1
    return promo


def _make_card(name, bank_name, card_type=None, annual_fee=None, base_reward_rate=None,
               annual_fee_waiver=None, apply_url=None):
    """Create a mock CreditCard with nested bank."""
    bank = MagicMock()
    bank.name = bank_name

    card = MagicMock()
    card.name = name
    card.bank = bank
    card.card_type = card_type
    card.annual_fee = annual_fee
    card.base_reward_rate = base_reward_rate
    card.annual_fee_waiver = annual_fee_waiver
    card.apply_url = apply_url
    card.id = 1
    return card


class TestFormatNewPromotions:
    def test_empty_list(self):
        result = format_new_promotions([])
        assert result["telegram"] == ""
        assert result["discord_embeds"] == []

    def test_single_promotion(self):
        promo = _make_promotion(
            title="網購 3% 回饋",
            card_name="LINE Pay 卡",
            bank_name="中國信託",
            reward_rate=3.0,
            end_date="2026-03-31",
        )
        result = format_new_promotions([promo])

        assert "新優惠通知" in result["telegram"]
        assert "LINE Pay" in result["telegram"]
        assert "3.0%" in result["telegram"]

        assert len(result["discord_embeds"]) == 1
        embed = result["discord_embeds"][0]
        assert embed["title"] == "網購 3% 回饋"
        assert embed["color"] == COLOR_NEW_PROMOTION
        assert any(f["value"] == "中國信託" for f in embed["fields"])

    def test_multiple_promotions(self):
        promos = [
            _make_promotion("Promo A", "Card A", "Bank A", reward_rate=2.0),
            _make_promotion("Promo B", "Card B", "Bank B", reward_rate=5.0),
        ]
        result = format_new_promotions(promos)

        assert "Promo A" in result["telegram"]
        assert "Promo B" in result["telegram"]
        assert len(result["discord_embeds"]) == 2


class TestFormatExpiringPromotions:
    def test_empty_list(self):
        result = format_expiring_promotions([])
        assert result["telegram"] == ""
        assert result["discord_embeds"] == []

    def test_single_expiring(self):
        promo = _make_promotion(
            title="即將到期優惠",
            card_name="Card X",
            bank_name="Bank X",
            end_date="2026-02-10",
        )
        result = format_expiring_promotions([promo])

        assert "即將到期" in result["telegram"]
        assert "2026-02-10" in result["telegram"]

        embed = result["discord_embeds"][0]
        assert embed["color"] == COLOR_EXPIRING_PROMOTION
        assert "[Expiring]" in embed["title"]


class TestFormatNewCards:
    def test_empty_list(self):
        result = format_new_cards([])
        assert result["telegram"] == ""
        assert result["discord_embeds"] == []

    def test_single_card(self):
        card = _make_card(
            name="Super Card",
            bank_name="Test Bank",
            card_type="御璽卡",
            annual_fee=0,
            base_reward_rate=1.5,
        )
        result = format_new_cards([card])

        assert "新信用卡通知" in result["telegram"]
        assert "Super Card" in result["telegram"]
        assert "免年費" in result["telegram"]
        assert "1.5%" in result["telegram"]

        embed = result["discord_embeds"][0]
        assert embed["title"] == "Super Card"
        assert embed["color"] == COLOR_NEW_CARD
        assert any(f["value"] == "Free" for f in embed["fields"])

    def test_card_with_annual_fee(self):
        card = _make_card(
            name="Premium Card",
            bank_name="Test Bank",
            annual_fee=2000,
        )
        result = format_new_cards([card])

        assert "$2000" in result["telegram"]

        embed = result["discord_embeds"][0]
        assert any(f["value"] == "$2000" for f in embed["fields"])

    def test_card_with_apply_url(self):
        card = _make_card(
            name="Card",
            bank_name="Bank",
            apply_url="https://example.com/apply",
        )
        result = format_new_cards([card])

        embed = result["discord_embeds"][0]
        assert embed["url"] == "https://example.com/apply"
```

**`tests/test_notifications_dispatcher.py`** -- New file:

```python
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models.notification_log import (
    NotificationChannel,
    NotificationLog,
    NotificationType,
)
from src.notifications.dispatcher import NotificationDispatcher


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


class TestNotificationDispatcher:
    @patch("src.notifications.dispatcher.get_settings")
    @patch("src.notifications.dispatcher.TelegramSender")
    @patch("src.notifications.dispatcher.DiscordSender")
    def test_dispatch_disabled(self, mock_discord, mock_telegram, mock_settings, db_session):
        mock_settings.return_value = MagicMock(notification_enabled=False)
        dispatcher = NotificationDispatcher(db_session)

        result = dispatcher.dispatch(
            NotificationType.new_promotion,
            [1, 2],
            {"telegram": "msg", "discord_embeds": [{"title": "t"}]},
        )
        assert result == {}

    @patch("src.notifications.dispatcher.get_settings")
    @patch("src.notifications.dispatcher.TelegramSender")
    def test_dispatch_telegram_success(self, mock_telegram_cls, mock_settings, db_session):
        mock_settings.return_value = MagicMock(notification_enabled=True)
        mock_telegram_cls.is_configured.return_value = True

        mock_sender = MagicMock()
        mock_sender.send.return_value = True
        mock_telegram_cls.return_value = mock_sender

        with patch("src.notifications.dispatcher.DiscordSender") as mock_discord_cls:
            mock_discord_cls.is_configured.return_value = False

            dispatcher = NotificationDispatcher(db_session)
            result = dispatcher.dispatch(
                NotificationType.new_promotion,
                [10, 20],
                {"telegram": "test message", "discord_embeds": []},
            )

        assert result["telegram"] == 2
        mock_sender.send.assert_called_once_with("test message")

        # Check logs were created
        logs = db_session.query(NotificationLog).all()
        assert len(logs) == 2
        assert all(log.channel == NotificationChannel.telegram for log in logs)

    @patch("src.notifications.dispatcher.get_settings")
    @patch("src.notifications.dispatcher.DiscordSender")
    def test_dispatch_discord_success(self, mock_discord_cls, mock_settings, db_session):
        mock_settings.return_value = MagicMock(notification_enabled=True)
        mock_discord_cls.is_configured.return_value = True

        mock_sender = MagicMock()
        mock_sender.send.return_value = True
        mock_discord_cls.return_value = mock_sender

        with patch("src.notifications.dispatcher.TelegramSender") as mock_telegram_cls:
            mock_telegram_cls.is_configured.return_value = False

            dispatcher = NotificationDispatcher(db_session)
            embeds = [{"title": "Promo 1"}, {"title": "Promo 2"}]
            result = dispatcher.dispatch(
                NotificationType.new_promotion,
                [10, 20],
                {"telegram": "", "discord_embeds": embeds},
            )

        assert result["discord"] == 2

    @patch("src.notifications.dispatcher.get_settings")
    @patch("src.notifications.dispatcher.TelegramSender")
    def test_dispatch_dedup_skips_already_sent(self, mock_telegram_cls, mock_settings, db_session):
        mock_settings.return_value = MagicMock(notification_enabled=True)
        mock_telegram_cls.is_configured.return_value = True

        # Pre-insert a log for reference_id=10
        existing_log = NotificationLog(
            notification_type=NotificationType.new_promotion,
            reference_id=10,
            channel=NotificationChannel.telegram,
        )
        db_session.add(existing_log)
        db_session.commit()

        mock_sender = MagicMock()
        mock_sender.send.return_value = True
        mock_telegram_cls.return_value = mock_sender

        with patch("src.notifications.dispatcher.DiscordSender") as mock_discord_cls:
            mock_discord_cls.is_configured.return_value = False

            dispatcher = NotificationDispatcher(db_session)
            result = dispatcher.dispatch(
                NotificationType.new_promotion,
                [10, 20],
                {"telegram": "test", "discord_embeds": []},
            )

        # Only 20 should be new (10 was already sent)
        assert result["telegram"] == 1

    @patch("src.notifications.dispatcher.get_settings")
    @patch("src.notifications.dispatcher.TelegramSender")
    def test_dispatch_all_already_sent(self, mock_telegram_cls, mock_settings, db_session):
        mock_settings.return_value = MagicMock(notification_enabled=True)
        mock_telegram_cls.is_configured.return_value = True

        # Pre-insert logs for both
        for ref_id in [10, 20]:
            db_session.add(
                NotificationLog(
                    notification_type=NotificationType.new_promotion,
                    reference_id=ref_id,
                    channel=NotificationChannel.telegram,
                )
            )
        db_session.commit()

        mock_sender = MagicMock()
        mock_telegram_cls.return_value = mock_sender

        with patch("src.notifications.dispatcher.DiscordSender") as mock_discord_cls:
            mock_discord_cls.is_configured.return_value = False

            dispatcher = NotificationDispatcher(db_session)
            result = dispatcher.dispatch(
                NotificationType.new_promotion,
                [10, 20],
                {"telegram": "test", "discord_embeds": []},
            )

        # Nothing new to send
        assert "telegram" not in result
        mock_sender.send.assert_not_called()

    @patch("src.notifications.dispatcher.get_settings")
    @patch("src.notifications.dispatcher.TelegramSender")
    def test_dispatch_send_failure_does_not_log(
        self, mock_telegram_cls, mock_settings, db_session
    ):
        mock_settings.return_value = MagicMock(notification_enabled=True)
        mock_telegram_cls.is_configured.return_value = True

        mock_sender = MagicMock()
        mock_sender.send.return_value = False  # Send failed
        mock_telegram_cls.return_value = mock_sender

        with patch("src.notifications.dispatcher.DiscordSender") as mock_discord_cls:
            mock_discord_cls.is_configured.return_value = False

            dispatcher = NotificationDispatcher(db_session)
            result = dispatcher.dispatch(
                NotificationType.new_promotion,
                [10],
                {"telegram": "test", "discord_embeds": []},
            )

        assert "telegram" not in result
        # No logs should be created on failure
        logs = db_session.query(NotificationLog).all()
        assert len(logs) == 0
```

### Verification
```bash
pytest tests/test_notifications_formatter.py tests/test_notifications_dispatcher.py -v
ruff check src/notifications/
```

---

## Task 4: Scheduler Integration

### Files to create/modify
- Modify `src/scheduler/jobs.py`
- Modify `src/scheduler/__init__.py`
- Create `tests/test_scheduler_notifications.py`

### Implementation

**`src/scheduler/jobs.py`** -- Modify existing:

```python
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload

from src.config import get_settings
from src.crawlers.banks import CtbcCrawler
from src.models import CreditCard, Promotion
from src.models.notification_log import NotificationType
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.formatter import (
    format_expiring_promotions,
    format_new_cards,
    format_new_promotions,
)

settings = get_settings()

# Sync database URL for scheduler (replace async driver)
sync_database_url = settings.database_url.replace("+aiosqlite", "")


def get_sync_session() -> Session:
    engine = create_engine(sync_database_url)
    return Session(engine)


def run_daily_promotion_crawl():
    """每日優惠爬取任務"""
    logger.info(f"Starting daily promotion crawl at {datetime.now()}")

    with get_sync_session() as session:
        crawlers = [
            CtbcCrawler(session),
            # 之後加入更多銀行爬蟲
        ]

        for crawler in crawlers:
            try:
                result = crawler.run()
                logger.info(f"Completed: {result}")
            except Exception as e:
                logger.error(f"Error crawling {crawler.bank_name}: {e}")

    logger.info("Daily promotion crawl completed")


def run_weekly_card_crawl():
    """每週信用卡資訊爬取任務"""
    logger.info(f"Starting weekly card crawl at {datetime.now()}")

    with get_sync_session() as session:
        crawlers = [
            CtbcCrawler(session),
        ]

        new_card_ids = []
        for crawler in crawlers:
            try:
                cards = crawler.fetch_cards()
                logger.info(f"Fetched {len(cards)} cards from {crawler.bank_name}")
                new_card_ids.extend(card.id for card in cards)
            except Exception as e:
                logger.error(f"Error crawling {crawler.bank_name}: {e}")

        # Notify about new cards
        if new_card_ids:
            try:
                _notify_new_cards(session, new_card_ids)
            except Exception as e:
                logger.error(f"Error sending new card notifications: {e}")

    logger.info("Weekly card crawl completed")


def cleanup_expired_promotions():
    """清理過期優惠"""
    logger.info("Cleaning up expired promotions")

    with get_sync_session() as session:
        today = datetime.now().date()
        expired = session.query(Promotion).filter(Promotion.end_date < today).all()

        for promo in expired:
            session.delete(promo)

        session.commit()
        logger.info(f"Deleted {len(expired)} expired promotions")


def check_new_promotions():
    """檢查今日新增優惠並發送通知"""
    logger.info("Checking for new promotions to notify")

    with get_sync_session() as session:
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        new_promos = (
            session.query(Promotion)
            .options(joinedload(Promotion.card).joinedload(CreditCard.bank))
            .filter(Promotion.created_at >= today_start, Promotion.created_at <= today_end)
            .all()
        )

        if not new_promos:
            logger.info("No new promotions found today")
            return

        logger.info(f"Found {len(new_promos)} new promotions today")

        message = format_new_promotions(new_promos)
        reference_ids = [promo.id for promo in new_promos]

        dispatcher = NotificationDispatcher(session)
        results = dispatcher.dispatch(
            NotificationType.new_promotion, reference_ids, message
        )
        logger.info(f"New promotion notification results: {results}")


def check_expiring_promotions():
    """檢查即將到期優惠（3天內）並發送通知"""
    logger.info("Checking for expiring promotions to notify")

    with get_sync_session() as session:
        today = datetime.now().date()
        expiry_threshold = today + timedelta(days=3)

        expiring_promos = (
            session.query(Promotion)
            .options(joinedload(Promotion.card).joinedload(CreditCard.bank))
            .filter(
                Promotion.end_date >= today,
                Promotion.end_date <= expiry_threshold,
            )
            .all()
        )

        if not expiring_promos:
            logger.info("No expiring promotions in the next 3 days")
            return

        logger.info(f"Found {len(expiring_promos)} promotions expiring within 3 days")

        message = format_expiring_promotions(expiring_promos)
        reference_ids = [promo.id for promo in expiring_promos]

        dispatcher = NotificationDispatcher(session)
        results = dispatcher.dispatch(
            NotificationType.expiring_promotion, reference_ids, message
        )
        logger.info(f"Expiring promotion notification results: {results}")


def _notify_new_cards(session: Session, card_ids: list[int]):
    """發送新信用卡通知（由 run_weekly_card_crawl 呼叫）"""
    cards = (
        session.query(CreditCard)
        .options(joinedload(CreditCard.bank))
        .filter(CreditCard.id.in_(card_ids))
        .all()
    )

    if not cards:
        return

    message = format_new_cards(cards)
    reference_ids = [card.id for card in cards]

    dispatcher = NotificationDispatcher(session)
    results = dispatcher.dispatch(
        NotificationType.new_card, reference_ids, message
    )
    logger.info(f"New card notification results: {results}")
```

**`src/scheduler/__init__.py`** -- Modify existing:

```python
"""Scheduler module for periodic crawling tasks.

Schedule overview:
  - 02:00 daily  - Promotion crawl
  - 04:00 daily  - Cleanup expired promotions
  - 06:00 daily  - Notify new promotions (after crawl)
  - 09:00 daily  - Notify expiring promotions
  - 03:00 Sunday - Card info crawl (includes new card notifications)
"""
```

Note: The actual APScheduler job registration depends on how the scheduler is wired in the FastAPI app. The new jobs to register are:

```python
# In wherever APScheduler is configured (e.g., src/main.py or a scheduler setup function):
from src.scheduler.jobs import (
    check_expiring_promotions,
    check_new_promotions,
    cleanup_expired_promotions,
    run_daily_promotion_crawl,
    run_weekly_card_crawl,
)

# Existing jobs
scheduler.add_job(run_daily_promotion_crawl, "cron", hour=2, minute=0)
scheduler.add_job(cleanup_expired_promotions, "cron", hour=4, minute=0)
scheduler.add_job(run_weekly_card_crawl, "cron", day_of_week="sun", hour=3, minute=0)

# New notification jobs
scheduler.add_job(check_new_promotions, "cron", hour=6, minute=0, id="check_new_promotions")
scheduler.add_job(check_expiring_promotions, "cron", hour=9, minute=0, id="check_expiring_promotions")
```

**`tests/test_scheduler_notifications.py`** -- New file:

```python
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models import Bank, CreditCard, Promotion
from src.models.notification_log import NotificationLog


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_data(db_session):
    """Create sample bank, card, and promotion data."""
    bank = Bank(name="Test Bank", code="test", website="https://test.com")
    db_session.add(bank)
    db_session.commit()

    card = CreditCard(
        bank_id=bank.id,
        name="Test Card",
        card_type="Visa",
        annual_fee=0,
        base_reward_rate=1.0,
    )
    db_session.add(card)
    db_session.commit()

    # A promotion created today
    promo_new = Promotion(
        card_id=card.id,
        title="New Promo Today",
        category="online_shopping",
        reward_type="cashback",
        reward_rate=3.0,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
    )

    # A promotion expiring in 2 days
    promo_expiring = Promotion(
        card_id=card.id,
        title="Expiring Soon",
        category="dining",
        reward_type="points",
        reward_rate=5.0,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=2),
    )

    db_session.add_all([promo_new, promo_expiring])
    db_session.commit()

    return {
        "bank": bank,
        "card": card,
        "promo_new": promo_new,
        "promo_expiring": promo_expiring,
    }


class TestCheckNewPromotions:
    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_notifies_new_promotions(
        self, mock_get_session, mock_dispatcher_cls, db_session, sample_data
    ):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"telegram": 1}
        mock_dispatcher_cls.return_value = mock_dispatcher

        from src.scheduler.jobs import check_new_promotions

        check_new_promotions()

        # Dispatcher should have been called (promotions were created today)
        mock_dispatcher.dispatch.assert_called_once()
        call_args = mock_dispatcher.dispatch.call_args
        from src.models.notification_log import NotificationType

        assert call_args.args[0] == NotificationType.new_promotion

    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_no_notification_when_no_new_promos(
        self, mock_get_session, mock_dispatcher_cls, db_session
    ):
        """No promotions created today -> no dispatch."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        from src.scheduler.jobs import check_new_promotions

        check_new_promotions()

        mock_dispatcher_cls.assert_not_called()


class TestCheckExpiringPromotions:
    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_notifies_expiring_promotions(
        self, mock_get_session, mock_dispatcher_cls, db_session, sample_data
    ):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"telegram": 1}
        mock_dispatcher_cls.return_value = mock_dispatcher

        from src.scheduler.jobs import check_expiring_promotions

        check_expiring_promotions()

        mock_dispatcher.dispatch.assert_called_once()
        call_args = mock_dispatcher.dispatch.call_args
        from src.models.notification_log import NotificationType

        assert call_args.args[0] == NotificationType.expiring_promotion

    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_no_notification_when_nothing_expiring(
        self, mock_get_session, mock_dispatcher_cls, db_session
    ):
        """No promotions expiring in 3 days -> no dispatch."""
        # Add a promotion expiring in 10 days (outside 3-day window)
        bank = Bank(name="Test", code="test")
        db_session.add(bank)
        db_session.commit()

        card = CreditCard(bank_id=bank.id, name="Card")
        db_session.add(card)
        db_session.commit()

        promo = Promotion(
            card_id=card.id,
            title="Far Future Promo",
            end_date=date.today() + timedelta(days=10),
        )
        db_session.add(promo)
        db_session.commit()

        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        from src.scheduler.jobs import check_expiring_promotions

        check_expiring_promotions()

        mock_dispatcher_cls.assert_not_called()
```

### Verification
```bash
pytest tests/test_scheduler_notifications.py -v
ruff check src/scheduler/jobs.py
pytest tests/ -v  # Run all tests to ensure nothing is broken
```
