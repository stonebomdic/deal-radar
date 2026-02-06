import json
import re
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from src.crawlers.base import BaseCrawler
from src.crawlers.utils import (
    clean_text,
    detect_promotion_category,
    extract_promotions_from_text,
)
from src.models import CreditCard, Promotion


# CTBC 信用卡 JSON API
CTBC_CARDS_API = "https://www.ctbcbank.com/web/content/twrbo/setting/creditcards.cardlist.json"


class CtbcCrawler(BaseCrawler):
    bank_name = "中國信託"
    bank_code = "ctbc"
    base_url = "https://www.ctbcbank.com"

    def __init__(self, db_session):
        super().__init__(db_session)
        self._browser = None
        self._page = None
        self._playwright = None

    def _init_browser(self):
        """初始化 Playwright 瀏覽器（帶 Stealth 模式）"""
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )
            context = self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="zh-TW",
            )
            self._page = context.new_page()
            stealth = Stealth()
            stealth.apply_stealth_sync(self._page)
        return self._page

    def _close_browser(self):
        """關閉瀏覽器"""
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def run(self) -> dict:
        """執行爬蟲（覆寫基類方法以管理瀏覽器生命週期）"""
        logger.info(f"Starting crawler for {self.bank_name}")

        try:
            self._init_browser()

            # 從 JSON API 擷取所有卡片
            cards = self._fetch_cards_from_api()
            logger.info(f"Fetched {len(cards)} cards from {self.bank_name}")

            # 擷取優惠（從各卡片的詳情頁）
            promotions = self._fetch_promotions_for_cards(cards[:10])  # 限制前 10 張以節省時間
            logger.info(f"Fetched {len(promotions)} promotions from {self.bank_name}")

            return {
                "bank": self.bank_name,
                "cards_count": len(cards),
                "promotions_count": len(promotions),
            }
        finally:
            self._close_browser()

    def _fetch_cards_from_api(self) -> List[CreditCard]:
        """從官方 JSON API 擷取所有信用卡資訊"""
        import time

        cards = []
        page = self._page

        logger.info(f"Fetching cards from API: {CTBC_CARDS_API}")
        page.goto(CTBC_CARDS_API, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        json_text = page.evaluate("() => document.body.innerText")

        try:
            data = json.loads(json_text)
            card_list = data.get("creditCards", [])
            logger.info(f"Found {len(card_list)} cards in API response")

            for card_json in card_list:
                # 跳過已停止申辦的卡片
                features = card_json.get("cardFeature", [])
                if features and "停止申辦" in features[0]:
                    logger.debug(f"Skipping discontinued card: {card_json.get('cardName')}")
                    continue

                card_data = self._parse_card_json(card_json)
                if card_data:
                    card = self.save_card(card_data)
                    if card:  # 過濾掉無效卡片
                        cards.append(card)
                        logger.info(f"Saved card: {card_data['name']}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON API response: {e}")

        return cards

    def _parse_card_json(self, card_json: dict) -> Optional[dict]:
        """解析單張卡片的 JSON 資料"""
        name = card_json.get("cardName", "")
        if not name:
            return None

        # 解析卡片等級
        card_levels = card_json.get("cardLevel", [])
        card_type = self._parse_card_level(card_levels)

        # 解析特色
        features = {
            "card_types": card_json.get("cardType", []),
            "reward_types": card_json.get("rewardType", []),
            "extra_functions": card_json.get("extraFunction", []),
            "highlights": card_json.get("cardFeature", []),
        }

        # 解析回饋率
        reward_rate = self._extract_reward_rate_from_features(features.get("highlights", []))

        # 解析年費
        annual_fee_text = card_json.get("annualFee", "")
        annual_fee = self._parse_annual_fee(annual_fee_text)
        annual_fee_waiver = self._parse_annual_fee_waiver(annual_fee_text)

        # 圖片 URL
        images = card_json.get("cardImg", [])
        image_url = f"{self.base_url}{images[0]}" if images else None

        # 詳情頁 URL
        intro_link = card_json.get("introLink", "")
        apply_url = f"{self.base_url}{intro_link}" if intro_link else None

        return {
            "name": name,
            "card_type": card_type,
            "annual_fee": annual_fee,
            "annual_fee_waiver": annual_fee_waiver,
            "base_reward_rate": reward_rate,
            "image_url": image_url,
            "apply_url": apply_url,
            "features": features,
        }

    def _parse_card_level(self, levels: List[str]) -> str:
        """從卡片等級列表解析主要等級"""
        level_priority = {
            "無限/世界/極致卡": "無限卡",
            "御璽/鈦金/晶緻卡": "御璽卡",
            "白金卡": "白金卡",
            "金卡": "金卡",
            "普卡": "普卡",
        }
        for level_key, level_value in level_priority.items():
            if any(level_key in l for l in levels):
                return level_value
        return "白金卡"

    def _extract_reward_rate_from_features(self, features: List[str]) -> float:
        """從特色列表中擷取回饋率"""
        max_rate = 0.0
        for feature in features:
            # 尋找百分比
            matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", feature)
            for match in matches:
                try:
                    rate = float(match)
                    if rate > max_rate and rate <= 30:
                        max_rate = rate
                except ValueError:
                    pass
        return max_rate if max_rate > 0 else 1.0

    def _parse_annual_fee(self, text: str) -> int:
        """從年費文字中解析年費金額"""
        if not text:
            return 0

        # 移除 HTML 標籤
        clean_text = re.sub(r"<[^>]+>", " ", text)

        # 尋找年費金額
        patterns = [
            r"NT\$?([\d,]+)\s*元",
            r"年費[：:]\s*(?:正卡)?(?:新臺幣|NT\$?)?\s*([\d,]+)",
            r"([\d,]+)\s*元",
        ]

        for pattern in patterns:
            match = re.search(pattern, clean_text)
            if match:
                fee = match.group(1).replace(",", "")
                try:
                    return int(fee)
                except ValueError:
                    pass

        if "免年費" in clean_text or "首年免" in clean_text:
            return 0

        return 0

    def _parse_annual_fee_waiver(self, text: str) -> Optional[str]:
        """從年費文字中解析減免條件"""
        if not text:
            return None

        clean_text = re.sub(r"<[^>]+>", " ", text)

        if "首年免年費" in clean_text or "首年免" in clean_text:
            return "首年免年費"
        if "免年費" in clean_text:
            return "免年費"
        if "消費滿" in clean_text and "免" in clean_text:
            return "消費滿額免年費"
        return None

    def _fetch_promotions_for_cards(self, cards: List[CreditCard]) -> List[Promotion]:
        """為指定卡片擷取優惠活動"""
        import time

        promotions = []
        page = self._page

        for card in cards:
            if not card or not card.apply_url:
                continue

            try:
                logger.debug(f"Fetching promotions for: {card.name}")
                page.goto(card.apply_url, wait_until="networkidle", timeout=30000)
                time.sleep(2)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # 移除導航、頁尾等雜訊元素
                for tag in soup.find_all(["nav", "footer", "header", "script", "style"]):
                    tag.decompose()

                # 取得清理後的文字
                body_text = clean_text(soup.get_text())

                # 使用共用工具擷取優惠
                extracted = extract_promotions_from_text(body_text, max_count=3)

                for promo_info in extracted:
                    promo_data = {
                        "title": promo_info["title"],
                        "description": promo_info["description"],
                        "source_url": card.apply_url,
                        "category": detect_promotion_category(promo_info["title"]),
                        "reward_rate": promo_info.get("reward_rate"),
                    }
                    promo = self.save_promotion(card, promo_data)
                    if promo:
                        promotions.append(promo)
                        logger.debug(f"Saved promotion: {promo_info['title']}")

            except Exception as e:
                logger.warning(f"Error fetching promotions for {card.name}: {e}")

        return promotions

    def fetch_cards(self) -> List[CreditCard]:
        """擷取卡片（實作抽象方法）"""
        return self._fetch_cards_from_api()

    def fetch_promotions(self) -> List[Promotion]:
        """擷取優惠活動（實作抽象方法）"""
        cards = self.db.query(CreditCard).filter_by(bank_id=self.bank.id).limit(10).all()
        return self._fetch_promotions_for_cards(cards)

