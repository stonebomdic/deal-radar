import pytest

from src.trackers.base import BaseTracker, PriceSnapshot, ProductResult


def test_product_result_dataclass():
    result = ProductResult(
        platform="pchome",
        product_id="DYAQD6",
        name="Sony WH-1000XM5",
        url="https://24h.pchome.com.tw/prod/DYAQD6",
        price=6990,
    )
    assert result.platform == "pchome"
    assert result.price == 6990


def test_price_snapshot_dataclass():
    snapshot = PriceSnapshot(price=6990, original_price=8490, in_stock=True)
    assert snapshot.price == 6990
    assert snapshot.in_stock is True


def test_base_tracker_is_abstract():
    with pytest.raises(TypeError):
        BaseTracker()
