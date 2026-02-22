# Deal Radar 擴充實作計畫

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在現有信用卡爬蟲系統上新增 PChome / Momo 商品價格追蹤與限時瘋搶功能，並與信用卡推薦引擎深度整合，讓通知同時告知降價資訊與最佳結帳卡。

**Architecture:** Monorepo 擴充，新增 `src/trackers/` 模組（對應現有 `src/crawlers/`），共用 DB、排程、通知、推薦引擎。PChome 優先使用 JSON API，Momo 使用 Playwright + stealth。

**Tech Stack:** Python 3.9+、SQLAlchemy 2.0（sync session）、httpx（PChome）、Playwright + playwright-stealth（Momo）、APScheduler、FastAPI、Next.js（前端）

---

## Task 1: Repo 重命名

**Files:**
- Modify: `pyproject.toml`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.prod.yml`
- Modify: `docker-compose.override.yml`
- Modify: `README.md`

**Step 1: 更新 pyproject.toml**

將第 2 行的 `name = "credit-card-crawler"` 改為：
```toml
name = "deal-radar"
description = "台灣信用卡 + 購物好康追蹤推薦系統"
```

**Step 2: 更新 docker-compose.yml service 名稱**

將所有 `credit-card-crawler` 字串替換為 `deal-radar`（service name、container_name 等）。

**Step 3: 更新 README.md 標題**

第一行改為 `# Deal Radar`，描述改為「台灣信用卡優惠 + 購物商場好康追蹤系統」。

**Step 4: Commit**

```bash
git add pyproject.toml docker-compose.yml docker-compose.prod.yml docker-compose.override.yml README.md
git commit -m "chore: rename project to deal-radar"
```

---

## Task 2: 新增資料模型

**Files:**
- Create: `src/models/tracked_product.py`
- Create: `src/models/price_history.py`
- Create: `src/models/flash_deal.py`
- Modify: `src/models/__init__.py`
- Test: `tests/test_tracker_models.py`

**Step 1: 撰寫 failing tests**

建立 `tests/test_tracker_models.py`：
```python
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
```

**Step 2: 執行測試確認失敗**

```bash
python3 -m pytest tests/test_tracker_models.py -v
```
預期：`FAIL` — `ModuleNotFoundError: No module named 'src.models.tracked_product'`

**Step 3: 建立 `src/models/tracked_product.py`**

```python
from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base
from src.models.base import TimestampMixin

if TYPE_CHECKING:
    from src.models.price_history import PriceHistory


class TrackedProduct(Base, TimestampMixin):
    __tablename__ = "tracked_products"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # pchome / momo
    product_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    target_price: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    price_history: Mapped[List["PriceHistory"]] = relationship(back_populates="product")

    def __repr__(self) -> str:
        return f"<TrackedProduct {self.platform}:{self.name}>"
```

**Step 4: 建立 `src/models/price_history.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base

if TYPE_CHECKING:
    from src.models.tracked_product import TrackedProduct


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("tracked_products.id"), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    original_price: Mapped[Optional[int]] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    product: Mapped["TrackedProduct"] = relationship(back_populates="price_history")

    def __repr__(self) -> str:
        return f"<PriceHistory product={self.product_id} price={self.price}>"
```

**Step 5: 建立 `src/models/flash_deal.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base
from src.models.base import TimestampMixin


class FlashDeal(Base, TimestampMixin):
    __tablename__ = "flash_deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_url: Mapped[str] = mapped_column(String(500), nullable=False)
    sale_price: Mapped[int] = mapped_column(Integer, nullable=False)
    original_price: Mapped[Optional[int]] = mapped_column(Integer)
    discount_rate: Mapped[Optional[float]] = mapped_column(Float)
    start_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<FlashDeal {self.platform}:{self.product_name}>"
```

**Step 6: 更新 `src/models/__init__.py`**

在現有 import 下方新增：
```python
from src.models.tracked_product import TrackedProduct
from src.models.price_history import PriceHistory
from src.models.flash_deal import FlashDeal
```

並在 `__all__` 串列加入 `"TrackedProduct"`, `"PriceHistory"`, `"FlashDeal"`。

**Step 7: 執行測試確認通過**

```bash
python3 -m pytest tests/test_tracker_models.py -v
```
預期：3 tests PASSED

**Step 8: Commit**

```bash
git add src/models/tracked_product.py src/models/price_history.py src/models/flash_deal.py src/models/__init__.py tests/test_tracker_models.py
git commit -m "feat(models): add TrackedProduct, PriceHistory, FlashDeal models"
```

---

## Task 3: 擴充 NotificationType

**Files:**
- Modify: `src/models/notification_log.py`

**Step 1: 新增通知類型**

在 `NotificationType` enum 新增三個值：
```python
price_drop = "price_drop"
target_price_reached = "target_price_reached"
flash_deal_new = "flash_deal_new"
```

**Step 2: 執行現有測試確保未破壞**

```bash
python3 -m pytest tests/ -v -k "notification"
```
預期：PASSED（或無相關測試，不應出現 FAIL）

**Step 3: Commit**

```bash
git add src/models/notification_log.py
git commit -m "feat(models): add price_drop, target_price_reached, flash_deal_new notification types"
```

---

## Task 4: BaseTracker 抽象基底

**Files:**
- Create: `src/trackers/__init__.py`
- Create: `src/trackers/base.py`
- Create: `src/trackers/platforms/__init__.py`
- Test: `tests/test_base_tracker.py`

