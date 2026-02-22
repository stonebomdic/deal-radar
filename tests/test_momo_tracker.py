import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.trackers.platforms.momo import MomoTracker


def test_parse_price_from_text():
    from src.trackers.platforms.momo import _parse_price
    assert _parse_price("NT$6,990") == 6990
    assert _parse_price("6990元") == 6990
    assert _parse_price("無效") is None


def test_calculate_discount_rate():
    from src.trackers.platforms.momo import _calculate_discount_rate
    assert _calculate_discount_rate(6500, 8490) == pytest.approx(0.766, abs=0.001)
    assert _calculate_discount_rate(6500, 0) is None
