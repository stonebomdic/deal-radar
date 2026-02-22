from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProductResult:
    platform: str
    product_id: str
    name: str
    url: str
    price: int
    original_price: Optional[int] = None
    image_url: Optional[str] = None


@dataclass
class PriceSnapshot:
    price: int
    in_stock: bool = True
    original_price: Optional[int] = None


@dataclass
class FlashDealResult:
    platform: str
    product_name: str
    product_url: str
    sale_price: int
    original_price: Optional[int] = None
    discount_rate: Optional[float] = None
    image_url: Optional[str] = None


class BaseTracker(ABC):
    platform: str = ""

    @abstractmethod
    def search_products(self, keyword: str) -> List[ProductResult]:
        """以關鍵字搜尋商品，回傳候選清單"""
        ...

    @abstractmethod
    def fetch_product_by_url(self, url: str) -> Optional[ProductResult]:
        """從 URL 解析商品基本資訊"""
        ...

    @abstractmethod
    def fetch_price(self, product_id: str) -> Optional[PriceSnapshot]:
        """取得指定商品目前最新價格快照"""
        ...

    @abstractmethod
    def fetch_flash_deals(self) -> List[FlashDealResult]:
        """抓取平台限時瘋搶列表"""
        ...
