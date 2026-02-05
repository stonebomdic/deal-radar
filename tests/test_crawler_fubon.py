import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.crawlers.banks.fubon import FubonCrawler
from src.db.database import Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_crawler_creates_bank(db_session):
    crawler = FubonCrawler(db_session)
    bank = crawler.bank
    assert bank.name == "富邦銀行"
    assert bank.code == "fubon"


def test_detect_card_type():
    crawler = FubonCrawler.__new__(FubonCrawler)
    assert crawler._detect_card_type("J 卡白金卡", "") == "白金卡"
    assert crawler._detect_card_type("momo 聯名卡", "") == "白金卡"


def test_extract_annual_fee():
    crawler = FubonCrawler.__new__(FubonCrawler)
    assert crawler._extract_annual_fee("年費：NT$2,000元") == 2000
    assert crawler._extract_annual_fee("免年費") == 0


def test_extract_reward_rate():
    crawler = FubonCrawler.__new__(FubonCrawler)
    assert crawler._extract_reward_rate("最高 3.5% 回饋") == 3.5
    assert crawler._extract_reward_rate("一般消費 1.2% 現金回饋") == 1.2


def test_detect_category():
    crawler = FubonCrawler.__new__(FubonCrawler)
    assert crawler._detect_category("餐飲優惠 8 折") == "dining"
    assert crawler._detect_category("網購滿千折百") == "online_shopping"
    assert crawler._detect_category("一般消費") == "others"
