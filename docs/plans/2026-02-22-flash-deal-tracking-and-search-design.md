# Design: Flash Deal Price History + Keyword Search Optimization

Date: 2026-02-22

## Problem

### 1. Flash Deal prices not captured in price history
When a tracked product appears in PChome/Momo flash sale pages, its discounted price is stored in `flash_deals` but never written to `price_history`. Users do not receive price-drop notifications for flash sale prices.

### 2. Keyword search broken / poor UX
- PChome: returns empty results inconsistently
- Momo: Playwright-based search is slow, times out, and fails often
- Search result cards have no external links to verify the correct product before tracking

---

## Feature 1: Flash Deal → Price History + Notification

### Approach
Extend `refresh_flash_deals()` in `src/trackers/utils.py` to cross-reference new flash deals against active `TrackedProduct` records after saving.

### Data Model Change
Add an optional `source` column to `PriceHistory`:

```python
# src/models/price_history.py
source: Mapped[Optional[str]] = mapped_column(String(20))
# values: "scheduler" (default) | "flash_deal"
```

Existing rows default to `None` (no migration value needed — nullable column).

### Logic in `refresh_flash_deals()`

After inserting a new `FlashDeal`, look up `TrackedProduct` by URL match:

```
tracked_product.url == flash_deal.product_url  (exact match)
```

If a match is found:
1. Query the last `PriceHistory` for that product.
2. Create a new `PriceHistory` with `price = flash_deal.sale_price`, `source = "flash_deal"`.
3. If `sale_price < last_price`: call `NotificationDispatcher` with `NotificationType.price_drop`.
   - Reuse `format_price_drop_alert()` from `src/notifications/formatter.py`.
   - Deduplication is already handled by `NotificationLog` (unique on type+reference_id+channel).

### Why not a separate scheduled job?
A cross-check job would introduce up to 1 hour of delay and require deduplication logic for "already notified this flash deal". Doing it inline at insertion time is simpler and more immediate.

### Affected files
- `src/models/price_history.py` — add `source` column
- `src/trackers/utils.py` — extend `refresh_flash_deals()` with cross-check logic

---

## Feature 2: Keyword Search Optimization

### Approach
- **PChome**: keep existing JSON API search (fast, stable). Add an external link to each result card.
- **Momo**: replace unreliable Playwright search with a frontend redirect to Momo's search results page. Show a UI hint guiding users to copy and paste the product URL.

### Frontend Changes

**`SearchBar.tsx`**

When platform is `momo` and input is a keyword (not a URL):
- Open `https://www.momoshop.com.tw/search/searchShop.jsp?keyword=<keyword>` in a new tab.
- Display inline hint: `已在新視窗開啟 Momo 搜尋，找到商品後請複製連結貼回此處追蹤`
- Do NOT call `POST /api/products` with keyword for Momo.

When platform is `pchome` and input is a keyword:
- Continue existing API search flow unchanged.

**`track/page.tsx` — search result cards**

Add a small external link button to each PChome result card:
- Text: `在 PChome 查看 ↗`
- `href = result.url`, `target="_blank"`

### Backend Changes
None. `POST /api/products` with `keyword` for Momo platform can remain as-is (it will no longer be called for keywords from the frontend).

### Affected files
- `frontend/src/app/track/components/SearchBar.tsx` — Momo keyword → redirect
- `frontend/src/app/track/page.tsx` — add external link to PChome result cards

---

## Summary

| Feature | Backend | Frontend | DB migration |
|---------|---------|----------|--------------|
| Flash deal → price history + notify | `trackers/utils.py` + `models/price_history.py` | None | Add nullable `source` column to `price_history` |
| Keyword search optimization | None | `SearchBar.tsx`, `track/page.tsx` | None |