**Step 1: 撰寫 failing tests**

建立 `tests/test_base_tracker.py`：
```python
import pytest
from src.trackers.base import BaseTracker, ProductResult, PriceSnapshot


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
```

**Step 2: 執行測試確認失敗**

```bash
python3 -m pytest tests/test_base_tracker.py -v
```
預期：`FAIL` — `ModuleNotFoundError`

**Step 3: 建立 `src/trackers/__init__.py`**（空檔）

**Step 4: 建立 `src/trackers/platforms/__init__.py`**（空檔）

**Step 5: 建立 `src/trackers/base.py`**

```python
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
```

**Step 6: 執行測試確認通過**

```bash
python3 -m pytest tests/test_base_tracker.py -v
```
預期：3 tests PASSED

**Step 7: Commit**

```bash
git add src/trackers/__init__.py src/trackers/base.py src/trackers/platforms/__init__.py tests/test_base_tracker.py
git commit -m "feat(trackers): add BaseTracker abstract class with dataclasses"
```

---

## Task 5: PChome Tracker

PChome 提供以下公開 JSON API（無需帳號）：
- 搜尋：`https://ecshweb.pchome.com.tw/search/v3.3/?q={keyword}&page=1&sort=rnk/dc`
- 商品詳情：`https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/{product_id}`
- 24h 限時特賣：`https://ecapi.pchome.com.tw/ecshop/prodapi/v2/store/DSAA31/prod?fields=Id,Name,Price,Pic`

**Files:**
- Create: `src/trackers/platforms/pchome.py`
- Test: `tests/test_pchome_tracker.py`

**Step 1: 撰寫 failing tests（使用 mock）**

建立 `tests/test_pchome_tracker.py`：
```python
import pytest
from unittest.mock import patch, MagicMock
from src.trackers.platforms.pchome import PChomeTracker


MOCK_SEARCH_RESPONSE = {
    "prods": [
        {
            "Id": "DYAQD6-A9009CMYB",
            "Name": "Sony WH-1000XM5 耳機",
            "Price": {"M": 6990, "P": 8490},
            "Pic": {"B": "path/to/img.jpg"},
        }
    ]
}

MOCK_PRODUCT_RESPONSE = {
    "Id": "DYAQD6-A9009CMYB",
    "Name": "Sony WH-1000XM5 耳機",
    "Price": {"M": 6990, "P": 8490},
    "Stock": True,
}

MOCK_FLASH_RESPONSE = [
    {
        "Id": "ABCD12-XYZ",
        "Name": "AirPods Pro 2",
        "Price": {"M": 6500, "P": 8490},
    }
]


def test_search_products():
    tracker = PChomeTracker()
    with patch.object(tracker.client, "get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_SEARCH_RESPONSE,
        )
        results = tracker.search_products("Sony 耳機")
    assert len(results) == 1
    assert results[0].platform == "pchome"
    assert results[0].price == 6990


def test_fetch_price():
    tracker = PChomeTracker()
    with patch.object(tracker.client, "get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_PRODUCT_RESPONSE,
        )
        snapshot = tracker.fetch_price("DYAQD6-A9009CMYB")
    assert snapshot is not None
    assert snapshot.price == 6990
    assert snapshot.in_stock is True


def test_fetch_flash_deals():
    tracker = PChomeTracker()
    with patch.object(tracker.client, "get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: MOCK_FLASH_RESPONSE,
        )
        deals = tracker.fetch_flash_deals()
    assert len(deals) == 1
    assert deals[0].platform == "pchome"
    assert deals[0].sale_price == 6500
```

**Step 2: 執行測試確認失敗**

```bash
python3 -m pytest tests/test_pchome_tracker.py -v
```
預期：`FAIL` — `ModuleNotFoundError`

**Step 3: 建立 `src/trackers/platforms/pchome.py`**

```python
from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote

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
        # 從 URL 萃取 product_id（路徑最後一段）
        product_id = url.rstrip("/").split("/")[-1]
        snapshot = self.fetch_price(product_id)
        if snapshot is None:
            return None
        return ProductResult(
            platform=self.platform,
            product_id=product_id,
            name="",  # 從 API 補充
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
```

**Step 4: 執行測試確認通過**

```bash
python3 -m pytest tests/test_pchome_tracker.py -v
```
預期：3 tests PASSED

**Step 5: Commit**

```bash
git add src/trackers/platforms/pchome.py tests/test_pchome_tracker.py
git commit -m "feat(trackers): add PChomeTracker using JSON API"
```

---

## Task 6: Momo Tracker

**Files:**
- Create: `src/trackers/platforms/momo.py`
- Test: `tests/test_momo_tracker.py`

**Step 1: 撰寫 failing tests（使用 mock）**

建立 `tests/test_momo_tracker.py`：
```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.trackers.platforms.momo import MomoTracker


def test_parse_price_from_text():
    from src.trackers.platforms.momo import _parse_price
    assert _parse_price("NT$6,990") == 6990
    assert _parse_price("6990元") == 6990
    assert _parse_price("無效") is None


def test_calculate_discount_rate():
    from src.trackers.platforms.momo import _calculate_discount_rate
    assert _calculate_discount_rate(6500, 8490) == pytest.approx(0.765, abs=0.001)
    assert _calculate_discount_rate(6500, 0) is None
```

**Step 2: 執行測試確認失敗**

