# Flash Deal Price History + Search Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** (1) When a tracked product appears in a flash sale, record its discounted price in the price history and send a price-drop notification. (2) Fix keyword search: PChome results show an external link, Momo keyword opens the Momo search page in a new tab instead of using broken Playwright search.

**Architecture:** Feature 1 extends `refresh_flash_deals()` in `src/trackers/utils.py` to cross-reference new flash deals against active `TrackedProduct` rows by URL match, then creates a `PriceHistory` with `source="flash_deal"` and dispatches a notification. Feature 2 is frontend-only: `SearchBar.tsx` handles Momo keyword by opening Momo's search URL in a new tab; PChome result cards in `track/page.tsx` gain an external "查看 ↗" link.

**Tech Stack:** Python / SQLAlchemy (sync Session) for backend; React / Next.js / TypeScript for frontend. Tests use pytest with in-memory SQLite.

---

### Task 1: Add `source` column to `PriceHistory`

**Files:**
- Modify: `src/models/price_history.py`
- Modify: `tests/test_tracker_models.py`

**Step 1: Write the failing test**

Add to `tests/test_tracker_models.py`:

```python
def test_price_history_source_column(db):
    product = TrackedProduct(
        platform="pchome", product_id="DYAQD6",
        name="Sony 耳機", url="https://24h.pchome.com.tw/prod/DYAQD6",
    )
    db.add(product)
    db.flush()

    snapshot = PriceHistory(
        product_id=product.id, price=5990, in_stock=True, source="flash_deal"
    )
    db.add(snapshot)
    db.commit()
    assert snapshot.source == "flash_deal"

    default_snapshot = PriceHistory(
        product_id=product.id, price=6990, in_stock=True
    )
    db.add(default_snapshot)
    db.commit()
    assert default_snapshot.source is None
```

**Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_tracker_models.py::test_price_history_source_column -v
```

Expected: `FAILED` — `TypeError: unexpected keyword argument 'source'`

**Step 3: Add `source` column to `PriceHistory`**

In `src/models/price_history.py`, add the import for `String` to the existing import line, then add the column after `snapshot_at`:

```python
# Change this line (add String):
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func

# Add after snapshot_at column:
source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
```

**Step 4: Run test to verify it passes**

```bash
python3 -m pytest tests/test_tracker_models.py::test_price_history_source_column -v
```

Expected: `PASSED`

**Step 5: Run the full model test suite**

```bash
python3 -m pytest tests/test_tracker_models.py -v
```

Expected: all PASSED

**Step 6: Commit**

```bash
git add src/models/price_history.py tests/test_tracker_models.py
git commit -m "feat(models): add source column to PriceHistory"
```

---

### Task 2: Extend `refresh_flash_deals()` to cross-reference tracked products and notify

**Files:**
- Modify: `src/trackers/utils.py`
- Create: `tests/test_flash_deal_cross_reference.py`

**Background:** `refresh_flash_deals()` currently saves new `FlashDeal` rows and returns a count. After saving each new deal, we need to check if any active `TrackedProduct` has `url == deal.product_url`. If so, create a `PriceHistory` (`source="flash_deal"`) and—if the price dropped compared to the last snapshot—dispatch a `price_drop` notification via `NotificationDispatcher`. The notification reuses `format_price_drop_alert()` and deduplication is handled automatically by `NotificationLog`.

`NotificationDispatcher.dispatch()` signature (from `src/notifications/dispatcher.py`):
```python
dispatcher.dispatch(notification_type: NotificationType, reference_ids: list[int], message: str)
```

`format_price_drop_alert()` signature (from `src/notifications/formatter.py`):
```python
format_price_drop_alert(product: TrackedProduct, snapshot: PriceHistory, top_cards: list, is_target_reached: bool) -> str
```
Pass `top_cards=[]` and `is_target_reached=False` here (flash deal cross-check doesn't have card context).

**Step 1: Write the failing tests**

Create `tests/test_flash_deal_cross_reference.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_flash_deal_cross_reference.py -v
```

Expected: all 4 FAILED (logic not yet implemented)

**Step 3: Update `refresh_flash_deals()` in `src/trackers/utils.py`**

Replace the current `refresh_flash_deals` function with:

```python
def refresh_flash_deals(session: Session, platform: str) -> int:
    """爬取並更新 flash_deals 資料表，回傳新增筆數。
    若新加入的特賣商品與追蹤清單有 URL 匹配，建立 PriceHistory 並視情況發送通知。
    """
    from src.models.notification_log import NotificationType
    from src.models.tracked_product import TrackedProduct
    from src.notifications.dispatcher import NotificationDispatcher
    from src.notifications.formatter import format_price_drop_alert

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
        if existing is not None:
            continue

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

        # 比對追蹤清單
        matched = (
            session.query(TrackedProduct)
            .filter_by(url=deal.product_url, is_active=True)
            .first()
        )
        if matched is None:
            continue

        last = (
            session.query(PriceHistory)
            .filter_by(product_id=matched.id)
            .order_by(PriceHistory.snapshot_at.desc())
            .first()
        )

        snapshot = PriceHistory(
            product_id=matched.id,
            price=deal.sale_price,
            original_price=deal.original_price,
            in_stock=True,
            source="flash_deal",
        )
        session.add(snapshot)
        session.flush()

        if last is not None and deal.sale_price < last.price:
            message = format_price_drop_alert(matched, snapshot, [], False)
            dispatcher = NotificationDispatcher(session)
            dispatcher.dispatch(NotificationType.price_drop, [snapshot.id], message)

    session.commit()
    return count
