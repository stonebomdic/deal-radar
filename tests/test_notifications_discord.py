from unittest.mock import MagicMock, patch

import httpx

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