```bash
python3 -m pytest tests/test_momo_tracker.py -v
```
預期：`FAIL` — `ModuleNotFoundError`

**Step 3: 建立 `src/trackers/platforms/momo.py`**

```python
from __future__ import annotations

import re
from typing import List, Optional

from loguru import logger
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from src.trackers.base import BaseTracker, FlashDealResult, PriceSnapshot, ProductResult

SEARCH_URL = "https://www.momoshop.com.tw/search/searchShop.jsp?keyword={keyword}"
FLASH_DEALS_URL = "https://www.momoshop.com.tw/category/LgrpCategory.jsp?l_code=fl"


def _parse_price(text: str) -> Optional[int]:
    """從文字中萃取數字價格"""
    match = re.search(r"[\d,]+", text.replace(",", ""))
    if match:
        try:
            return int(match.group().replace(",", ""))
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
        stealth_sync(page)
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

                    # 從 URL 萃取商品 ID
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
        snapshot = self.fetch_price(url)  # Momo 用 URL 當 product_id
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
        # product_id 為完整 URL 或 i_code
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
```

**Step 4: 執行測試確認通過**

```bash
python3 -m pytest tests/test_momo_tracker.py -v
```
預期：2 tests PASSED（純 utility 函式測試，不觸及 Playwright）

**Step 5: Commit**

```bash
git add src/trackers/platforms/momo.py tests/test_momo_tracker.py
git commit -m "feat(trackers): add MomoTracker using Playwright"
```

---

## Task 7: 推薦引擎整合——計算最佳結帳卡

**Files:**
- Modify: `src/recommender/scoring.py`
- Test: `tests/test_shopping_reward.py`

**Step 1: 撰寫 failing tests**

建立 `tests/test_shopping_reward.py`：
```python
import pytest
from unittest.mock import MagicMock
from src.recommender.scoring import calculate_shopping_reward
from src.models.card import CreditCard
from src.models.promotion import Promotion


def _make_card(base_rate=1.0, annual_fee=0):
    card = MagicMock(spec=CreditCard)
    card.id = 1
    card.name = "測試卡"
    card.base_reward_rate = base_rate
    card.annual_fee = annual_fee
    card.features = {"online_shopping": True}
    return card


def _make_promo(category="online_shopping", rate=3.0, limit=None):
    promo = MagicMock(spec=Promotion)
    promo.category = category
    promo.reward_rate = rate
    promo.reward_limit = limit
    return promo


def test_shopping_reward_basic():
    card = _make_card(base_rate=1.0)
    promotions = [_make_promo(category="online_shopping", rate=3.0)]
    result = calculate_shopping_reward(card, "pchome", 6990, promotions)
    # 6990 * 3% = 209.7
    assert result["reward_amount"] == pytest.approx(209.7, abs=1)
    assert result["best_rate"] == pytest.approx(3.0)


def test_shopping_reward_with_limit():
    card = _make_card(base_rate=1.0)
    promotions = [_make_promo(category="online_shopping", rate=5.0, limit=100)]
    result = calculate_shopping_reward(card, "pchome", 6990, promotions)
    # 上限 100 元
    assert result["reward_amount"] == pytest.approx(100.0)


def test_shopping_reward_no_promo_uses_base_rate():
    card = _make_card(base_rate=2.0)
    result = calculate_shopping_reward(card, "momo", 5000, [])
    # 5000 * 2% = 100
    assert result["reward_amount"] == pytest.approx(100.0)
```

**Step 2: 執行測試確認失敗**

```bash
python3 -m pytest tests/test_shopping_reward.py -v
```
預期：`FAIL` — `ImportError: cannot import name 'calculate_shopping_reward'`

**Step 3: 在 `src/recommender/scoring.py` 末端新增函式**

Platform 與信用卡 promotion category 的對應：
- `pchome` → `online_shopping`
- `momo` → `online_shopping`

```python
def calculate_shopping_reward(
    card: CreditCard,
    platform: str,
    amount: int,
    promotions: List[Promotion],
) -> Dict:
    """計算單次購物的最佳回饋

    Args:
        card: 信用卡
        platform: "pchome" 或 "momo"
        amount: 購物金額（元）
        promotions: 該卡目前有效的優惠列表

    Returns:
        {"reward_amount": float, "best_rate": float, "reason": str}
    """
    # platform → promotion category 對應
    platform_category = {"pchome": "online_shopping", "momo": "online_shopping"}
    category = platform_category.get(platform, "online_shopping")

    base_rate = card.base_reward_rate or 0.0
    best_rate = base_rate
    best_limit = None

    for promo in promotions:
        if promo.category == category and promo.reward_rate:
            if promo.reward_rate > best_rate:
                best_rate = promo.reward_rate
                best_limit = promo.reward_limit

    reward = amount * (best_rate / 100)
    if best_limit is not None and reward > best_limit:
        reward = float(best_limit)

    reason = f"{platform.upper()} 回饋 {best_rate}%"
    if best_limit:
        reason += f"（上限 {best_limit} 元）"

    return {
        "reward_amount": round(reward, 2),
        "best_rate": best_rate,
        "reason": reason,
    }
```

**Step 4: 執行測試確認通過**

```bash
python3 -m pytest tests/test_shopping_reward.py -v
```
預期：3 tests PASSED

**Step 5: 執行全部測試確保無回歸**

```bash
python3 -m pytest tests/ -v
```
預期：全部 PASSED

**Step 6: Commit**

