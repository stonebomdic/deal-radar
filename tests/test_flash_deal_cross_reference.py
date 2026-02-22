from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models.flash_deal import FlashDeal
from src.models.price_history import PriceHistory
from src.models.tracked_product import TrackedProduct
from src.trackers.base import FlashDealResult
from src.trackers.utils import refresh_flash_deals


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_tracked(db, url="https://24h.pchome.com.tw/prod/DYAQD6", platform="pchome"):
    product = TrackedProduct(
        platform=platform, product_id="DYAQD6",
        name="Sony 耳機", url=url, is_active=True,
    )
    db.add(product)
    db.flush()
    return product


def test_flash_deal_match_creates_price_history(db):
    """新的 flash deal 命中追蹤商品時，應建立 PriceHistory(source='flash_deal')"""
    product = _make_tracked(db)

    mock_deal = FlashDealResult(
        platform="pchome",
        product_name="Sony 耳機",
        product_url=product.url,
        sale_price=5990,
        original_price=8490,
        discount_rate=0.706,
    )

    mock_tracker = MagicMock()
    mock_tracker.fetch_flash_deals.return_value = [mock_deal]

    with patch("src.trackers.utils.get_tracker", return_value=mock_tracker), \
         patch("src.trackers.utils.NotificationDispatcher"):
        refresh_flash_deals(db, "pchome")

    history = db.query(PriceHistory).filter_by(product_id=product.id).all()
    assert len(history) == 1
    assert history[0].price == 5990
    assert history[0].source == "flash_deal"


def test_flash_deal_no_match_no_price_history(db):
    """flash deal 商品 URL 與追蹤清單不符時，不應建立 PriceHistory"""
    _make_tracked(db, url="https://24h.pchome.com.tw/prod/OTHER")

    mock_deal = FlashDealResult(
        platform="pchome",
        product_name="別的商品",
        product_url="https://24h.pchome.com.tw/prod/DIFFERENT",
        sale_price=5990,
        original_price=8490,
        discount_rate=0.706,
    )
    mock_tracker = MagicMock()
    mock_tracker.fetch_flash_deals.return_value = [mock_deal]

    with patch("src.trackers.utils.get_tracker", return_value=mock_tracker):
        refresh_flash_deals(db, "pchome")

    assert db.query(PriceHistory).count() == 0


def test_flash_deal_triggers_notification_on_price_drop(db):
    """flash deal 價格低於上次紀錄時，應觸發 price_drop 通知"""
    product = _make_tracked(db)
    # 先建立一筆較高價的歷史
    prior = PriceHistory(product_id=product.id, price=7990, in_stock=True)
    db.add(prior)
    db.commit()

    mock_deal = FlashDealResult(
        platform="pchome",
        product_name="Sony 耳機",
        product_url=product.url,
        sale_price=5990,
        original_price=8490,
        discount_rate=0.706,
    )
    mock_tracker = MagicMock()
    mock_tracker.fetch_flash_deals.return_value = [mock_deal]

    mock_dispatcher = MagicMock()
    with patch("src.trackers.utils.get_tracker", return_value=mock_tracker), \
         patch("src.trackers.utils.NotificationDispatcher", return_value=mock_dispatcher):
        refresh_flash_deals(db, "pchome")

    assert mock_dispatcher.dispatch.called


def test_flash_deal_no_notification_when_price_same_or_higher(db):
    """flash deal 價格不低於上次紀錄時，不應觸發通知"""
    product = _make_tracked(db)
    prior = PriceHistory(product_id=product.id, price=5990, in_stock=True)
    db.add(prior)
    db.commit()

    mock_deal = FlashDealResult(
        platform="pchome",
        product_name="Sony 耳機",
        product_url=product.url,
        sale_price=6500,  # higher than 5990
        original_price=8490,
        discount_rate=0.765,
    )
    mock_tracker = MagicMock()
    mock_tracker.fetch_flash_deals.return_value = [mock_deal]

    mock_dispatcher = MagicMock()
    with patch("src.trackers.utils.get_tracker", return_value=mock_tracker), \
         patch("src.trackers.utils.NotificationDispatcher", return_value=mock_dispatcher):
        refresh_flash_deals(db, "pchome")

    mock_dispatcher.dispatch.assert_not_called()
