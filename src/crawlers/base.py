from abc import ABC, abstractmethod
from typing import List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from src.models import Bank, CreditCard, Promotion


class BaseCrawler(ABC):
    bank_name: str
    bank_code: str
    base_url: str

    def __init__(self, db_session: Session):
        self.db = db_session
        self._bank: Optional[Bank] = None

    @property
    def bank(self) -> Bank:
        if self._bank is None:
            self._bank = self.db.query(Bank).filter_by(code=self.bank_code).first()
            if self._bank is None:
                self._bank = Bank(
                    name=self.bank_name,
                    code=self.bank_code,
                    website=self.base_url,
                )
                self.db.add(self._bank)
                self.db.commit()
        return self._bank

    @abstractmethod
    def fetch_cards(self) -> List[CreditCard]:
        """爬取所有信用卡資訊"""
        pass

    @abstractmethod
    def fetch_promotions(self) -> List[Promotion]:
        """爬取所有優惠活動"""
        pass

    def run(self) -> dict:
        """執行爬蟲"""
        logger.info(f"Starting crawler for {self.bank_name}")

        cards = self.fetch_cards()
        logger.info(f"Fetched {len(cards)} cards from {self.bank_name}")

        promotions = self.fetch_promotions()
        logger.info(f"Fetched {len(promotions)} promotions from {self.bank_name}")

        return {
            "bank": self.bank_name,
            "cards_count": len(cards),
            "promotions_count": len(promotions),
        }

    # 非卡片名稱的關鍵字（用於過濾爬蟲誤抓的資料）
    INVALID_CARD_NAME_KEYWORDS = [
        '總覽', '首頁', '介紹', '比較', '查詢', '瀏覽', '申辦',
        '信用卡列表', '卡片一覽', '全部卡片', '更多卡片',
        '信用卡推薦', '信用卡權益', '優惠活動', '最新消息',
        '權益說明', '回饋說明', '活動說明',
    ]

    def is_valid_card_name(self, name: str) -> bool:
        """驗證卡片名稱是否有效"""
        if not name or len(name) < 2 or len(name) > 50:
            return False
        return not any(kw in name for kw in self.INVALID_CARD_NAME_KEYWORDS)

    def save_card(self, card_data: dict) -> CreditCard:
        """儲存或更新信用卡"""
        name = card_data.get("name", "")
        if not self.is_valid_card_name(name):
            logger.warning(f"Skipping invalid card name: {name}")
            return None

        card = (
            self.db.query(CreditCard)
            .filter_by(bank_id=self.bank.id, name=card_data["name"])
            .first()
        )

        if card:
            for key, value in card_data.items():
                if key != "name":
                    setattr(card, key, value)
        else:
            card = CreditCard(bank_id=self.bank.id, **card_data)
            self.db.add(card)

        self.db.commit()
        return card

    def save_promotion(self, card: CreditCard, promo_data: dict) -> Promotion:
        """儲存或更新優惠活動"""
        promotion = (
            self.db.query(Promotion)
            .filter_by(card_id=card.id, title=promo_data["title"])
            .first()
        )

        if promotion:
            for key, value in promo_data.items():
                if key != "title":
                    setattr(promotion, key, value)
        else:
            promotion = Promotion(card_id=card.id, **promo_data)
            self.db.add(promotion)

        self.db.commit()
        return promotion
