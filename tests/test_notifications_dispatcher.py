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
    def test_dispatch_disabled(
        self, mock_discord, mock_telegram, mock_settings, db_session
    ):
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
    def test_dispatch_telegram_success(
        self, mock_telegram_cls, mock_settings, db_session
    ):
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
    def test_dispatch_discord_success(
        self, mock_discord_cls, mock_settings, db_session
    ):
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
    def test_dispatch_dedup_skips_already_sent(
        self, mock_telegram_cls, mock_settings, db_session
    ):
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
    def test_dispatch_all_already_sent(
        self, mock_telegram_cls, mock_settings, db_session
    ):
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