```

**Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_flash_deal_cross_reference.py -v
```

Expected: all 4 PASSED

**Step 5: Run the full test suite to check for regressions**

```bash
python3 -m pytest tests/ -v --ignore=tests/test_momo_tracker.py
```

(Momo tracker tests require Playwright; skip in local dev. All others should PASS.)

**Step 6: Lint**

```bash
python3 -m ruff check src/trackers/utils.py
```

Expected: no errors

**Step 7: Commit**

```bash
git add src/trackers/utils.py tests/test_flash_deal_cross_reference.py
git commit -m "feat(trackers): cross-reference flash deals with tracked products, record price history and notify on drop"
```

---

### Task 3: Frontend — Momo keyword redirects to Momo search

**Files:**
- Modify: `frontend/src/app/track/components/SearchBar.tsx`

**Background:** When the user selects `momo` as platform and submits a keyword (not a URL), instead of calling `POST /api/products`, open Momo's search page in a new tab and show an inline hint. The Momo search URL pattern is:
```
https://www.momoshop.com.tw/search/searchShop.jsp?keyword=<encoded-keyword>
```

**Step 1: Replace the keyword branch in `handleSubmit`**

Current code in `SearchBar.tsx` lines 29–37:
```typescript
} else {
  const resp = await fetch("/api/products", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ platform, keyword: input }),
  });
  const data = await resp.json();
  onResults(data.results || []);
}
```

Replace with:
```typescript
} else {
  if (platform === "momo") {
    const momoSearchUrl = `https://www.momoshop.com.tw/search/searchShop.jsp?keyword=${encodeURIComponent(input)}`;
    window.open(momoSearchUrl, "_blank", "noopener,noreferrer");
    setMomoHint(true);
  } else {
    const resp = await fetch("/api/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, keyword: input }),
    });
    const data = await resp.json();
    onResults(data.results || []);
  }
}
```

Also add `momoHint` state and reset it when input changes:

```typescript
const [momoHint, setMomoHint] = useState(false);

// inside the input onChange handler, add:
setMomoHint(false);
```

And render the hint below the form (inside the component return, after `</form>`):

```typescript
{momoHint && (
  <p className="mt-2 text-sm text-blue-600">
    已在新視窗開啟 Momo 搜尋，找到商品後請複製連結貼回此處追蹤
  </p>
)}
```

**Step 2: Verify in browser**

1. Go to http://localhost:3000/track
2. Select `Momo`, type `AirPods Pro`
3. Click 搜尋
4. Expected: new tab opens to Momo search; blue hint text appears below the search bar
5. Select `PChome`, type `Sony 耳機`, click 搜尋
6. Expected: search results appear as before (no regression)

**Step 3: Commit**

```bash
git add frontend/src/app/track/components/SearchBar.tsx
git commit -m "feat(frontend): redirect Momo keyword search to Momo search page"
```

---

### Task 4: Frontend — Add external link to PChome search result cards

**Files:**
- Modify: `frontend/src/app/track/page.tsx`

**Background:** The search result cards currently show product name, platform, price, and a "追蹤" button. We need to add a small "在 PChome 查看 ↗" link so users can verify the product before tracking.

**Step 1: Add external link to each result card**

In `frontend/src/app/track/page.tsx`, find the result card block (around line 39–65). Inside the left `<div>` that contains `<p className="font-medium">{result.name}</p>`, add a link after the platform badge:

```typescript
<div>
  <p className="font-medium">{result.name}</p>
  <div className="flex items-center gap-2 mt-0.5">
    <p className="text-sm text-gray-500">{result.platform.toUpperCase()}</p>
    <a
      href={result.url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-xs text-blue-500 hover:underline"
    >
      查看 ↗
    </a>
  </div>
</div>
```

**Step 2: Verify in browser**

1. Go to http://localhost:3000/track
2. Select `PChome`, type `Sony`
3. Click 搜尋
4. Expected: results display with a small `查看 ↗` link next to the platform badge; clicking it opens PChome in a new tab

**Step 3: Commit**

```bash
git add frontend/src/app/track/page.tsx
git commit -m "feat(frontend): add external product link to PChome search result cards"
```

---

## Final Verification

```bash
# Run all non-Playwright tests
python3 -m pytest tests/ -v --ignore=tests/test_momo_tracker.py

# Lint
python3 -m ruff check src/ tests/

# Check frontend builds cleanly
npm run build --prefix frontend
```

All tests should PASS; ruff should report no errors; build should succeed.
