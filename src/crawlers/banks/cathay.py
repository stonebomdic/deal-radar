import re
import time
from typing import List, Optional, Tuple

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

# 國泰世華信用卡介紹頁
CATHAY_CARDS_URL = "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"


class CathayCrawler(BaseCrawler):
    bank_name = "國泰世華"
    bank_code = "cathay"
    base_url = "https://www.cathaybk.com.tw"

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
        """執行爬蟲"""
        logger.info(f"Starting crawler for {self.bank_name}")

        try:
            self._init_browser()

            card_links = self._fetch_card_links()
            logger.info(f"Found {len(card_links)} card links")

            cards = []
            promotions = []

            for i, link in enumerate(card_links):
                try:
                    card_data, promos = self._fetch_card_detail(link)
                    if card_data:
                        card = self.save_card(card_data)
                        cards.append(card)
                        logger.info(f"[{i+1}/{len(card_links)}] Saved card: {card_data['name']}")

                        for promo_data in promos:
                            promo = self.save_promotion(card, promo_data)
                            promotions.append(promo)
                except Exception as e:
                    logger.warning(f"Error fetching card from {link['url']}: {e}")

            logger.info(f"Fetched {len(cards)} cards from {self.bank_name}")
            logger.info(f"Fetched {len(promotions)} promotions from {self.bank_name}")

            return {
                "bank": self.bank_name,
                "cards_count": len(cards),
                "promotions_count": len(promotions),
            }
        finally:
            self._close_browser()

    def _fetch_card_links(self) -> List[dict]:
        """從信用卡介紹頁面擷取所有卡片連結"""
        page = self._page
        card_links = []

        logger.info(f"Fetching card links from: {CATHAY_CARDS_URL}")
        page.goto(CATHAY_CARDS_URL, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        # 滾動頁面載入所有卡片
        for i in range(10):
            page.evaluate(f"window.scrollTo(0, {i * 1000})")
            time.sleep(0.3)

        time.sleep(2)

        # 擷取所有卡片連結
        links = page.evaluate("""
            () => {
                const cards = [];
                const seen = new Set();

                document.querySelectorAll('a[href*="credit-card/cards/"]').forEach(a => {
                    const href = a.href;
                    const text = a.innerText.trim();

                    if (href.includes('/cards/') &&
                        !href.endsWith('/cards/') &&
                        !href.endsWith('/cards') &&
                        !seen.has(href)) {

                        seen.add(href);

                        const img = a.querySelector('img');
                        const imgSrc = img ? (img.src || img.dataset.src) : null;

                        const nameEl = a.querySelector('h3, h4, .card-name, [class*="title"]');
                        let name = nameEl ? nameEl.innerText.trim() : text.split('\\n')[0].trim();

                        if (name && name.length > 2 && name.length < 50) {
                            cards.push({
                                name: name,
                                url: href,
                                image: imgSrc
                            });
                        }
                    }
                });

                return cards;
            }
        """)

        for link in links:
            name = link.get('name', '')
            url = link.get('url', '')

            if 'debit-card' in url or 'corporate-card' in url:
                continue
            if '簽帳金融卡' in name or '企業卡' in name:
                continue

            card_links.append(link)

        return card_links

    def _fetch_card_detail(self, link: dict) -> Tuple[Optional[dict], List[dict]]:
        """從卡片詳情頁擷取資訊"""
        page = self._page
        url = link.get('url', '')

        if not url:
            return None, []

        logger.debug(f"Fetching card detail: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        html = page.content()
        soup = BeautifulSoup(html, "lxml")
        body_text = " ".join(soup.get_text().split())

        h1 = soup.find("h1")
        name = h1.get_text().strip() if h1 else link.get('name', '')

        if not name:
            return None, []

        card_type = self._detect_card_type(name, url)
        annual_fee = self._extract_annual_fee(body_text)
        annual_fee_waiver = self._extract_annual_fee_waiver(body_text)
        reward_rate = self._extract_reward_rate(body_text)

        image_url = link.get('image')
        if not image_url:
            card_img = soup.select_one("img[src*='card'], img[src*='Card']")
            if card_img:
                src = card_img.get('src', '')
                image_url = f"{self.base_url}{src}" if src.startswith('/') else src

        features = self._extract_features(body_text, name)

        card_data = {
            "name": name,
            "card_type": card_type,
            "annual_fee": annual_fee,
            "annual_fee_waiver": annual_fee_waiver,
            "base_reward_rate": reward_rate,
            "image_url": image_url,
            "apply_url": url,
            "features": features,
        }

        promotions = self._extract_promotions(body_text, url)

        return card_data, promotions

    def _detect_card_type(self, name: str, url: str) -> str:
        """根據卡名和 URL 判斷卡片等級"""
        name_lower = name.lower()
        url_lower = url.lower()

        if '無限卡' in name or 'infinite' in name_lower or 'infinite' in url_lower:
            return "無限卡"
        if '世界卡' in name or 'world' in url_lower:
            return "世界卡"
        if '御璽' in name or 'signature' in url_lower:
            return "御璽卡"
        if '晶緻' in name or 'precious' in url_lower:
            return "晶緻卡"
        if '鈦金' in name or 'titanium' in url_lower:
            return "鈦金卡"
        if '白金' in name or 'platinum' in url_lower:
            return "白金卡"
        if '金卡' in name or 'gold' in url_lower:
            return "金卡"

        return "白金卡"

    def _extract_annual_fee(self, text: str) -> int:
        """從頁面文字擷取年費"""
        patterns = [
            r"年費[：:]\s*(?:新臺幣|NT\$?)?\s*([\d,]+)\s*元",
            r"年費\s*(?:新臺幣|NT\$?)?\s*([\d,]+)",
            r"([\d,]+)\s*元[^。]*年費",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                fee = match.group(1).replace(",", "")
                try:
                    return int(fee)
                except ValueError:
                    pass

        if "免年費" in text or "年費減免" in text or "首年免" in text:
            return 0

        return 0

    def _extract_annual_fee_waiver(self, text: str) -> Optional[str]:
        """擷取年費減免條件"""
        if "首年免年費" in text or "首年免" in text:
            return "首年免年費"
        if "免年費" in text:
            return "免年費"
        if "消費滿" in text and "免" in text:
            return "消費滿額免年費"
        if "年費減免" in text:
            return "年費減免"
        return None

    def _extract_reward_rate(self, text: str) -> float:
        """擷取基本回饋率"""
        patterns = [
            r"最高[^\d]*([\d.]+)\s*%",
            r"([\d.]+)\s*%\s*(?:回饋|現金回饋|刷卡金)",
            r"國內[^\d]*([\d.]+)\s*%",
            r"一般消費[^\d]*([\d.]+)\s*%",
        ]

        max_rate = 0.0
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    rate = float(match)
                    if rate > max_rate and rate <= 30:
                        max_rate = rate
                except ValueError:
                    pass

        return max_rate if max_rate > 0 else 1.0

    def _extract_features(self, text: str, card_name: str) -> dict:
        """擷取卡片特色"""
        features = {}

        if any(kw in text for kw in ["行動支付", "Apple Pay", "Google Pay", "Samsung Pay"]):
            features["mobile_pay"] = True

        if "網購" in text or "線上消費" in text:
            features["online_shopping"] = True

        if "國外" in text or "海外" in text:
            features["overseas"] = True

        if "機場接送" in text:
            features["airport_transfer"] = True
        if "貴賓室" in text:
            features["lounge"] = True

        if "旅遊" in text and "保險" in text:
            features["travel_insurance"] = True

        if "哩程" in text or "里程" in text:
            features["mileage"] = True

        # Cathay-specific
        if "CUBE" in card_name:
            features["rewards"] = "CUBE 點數回饋"
        elif "Costco" in card_name:
            features["rewards"] = "Costco 聯名回饋"

        return features

    def _extract_promotions(self, text: str, url: str) -> List[dict]:
        """擷取優惠活動"""
        # 使用共用工具擷取並清理優惠
        text = clean_text(text)
        extracted = extract_promotions_from_text(text, max_count=3)

        promotions = []
        for promo_info in extracted:
            promotions.append({
                "title": promo_info["title"],
                "description": promo_info["description"],
                "source_url": url,
                "category": detect_promotion_category(promo_info["title"]),
                "reward_rate": promo_info.get("reward_rate"),
            })

        return promotions

    def fetch_cards(self) -> List[CreditCard]:
        """擷取卡片（實作抽象方法）"""
        card_links = self._fetch_card_links()
        cards = []
        for link in card_links:
            try:
                card_data, _ = self._fetch_card_detail(link)
                if card_data:
                    card = self.save_card(card_data)
                    cards.append(card)
            except Exception as e:
                logger.warning(f"Error fetching card: {e}")
        return cards

    def fetch_promotions(self) -> List[Promotion]:
        """擷取優惠活動（實作抽象方法）"""
        cards = self.db.query(CreditCard).filter_by(bank_id=self.bank.id).all()
        promotions = []
        for card in cards:
            if card.apply_url:
                try:
                    _, promos = self._fetch_card_detail({"url": card.apply_url, "name": card.name})
                    for promo_data in promos:
                        promo = self.save_promotion(card, promo_data)
                        promotions.append(promo)
                except Exception as e:
                    logger.warning(f"Error fetching promotions for {card.name}: {e}")
        return promotions
