from unittest.mock import MagicMock, patch

import httpx

from src.notifications.telegram import TelegramSender, escape_markdown_v2


class TestEscapeMarkdownV2:
    def test_escape_special_chars(self):
        text = "Hello_World! Price: $100.00 (50% off)"
        escaped = escape_markdown_v2(text)
        assert escaped == r"Hello\_World\! Price: $100\.00 \(50% off\)"

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
        assert call_args.kwargs["json"]["chat_id"] == "456"
        assert call_args.kwargs["json"]["parse_mode"] == "MarkdownV2"

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
