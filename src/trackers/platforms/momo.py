from __future__ import annotations

import re
from typing import List, Optional

from loguru import logger
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from src.trackers.base import BaseTracker, FlashDealResult, PriceSnapshot, ProductResult

SEARCH_URL = "https://www.momoshop.com.tw/search/searchShop.jsp?keyword={keyword}"
FLASH_DEALS_URL = "https://www.momoshop.com.tw/category/LgrpCategory.jsp?l_code=fl"


def _parse_price(text: str) -> Optional[int]:
    """從文字中萃取數字價格"""
    cleaned = text.replace(",", "").replace("NT$", "").replace("元", "")
    match = re.search(r"\d+", cleaned)
    if match:
        try:
            return int(match.group())
        except ValueError:
            return None
    return None


def _calculate_discount_rate(sale: int, original: int) -> Optional[float]:
    if not original or original <= 0:
        return None
    return round(sale / original, 3)


class MomoTracker(BaseTracker):
    platform = "momo"

    def _get_browser_page(self, playwright):
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        return browser, page

    def search_products(self, keyword: str) -> List[ProductResult]:
        results = []
        try:
            with sync_playwright() as p:
                browser, page = self._get_browser_page(p)
                page.goto(SEARCH_URL.format(keyword=keyword), timeout=30000)
                page.wait_for_selector(".prdListArea", timeout=15000)

                items = page.query_selector_all(".prdListArea .li_column")
                for item in items[:10]:
                    name_el = item.query_selector(".prdName")
                    price_el = item.query_selector(".price b")
                    url_el = item.query_selector("a")

                    if not name_el or not price_el or not url_el:
                        continue

                    name = name_el.inner_text().strip()
                    price = _parse_price(price_el.inner_text()) or 0
                    url = url_el.get_attribute("href") or ""
                    if url.startswith("/"):
                        url = "https://www.momoshop.com.tw" + url

                    m = re.search(r"i_code=(\d+)", url)
                    product_id = m.group(1) if m else url

                    results.append(
                        ProductResult(
                            platform=self.platform,
                            product_id=product_id,
                            name=name,
                            url=url,
                            price=price,
                        )
                    )
                browser.close()
        except Exception as e:
            logger.error(f"Momo search failed: {e}")
        return results

    def fetch_product_by_url(self, url: str) -> Optional[ProductResult]:
        snapshot = self.fetch_price(url)
        if snapshot is None:
            return None
        m = re.search(r"i_code=(\d+)", url)
        product_id = m.group(1) if m else url
        return ProductResult(
            platform=self.platform,
            product_id=product_id,
            name="",
            url=url,
            price=snapshot.price,
            original_price=snapshot.original_price,
        )

    def fetch_price(self, product_id: str) -> Optional[PriceSnapshot]:
        url = (
            product_id
            if product_id.startswith("http")
            else f"https://www.momoshop.com.tw/goods/GoodsDetail.jsp?i_code={product_id}"
        )
        try:
            with sync_playwright() as p:
                browser, page = self._get_browser_page(p)
                page.goto(url, timeout=30000)
                page.wait_for_selector(".goodsPrice", timeout=15000)

                price_el = page.query_selector(".goodsPrice .price b")
                orig_el = page.query_selector(".goodsPrice .originalPrice")
                stock_el = page.query_selector(".addBtnArea")

                price = _parse_price(price_el.inner_text()) if price_el else None
                original_price = _parse_price(orig_el.inner_text()) if orig_el else None
                in_stock = stock_el is not None

                browser.close()

                if price is None:
                    return None
                return PriceSnapshot(
                    price=price, original_price=original_price, in_stock=in_stock
                )
        except Exception as e:
            logger.error(f"Momo fetch_price failed for {product_id}: {e}")
            return None

    def fetch_flash_deals(self) -> List[FlashDealResult]:
        results = []
        try:
            with sync_playwright() as p:
                browser, page = self._get_browser_page(p)
                page.goto(FLASH_DEALS_URL, timeout=30000)
                page.wait_for_selector(".prdListArea", timeout=15000)

                items = page.query_selector_all(".prdListArea .li_column")
                for item in items[:30]:
                    name_el = item.query_selector(".prdName")
                    sale_el = item.query_selector(".price b")
                    orig_el = item.query_selector(".originalPrice")
                    url_el = item.query_selector("a")

                    if not name_el or not sale_el or not url_el:
                        continue

                    name = name_el.inner_text().strip()
                    sale_price = _parse_price(sale_el.inner_text()) or 0
                    original_price = _parse_price(orig_el.inner_text()) if orig_el else None
                    discount_rate = _calculate_discount_rate(sale_price, original_price or 0)

                    url = url_el.get_attribute("href") or ""
                    if url.startswith("/"):
                        url = "https://www.momoshop.com.tw" + url

                    results.append(
                        FlashDealResult(
                            platform=self.platform,
                            product_name=name,
                            product_url=url,
                            sale_price=sale_price,
                            original_price=original_price,
                            discount_rate=discount_rate,
                        )
                    )
                browser.close()
        except Exception as e:
            logger.error(f"Momo fetch_flash_deals failed: {e}")
        return results
