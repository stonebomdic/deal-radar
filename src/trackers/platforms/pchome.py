from __future__ import annotations

from typing import List, Optional

import httpx
from loguru import logger

from src.trackers.base import BaseTracker, FlashDealResult, PriceSnapshot, ProductResult

SEARCH_URL = "https://ecshweb.pchome.com.tw/search/v3.3/"
PRODUCT_URL = "https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{product_id}"
FLASH_DEALS_URL = (
    "https://ecapi.pchome.com.tw/ecshop/prodapi/v2/store/DSAA31/prod"
    "?fields=Id,Name,Price,Pic&limit=50"
)
BASE_PRODUCT_URL = "https://24h.pchome.com.tw/prod/{product_id}"


class PChomeTracker(BaseTracker):
    platform = "pchome"

    def __init__(self):
        self.client = httpx.Client(timeout=10, headers={"User-Agent": "Mozilla/5.0"})

    def search_products(self, keyword: str) -> List[ProductResult]:
        try:
            resp = self.client.get(
                SEARCH_URL, params={"q": keyword, "page": 1, "sort": "rnk/dc"}
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"PChome search failed: {e}")
            return []

        results = []
        for prod in data.get("prods", []):
            price_data = prod.get("Price", {})
            product_id = prod.get("Id", "")
            results.append(
                ProductResult(
                    platform=self.platform,
                    product_id=product_id,
                    name=prod.get("Name", ""),
                    url=BASE_PRODUCT_URL.format(product_id=product_id),
                    price=price_data.get("M", 0),
                    original_price=price_data.get("P"),
                )
            )
        return results

    def fetch_product_by_url(self, url: str) -> Optional[ProductResult]:
        product_id = url.rstrip("/").split("/")[-1]
        snapshot = self.fetch_price(product_id)
        if snapshot is None:
            return None
        return ProductResult(
            platform=self.platform,
            product_id=product_id,
            name="",
            url=url,
            price=snapshot.price,
            original_price=snapshot.original_price,
        )

    def fetch_price(self, product_id: str) -> Optional[PriceSnapshot]:
        try:
            resp = self.client.get(PRODUCT_URL.format(product_id=product_id))
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"PChome fetch_price failed for {product_id}: {e}")
            return None

        price_data = data.get("Price", {})
        return PriceSnapshot(
            price=price_data.get("M", 0),
            original_price=price_data.get("P"),
            in_stock=bool(data.get("Stock", True)),
        )

    def fetch_flash_deals(self) -> List[FlashDealResult]:
        try:
            resp = self.client.get(FLASH_DEALS_URL)
            resp.raise_for_status()
            items = resp.json()
        except Exception as e:
            logger.error(f"PChome fetch_flash_deals failed: {e}")
            return []

        results = []
        for item in items:
            price_data = item.get("Price", {})
            sale_price = price_data.get("M", 0)
            original_price = price_data.get("P")
            discount_rate = (
                round(sale_price / original_price, 3)
                if original_price and original_price > 0
                else None
            )
            product_id = item.get("Id", "")
            results.append(
                FlashDealResult(
                    platform=self.platform,
                    product_name=item.get("Name", ""),
                    product_url=BASE_PRODUCT_URL.format(product_id=product_id),
                    sale_price=sale_price,
                    original_price=original_price,
                    discount_rate=discount_rate,
                )
            )
        return results
