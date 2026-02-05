from unittest.mock import MagicMock

from src.notifications.formatter import (
    COLOR_EXPIRING_PROMOTION,
    COLOR_NEW_CARD,
    COLOR_NEW_PROMOTION,
    format_expiring_promotions,
    format_new_cards,
    format_new_promotions,
)


def _make_promotion(
    title, card_name, bank_name, reward_rate=None, end_date=None, description=None
):
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


def _make_card(
    name,
    bank_name,
    card_type=None,
    annual_fee=None,
    base_reward_rate=None,
    annual_fee_waiver=None,
    apply_url=None,
):
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
        assert r"3\.0%" in result["telegram"]

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
        assert r"2026\-02\-10" in result["telegram"]

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
        assert r"1\.5%" in result["telegram"]

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