```bash
git add src/recommender/scoring.py tests/test_shopping_reward.py
git commit -m "feat(recommender): add calculate_shopping_reward for platform-specific card ranking"
```

---

## Task 8: Tracker 排程 Jobs

**Files:**
- Create: `src/trackers/utils.py`（儲存工具函式）
- Modify: `src/scheduler/jobs.py`
- Modify: `src/scheduler/runner.py`

**Step 1: 建立 `src/trackers/utils.py`（追蹤核心邏輯）**

```python
from __future__ import annotations

from typing import List, Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from src.models.flash_deal import FlashDeal
from src.models.price_history import PriceHistory
from src.models.tracked_product import TrackedProduct
from src.trackers.base import BaseTracker


def get_tracker(platform: str) -> Optional[BaseTracker]:
    """根據 platform 名稱取得對應 Tracker 實例"""
    if platform == "pchome":
        from src.trackers.platforms.pchome import PChomeTracker
        return PChomeTracker()
    elif platform == "momo":
        from src.trackers.platforms.momo import MomoTracker
        return MomoTracker()
    logger.warning(f"Unknown platform: {platform}")
    return None


def check_price_and_snapshot(
    session: Session, product: TrackedProduct
) -> Tuple[Optional[PriceHistory], bool, bool]:
    """
    爬取最新價格並存入 price_history。

    Returns:
        (new_snapshot, is_price_drop, is_target_reached)
    """
    tracker = get_tracker(product.platform)
    if tracker is None:
        return None, False, False

    snapshot = tracker.fetch_price(product.product_id)
    if snapshot is None:
        logger.warning(f"No price fetched for product {product.id}")
        return None, False, False

    # 取得上一筆快照（如有）
    last = (
        session.query(PriceHistory)
        .filter_by(product_id=product.id)
        .order_by(PriceHistory.snapshot_at.desc())
        .first()
    )

    new_record = PriceHistory(
        product_id=product.id,
        price=snapshot.price,
        original_price=snapshot.original_price,
        in_stock=snapshot.in_stock,
    )
    session.add(new_record)
    session.commit()
    session.refresh(new_record)

    is_price_drop = last is not None and snapshot.price < last.price
    is_target_reached = (
        product.target_price is not None and snapshot.price <= product.target_price
    )

    return new_record, is_price_drop, is_target_reached


def refresh_flash_deals(session: Session, platform: str) -> int:
    """爬取並更新 flash_deals 資料表，回傳新增筆數"""
    tracker = get_tracker(platform)
    if tracker is None:
        return 0

    deals = tracker.fetch_flash_deals()
    count = 0
    for deal in deals:
        existing = (
            session.query(FlashDeal)
            .filter_by(platform=deal.platform, product_url=deal.product_url)
            .first()
        )
        if existing is None:
            record = FlashDeal(
                platform=deal.platform,
                product_name=deal.product_name,
                product_url=deal.product_url,
                sale_price=deal.sale_price,
                original_price=deal.original_price,
                discount_rate=deal.discount_rate,
            )
            session.add(record)
            count += 1
    session.commit()
    return count
```

**Step 2: 在 `src/scheduler/jobs.py` 末端新增兩個 job 函式**

```python
def run_price_tracking():
    """每 30 分鐘：爬取所有 active 商品最新價格並觸發通知"""
    from src.models.tracked_product import TrackedProduct
    from src.models.notification_log import NotificationType
    from src.trackers.utils import check_price_and_snapshot
    from src.notifications.formatter import format_price_drop_alert

    logger.info("Starting price tracking job")
    with get_sync_session() as session:
        products = session.query(TrackedProduct).filter_by(is_active=True).all()
        logger.info(f"Tracking {len(products)} active products")

        for product in products:
            try:
                snapshot, is_drop, is_target = check_price_and_snapshot(session, product)
                if snapshot and (is_drop or is_target):
                    notification_type = (
                        NotificationType.target_price_reached
                        if is_target
                        else NotificationType.price_drop
                    )
                    # 取得 Top 3 推薦卡
                    top_cards = _get_top_cards_for_shopping(
                        session, product.platform, snapshot.price
                    )
                    message = format_price_drop_alert(product, snapshot, top_cards, is_target)
                    dispatcher = NotificationDispatcher(session)
                    dispatcher.dispatch(notification_type, [snapshot.id], message)
            except Exception as e:
                logger.error(f"Error tracking product {product.id}: {e}")

    logger.info("Price tracking job completed")


def run_flash_deals_refresh():
    """每 1 小時：更新限時瘋搶列表"""
    from src.trackers.utils import refresh_flash_deals

    logger.info("Starting flash deals refresh")
    with get_sync_session() as session:
        for platform in ["pchome", "momo"]:
            try:
                count = refresh_flash_deals(session, platform)
                logger.info(f"Flash deals refreshed for {platform}: +{count} new")
            except Exception as e:
                logger.error(f"Error refreshing flash deals for {platform}: {e}")
    logger.info("Flash deals refresh completed")


def _get_top_cards_for_shopping(session, platform: str, amount: int, top_n: int = 3):
    """取得指定購物平台與金額的 Top N 信用卡（含回饋試算）"""
    from src.models.card import CreditCard
    from src.models.promotion import Promotion
    from src.recommender.scoring import calculate_shopping_reward

    cards = session.query(CreditCard).all()
    ranked = []
    for card in cards:
        promotions = session.query(Promotion).filter_by(card_id=card.id).all()
        result = calculate_shopping_reward(card, platform, amount, promotions)
        ranked.append({"card": card, **result})

    ranked.sort(key=lambda x: x["reward_amount"], reverse=True)
    return ranked[:top_n]
```

