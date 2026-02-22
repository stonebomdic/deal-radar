from unittest.mock import MagicMock

import pytest

from src.models.card import CreditCard
from src.models.promotion import Promotion
from src.recommender.scoring import calculate_shopping_reward


def _make_card(base_rate=1.0, annual_fee=0):
    card = MagicMock(spec=CreditCard)
    card.id = 1
    card.name = "測試卡"
    card.base_reward_rate = base_rate
    card.annual_fee = annual_fee
    card.features = {"online_shopping": True}
    return card


def _make_promo(category="online_shopping", rate=3.0, limit=None):
    promo = MagicMock(spec=Promotion)
    promo.category = category
    promo.reward_rate = rate
    promo.reward_limit = limit
    return promo


def test_shopping_reward_basic():
    card = _make_card(base_rate=1.0)
    promotions = [_make_promo(category="online_shopping", rate=3.0)]
    result = calculate_shopping_reward(card, "pchome", 6990, promotions)
    # 6990 * 3% = 209.7
    assert result["reward_amount"] == pytest.approx(209.7, abs=1)
    assert result["best_rate"] == pytest.approx(3.0)


def test_shopping_reward_with_limit():
    card = _make_card(base_rate=1.0)
    promotions = [_make_promo(category="online_shopping", rate=5.0, limit=100)]
    result = calculate_shopping_reward(card, "pchome", 6990, promotions)
    # 上限 100 元
    assert result["reward_amount"] == pytest.approx(100.0)


def test_shopping_reward_no_promo_uses_base_rate():
    card = _make_card(base_rate=2.0)
    result = calculate_shopping_reward(card, "momo", 5000, [])
    # 5000 * 2% = 100
    assert result["reward_amount"] == pytest.approx(100.0)
