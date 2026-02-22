import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models.tracked_product import TrackedProduct
from src.models.price_history import PriceHistory
from src.models.flash_deal import FlashDeal


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_create_tracked_product(db):
    product = TrackedProduct(
        platform="pchome",
        product_id="DYAQD6",
        name="Sony WH-1000XM5",
        url="https://24h.pchome.com.tw/prod/DYAQD6",
        target_price=6000,
        is_active=True,
    )
    db.add(product)
    db.commit()
    assert product.id is not None
    assert product.platform == "pchome"


def test_create_price_history(db):
    product = TrackedProduct(
        platform="pchome", product_id="DYAQD6",
        name="Sony WH-1000XM5", url="https://24h.pchome.com.tw/prod/DYAQD6",
    )
    db.add(product)
    db.flush()

    snapshot = PriceHistory(
        product_id=product.id,
        price=6990,
        original_price=8490,
        in_stock=True,
    )
    db.add(snapshot)
    db.commit()
    assert snapshot.id is not None
    assert snapshot.price == 6990


def test_create_flash_deal(db):
    deal = FlashDeal(
        platform="momo",
        product_name="AirPods Pro 2",
        product_url="https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code=12345",
        sale_price=6500,
        original_price=8490,
        discount_rate=0.765,
    )
    db.add(deal)
    db.commit()
    assert deal.id is not None
    assert deal.discount_rate == pytest.approx(0.765)