**Step 3: 在 `src/scheduler/runner.py` 新增兩個排程**

在 `create_scheduler()` 函式末端，`return scheduler` 之前加入：

```python
from src.scheduler.jobs import run_price_tracking, run_flash_deals_refresh

# 每 30 分鐘追蹤商品價格
scheduler.add_job(
    run_price_tracking,
    "interval",
    minutes=30,
    id="price_tracking",
    name="Price Tracking",
)

# 每 1 小時更新限時瘋搶
scheduler.add_job(
    run_flash_deals_refresh,
    "interval",
    hours=1,
    id="flash_deals_refresh",
    name="Flash Deals Refresh",
)
```

**Step 4: 執行全部測試確保未破壞**

```bash
python3 -m pytest tests/ -v
```
預期：全部 PASSED

**Step 5: Commit**

```bash
git add src/trackers/utils.py src/scheduler/jobs.py src/scheduler/runner.py
git commit -m "feat(scheduler): add price tracking and flash deals refresh jobs"
```

---

## Task 9: 通知訊息格式化

**Files:**
- Modify: `src/notifications/formatter.py`

**Step 1: 在 `src/notifications/formatter.py` 末端新增**

查看現有 formatter 格式後，新增以下函式：

```python
def format_price_drop_alert(
    product,        # TrackedProduct
    snapshot,       # PriceHistory
    top_cards: list,
    is_target_reached: bool = False,
) -> dict:
    """格式化降價或目標價通知（含 Top 3 最佳結帳卡）"""
    emoji = "🎯" if is_target_reached else "📉"
    title = "目標價達成！" if is_target_reached else "價格警示"
    platform_name = "PChome" if product.platform == "pchome" else "Momo"

    discount_text = ""
    if snapshot.original_price and snapshot.original_price > snapshot.price:
        pct = round(snapshot.price / snapshot.original_price * 100)
        discount_text = f"（折 {pct} 折）"

    card_lines = "\n".join(
        f"  {i+1}. {r['card'].name}：回饋 {r['best_rate']}% = "
        f"-${r['reward_amount']:.0f}，實付 ${snapshot.price - r['reward_amount']:.0f}"
        for i, r in enumerate(top_cards)
    )

    telegram_text = (
        f"{emoji} {title}：{product.name}\n\n"
        f"🏪 {platform_name} 現價：${snapshot.price:,}{discount_text}\n\n"
        f"💳 最佳結帳方式：\n{card_lines}\n\n"
        f"🔗 {product.url}"
    )

    # Discord embed
    embed = {
        "title": f"{emoji} {title}：{product.name}",
        "color": 0x00B894 if is_target_reached else 0xE17055,
        "fields": [
            {
                "name": f"🏪 {platform_name} 現價",
                "value": f"**${snapshot.price:,}**{discount_text}",
                "inline": True,
            },
            {
                "name": "💳 最佳結帳卡",
                "value": "\n".join(
                    f"{i+1}. {r['card'].name} (-${r['reward_amount']:.0f})"
                    for i, r in enumerate(top_cards)
                ),
                "inline": False,
            },
        ],
        "url": product.url,
    }

    return {"telegram": telegram_text, "discord_embeds": [embed]}
```

**Step 2: 執行全部測試**

```bash
python3 -m pytest tests/ -v
```
預期：全部 PASSED

**Step 3: Commit**

```bash
git add src/notifications/formatter.py
git commit -m "feat(notifications): add format_price_drop_alert with best card recommendations"
```

---

## Task 10: API 端點

**Files:**
- Create: `src/api/products.py`
- Modify: `src/api/router.py`
- Test: `tests/test_products_api.py`

**Step 1: 撰寫 failing tests**

建立 `tests/test_products_api.py`：
```python
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.mark.asyncio
async def test_get_products_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/products")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_flash_deals_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/flash-deals")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
```

**Step 2: 執行測試確認失敗**

```bash
python3 -m pytest tests/test_products_api.py -v
```
預期：`FAIL` — 404 或路由不存在

**Step 3: 建立 `src/api/products.py`**

```python
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.flash_deal import FlashDeal
from src.models.price_history import PriceHistory
from src.models.tracked_product import TrackedProduct

router = APIRouter(prefix="/api", tags=["products"])


class AddProductRequest(BaseModel):
    platform: str          # "pchome" or "momo"
    url: Optional[str] = None
    keyword: Optional[str] = None
    target_price: Optional[int] = None


class ProductResponse(BaseModel):
    id: int
    platform: str
    name: str
    url: str
    target_price: Optional[int]
    is_active: bool
    current_price: Optional[int] = None
    lowest_price: Optional[int] = None


class PriceHistoryResponse(BaseModel):
    price: int
    original_price: Optional[int]
    in_stock: bool
    snapshot_at: str


@router.get("/products")
async def list_products(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(TrackedProduct).where(TrackedProduct.is_active == True))
    products = result.scalars().all()
    return {"items": [
        ProductResponse(
            id=p.id, platform=p.platform, name=p.name,
            url=p.url, target_price=p.target_price, is_active=p.is_active
        )
        for p in products
    ]}


@router.post("/products", status_code=201)
async def add_product(body: AddProductRequest, db: AsyncSession = Depends(get_db)):
    if not body.url and not body.keyword:
        raise HTTPException(status_code=400, detail="url 或 keyword 至少提供一個")

    platform = body.platform.lower()
    if platform not in ("pchome", "momo"):
        raise HTTPException(status_code=400, detail="platform 僅支援 pchome 或 momo")

    # 以 URL 直接建立（不即時爬取，排程會補充價格）
    if body.url:
        from sqlalchemy import select
        existing = await db.execute(
            select(TrackedProduct).where(TrackedProduct.url == body.url)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="此商品已在追蹤清單中")

        # 從 URL 萃取 product_id
        url = body.url
        import re
        if platform == "pchome":
            pid = url.rstrip("/").split("/")[-1]
        else:
            m = re.search(r"i_code=(\d+)", url)
            pid = m.group(1) if m else url

        product = TrackedProduct(
            platform=platform, product_id=pid,
            name=pid,  # 排程爬取後更新
            url=url, target_price=body.target_price,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return {"id": product.id, "message": "已加入追蹤"}

    # keyword 搜尋（同步呼叫 tracker）
    from src.trackers.utils import get_tracker
    tracker = get_tracker(platform)
    if tracker is None:
        raise HTTPException(status_code=500, detail="Tracker 不可用")
    results = tracker.search_products(body.keyword)
    return {"results": [
        {"platform": r.platform, "product_id": r.product_id,
         "name": r.name, "url": r.url, "price": r.price}
        for r in results
    ]}


@router.delete("/products/{product_id}", status_code=204)
async def remove_product(product_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(TrackedProduct).where(TrackedProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.is_active = False
    await db.commit()


@router.get("/products/{product_id}/history")
async def get_price_history(product_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.snapshot_at.asc())
    )
    history = result.scalars().all()
    return [
        PriceHistoryResponse(
            price=h.price, original_price=h.original_price,
            in_stock=h.in_stock,
            snapshot_at=h.snapshot_at.isoformat(),
        )
        for h in history
    ]


@router.get("/flash-deals")
async def list_flash_deals(
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    stmt = select(FlashDeal).order_by(FlashDeal.discount_rate.asc())
    if platform:
        stmt = stmt.where(FlashDeal.platform == platform)
    result = await db.execute(stmt)
    deals = result.scalars().all()
    return [
        {
            "id": d.id, "platform": d.platform,
            "product_name": d.product_name, "product_url": d.product_url,
            "sale_price": d.sale_price, "original_price": d.original_price,
            "discount_rate": d.discount_rate,
        }
        for d in deals
    ]
```

**Step 4: 更新 `src/api/router.py`**

```python
from src.api.products import router as products_router
api_router.include_router(products_router)
```

**Step 5: 執行測試確認通過**

```bash
python3 -m pytest tests/test_products_api.py -v
```
預期：2 tests PASSED

**Step 6: Commit**

```bash
git add src/api/products.py src/api/router.py tests/test_products_api.py
git commit -m "feat(api): add /products and /flash-deals endpoints"
```

---

## Task 11: 前端——導覽列更新

**Files:**
- Modify: `frontend/src/components/` 中的 Navbar 元件（依現有路徑）

**Step 1: 找到現有 Navbar 元件**

```bash
find frontend/src -name "*.tsx" | xargs grep -l "nav\|Nav\|header\|Header" | head -5
```

**Step 2: 在現有導覽連結列表中新增兩個項目**

在現有的導覽項目陣列中加入：
```tsx
{ href: "/track", label: "商品追蹤" },
{ href: "/deals", label: "限時瘋搶" },
```

**Step 3: 啟動前端確認導覽列正確顯示**

```bash
npm run dev --prefix frontend
```
瀏覽 `http://localhost:3000`，確認導覽列出現「商品追蹤」和「限時瘋搶」。

**Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add product tracking and flash deals nav items"
```

---

## Task 12: 前端——商品追蹤頁面 `/track`

**Files:**
- Create: `frontend/src/app/track/page.tsx`
- Create: `frontend/src/app/track/components/SearchBar.tsx`
- Create: `frontend/src/app/track/components/TrackingList.tsx`
- Create: `frontend/src/app/track/components/PriceChart.tsx`

**Step 1: 建立 `frontend/src/app/track/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import SearchBar from "./components/SearchBar";
import TrackingList from "./components/TrackingList";

export default function TrackPage() {
  const [searchResults, setSearchResults] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSearchResults = (results: any[]) => {
    setSearchResults(results);
  };

  const handleProductAdded = () => {
    setRefreshKey((k) => k + 1);
    setSearchResults([]);
  };

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-2">商品追蹤</h1>
      <p className="text-gray-500 mb-8">
        貼上 PChome / Momo 商品連結，或輸入關鍵字搜尋，降價立即通知
      </p>

      <SearchBar
        onResults={handleSearchResults}
        onProductAdded={handleProductAdded}
      />

      {searchResults.length > 0 && (
        <section className="mt-6">
          <h2 className="text-lg font-semibold mb-3">搜尋結果</h2>
          <div className="space-y-2">
            {searchResults.map((result: any, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-4 rounded-xl border bg-white/60 backdrop-blur"
              >
                <div>
                  <p className="font-medium">{result.name}</p>
                  <p className="text-sm text-gray-500">{result.platform.toUpperCase()}</p>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-lg font-bold text-green-600">
                    ${result.price?.toLocaleString()}
                  </span>
                  <button
                    onClick={async () => {
                      await fetch("/api/products", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                          platform: result.platform,
                          url: result.url,
                        }),
                      });
                      handleProductAdded();
                    }}
                    className="px-3 py-1 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
                  >
                    追蹤
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mt-8">
        <h2 className="text-lg font-semibold mb-3">我的追蹤清單</h2>
        <TrackingList key={refreshKey} />
      </section>
    </main>
  );
}
```

**Step 2: 建立 `frontend/src/app/track/components/SearchBar.tsx`**

```tsx
"use client";

import { useState } from "react";

interface Props {
  onResults: (results: any[]) => void;
  onProductAdded: () => void;
}

export default function SearchBar({ onResults, onProductAdded }: Props) {
  const [input, setInput] = useState("");
  const [platform, setPlatform] = useState("pchome");
  const [loading, setLoading] = useState(false);

  const isUrl = input.startsWith("http");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    if (isUrl) {
      const detectedPlatform = input.includes("pchome") ? "pchome" : "momo";
      const resp = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform: detectedPlatform, url: input }),
      });
      if (resp.ok) onProductAdded();
    } else {
      const resp = await fetch("/api/products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ platform, keyword: input }),
      });
      const data = await resp.json();
      onResults(data.results || []);
    }

    setLoading(false);
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      {!isUrl && (
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
          className="px-3 py-2 rounded-xl border bg-white/60 backdrop-blur"
        >
          <option value="pchome">PChome</option>
          <option value="momo">Momo</option>
        </select>
      )}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="貼上商品連結或輸入關鍵字..."
        className="flex-1 px-4 py-2 rounded-xl border bg-white/60 backdrop-blur focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
      <button
        type="submit"
        disabled={loading || !input.trim()}
        className="px-5 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "搜尋中..." : isUrl ? "加入追蹤" : "搜尋"}
      </button>
    </form>
  );
}
```

**Step 3: 建立 `frontend/src/app/track/components/TrackingList.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import PriceChart from "./PriceChart";

export default function TrackingList() {
  const [products, setProducts] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [histories, setHistories] = useState<Record<number, any[]>>({});

  useEffect(() => {
    fetch("/api/products")
      .then((r) => r.json())
      .then((data) => setProducts(data.items || []));
  }, []);

  const loadHistory = async (id: number) => {
    if (histories[id]) return;
    const resp = await fetch(`/api/products/${id}/history`);
    const data = await resp.json();
    setHistories((prev) => ({ ...prev, [id]: data }));
  };

  const toggle = (id: number) => {
    if (expanded === id) {
      setExpanded(null);
    } else {
      setExpanded(id);
      loadHistory(id);
    }
  };

  const removeProduct = async (id: number) => {
    await fetch(`/api/products/${id}`, { method: "DELETE" });
    setProducts((prev) => prev.filter((p) => p.id !== id));
  };

  if (products.length === 0) {
    return (
      <p className="text-gray-400 text-center py-8">尚未追蹤任何商品</p>
    );
  }

  return (
    <div className="space-y-3">
      {products.map((p) => (
        <div
          key={p.id}
          className="rounded-xl border bg-white/60 backdrop-blur overflow-hidden"
        >
          <div
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/80"
            onClick={() => toggle(p.id)}
          >
            <div>
              <p className="font-medium">{p.name}</p>
              <p className="text-sm text-gray-400">
                {p.platform.toUpperCase()}
                {p.target_price && ` · 目標價 $${p.target_price.toLocaleString()}`}
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); removeProduct(p.id); }}
              className="text-red-400 hover:text-red-600 text-sm px-2"
            >
              移除
            </button>
          </div>

          {expanded === p.id && histories[p.id] && (
            <div className="px-4 pb-4">
              <PriceChart data={histories[p.id]} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

**Step 4: 建立 `frontend/src/app/track/components/PriceChart.tsx`**

使用 recharts（Next.js 專案中常用且輕量）：

```tsx
"use client";

import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts";

interface HistoryPoint {
  price: number;
  snapshot_at: string;
}

export default function PriceChart({ data }: { data: HistoryPoint[] }) {
  if (!data || data.length === 0) {
    return <p className="text-gray-400 text-sm">尚無價格記錄</p>;
  }

  const chartData = data.map((d) => ({
    date: new Date(d.snapshot_at).toLocaleDateString("zh-TW", {
      month: "short", day: "numeric"
    }),
    price: d.price,
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={chartData}>
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v) => `$${v.toLocaleString()}`}
          width={70}
        />
        <Tooltip formatter={(v: number) => [`$${v.toLocaleString()}`, "價格"]} />
        <Line
          type="monotone" dataKey="price"
          stroke="#3B82F6" strokeWidth={2} dot={{ r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

**Step 5: 安裝 recharts（若尚未安裝）**

```bash
cd frontend && npm install recharts
```

**Step 6: 啟動前端確認頁面正確**

```bash
npm run dev --prefix frontend
```
瀏覽 `http://localhost:3000/track` 確認頁面正常渲染。

**Step 7: Commit**

```bash
git add frontend/src/app/track/
git commit -m "feat(frontend): add /track product tracking page with price chart"
```

---

## Task 13: 前端——限時瘋搶頁面 `/deals`

**Files:**
- Create: `frontend/src/app/deals/page.tsx`
- Create: `frontend/src/app/deals/components/DealCard.tsx`

**Step 1: 建立 `frontend/src/app/deals/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import DealCard from "./components/DealCard";

export default function DealsPage() {
  const [platform, setPlatform] = useState<"pchome" | "momo">("pchome");
  const [deals, setDeals] = useState<any[]>([]);
  const [sortBy, setSortBy] = useState<"discount" | "time">("discount");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/flash-deals?platform=${platform}`)
      .then((r) => r.json())
      .then((data) => {
        let sorted = [...data];
        if (sortBy === "discount") {
          sorted.sort((a, b) => (a.discount_rate || 1) - (b.discount_rate || 1));
        }
        setDeals(sorted);
        setLoading(false);
      });
  }, [platform, sortBy]);

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-2">限時瘋搶</h1>
      <p className="text-gray-500 mb-6">即時追蹤 PChome / Momo 最夯限時特賣，並推薦最佳刷卡方式</p>

      <div className="flex gap-3 mb-6">
        <div className="flex rounded-xl overflow-hidden border">
          {(["pchome", "momo"] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={`px-5 py-2 text-sm font-medium transition-colors ${
                platform === p ? "bg-blue-600 text-white" : "bg-white/60 text-gray-600 hover:bg-white"
              }`}
            >
              {p === "pchome" ? "PChome 24h" : "Momo 購物"}
            </button>
          ))}
        </div>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as any)}
          className="px-3 py-2 rounded-xl border bg-white/60 text-sm"
        >
          <option value="discount">折扣最高</option>
          <option value="time">最新上架</option>
        </select>
      </div>

      {loading ? (
        <p className="text-center text-gray-400 py-12">載入中...</p>
      ) : deals.length === 0 ? (
        <p className="text-center text-gray-400 py-12">目前無限時瘋搶資料</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {deals.map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
        </div>
      )}
    </main>
  );
}
```

**Step 2: 建立 `frontend/src/app/deals/components/DealCard.tsx`**

```tsx
"use client";

import { useState } from "react";

interface Deal {
  id: number;
  platform: string;
  product_name: string;
  product_url: string;
  sale_price: number;
  original_price?: number;
  discount_rate?: number;
  best_card?: { name: string; reward_amount: number; best_rate: number };
}

export default function DealCard({ deal }: { deal: Deal }) {
  const [showDetails, setShowDetails] = useState(false);

  const discountPct = deal.discount_rate
    ? Math.round(deal.discount_rate * 100)
    : null;

  return (
    <div className="rounded-xl border bg-white/60 backdrop-blur overflow-hidden hover:shadow-md transition-shadow">
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <h3 className="font-semibold text-sm leading-tight line-clamp-2 flex-1 mr-2">
            {deal.product_name}
          </h3>
          {discountPct !== null && (
            <span className="text-xs font-bold text-red-500 bg-red-50 px-2 py-0.5 rounded-full shrink-0">
              {discountPct}折
            </span>
          )}
        </div>

        <div className="flex items-baseline gap-2 mb-3">
          <span className="text-xl font-bold text-blue-700">
            ${deal.sale_price.toLocaleString()}
          </span>
          {deal.original_price && (
            <span className="text-sm text-gray-400 line-through">
              ${deal.original_price.toLocaleString()}
            </span>
          )}
        </div>

        {/* 最佳結帳卡 Top 1 */}
        {deal.best_card && (
          <div className="bg-green-50 rounded-lg px-3 py-2 mb-3">
            <p className="text-xs text-green-700">
              💳 {deal.best_card.name}：回饋 {deal.best_card.best_rate}%
              = 省 <strong>${deal.best_card.reward_amount.toFixed(0)}</strong>
            </p>
          </div>
        )}

        <div className="flex justify-between items-center">
          <a
            href={deal.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline"
          >
            前往購買 →
          </a>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            {showDetails ? "收起" : "查看更多"}
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Step 3: 啟動前端確認頁面**

```bash
npm run dev --prefix frontend
```
瀏覽 `http://localhost:3000/deals` 確認頁面正確顯示。

**Step 4: Commit**

```bash
git add frontend/src/app/deals/
git commit -m "feat(frontend): add /deals flash deals page with best card highlights"
```

---

## Task 14: 執行全部測試與 Lint

**Step 1: 執行全部 Python 測試**

```bash
python3 -m pytest tests/ -v
```
預期：全部 PASSED

**Step 2: Lint 檢查**

```bash
python3 -m ruff check src/ tests/
```
預期：無新增錯誤（現有 2 個 pre-existing E741/F841 錯誤可忽略）

**Step 3: 前端 build 測試**

```bash
npm run build --prefix frontend
```
預期：Build 成功，無 TypeScript 錯誤

**Step 4: Final commit（若有 lint 修正）**

```bash
git add -A
git commit -m "chore: fix lint and type issues after deal-radar expansion"
```

---

## 實作順序建議

```
Task 1（Repo 重命名）
    ↓
Task 2（資料模型）
    ↓
Task 3（NotificationType 擴充）
    ↓
Task 4（BaseTracker）
    ↓
Task 5（PChome Tracker）  ←→  Task 6（Momo Tracker）  [可並行]
    ↓
Task 7（推薦引擎整合）
    ↓
Task 8（排程 Jobs）
    ↓
Task 9（通知格式化）
    ↓
Task 10（API 端點）
    ↓
Task 11-13（前端）  [可並行]
    ↓
Task 14（測試 & Lint）
```
