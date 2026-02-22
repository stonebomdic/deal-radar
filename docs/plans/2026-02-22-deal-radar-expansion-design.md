# Deal Radar 擴充設計文件

**日期：** 2026-02-22
**範疇：** 在現有信用卡爬蟲系統上增加 PChome / Momo 購物平台的商品價格追蹤與限時瘋搶功能，並深度整合信用卡推薦引擎

---

## 一、Repo 重命名

- **舊名：** `credit-card-crawler`
- **新名：** `deal-radar`
- **調整範疇：**
  - GitHub repo 名稱
  - `docker-compose.yml` service 名稱
  - `README.md` 標題與描述
  - Python package 內部 `src/` 結構**維持不動**

---

## 二、架構方向

採用 **Monorepo 擴充（方案 A）**：在現有 repo 內直接擴充，新增 `src/trackers/` 模組，共用現有 DB、排程、通知、推薦引擎基礎設施。

---

## 三、資料模型

### `tracked_products`（使用者追蹤的特定商品）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | int PK | |
| `platform` | str | `pchome` / `momo` |
| `product_id` | str | 平台原生商品 ID |
| `name` | str | 商品名稱 |
| `url` | str | 商品頁 URL |
| `target_price` | int | 使用者設定的目標價（選填） |
| `is_active` | bool | 是否仍在追蹤中 |
| `created_at` / `updated_at` | datetime | |

### `price_history`（價格快照，定期爬取）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | int PK | |
| `product_id` | int FK → tracked_products | |
| `price` | int | 當時價格（元） |
| `original_price` | int | 原價（有折扣時） |
| `in_stock` | bool | 是否有貨 |
| `snapshot_at` | datetime | 快照時間 |

**價格歷史設計原則：** 每次排程爬取後插入新紀錄（不覆蓋），保留完整時間序列供走勢圖使用。

### `flash_deals`（限時瘋搶列表，主動抓取）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | int PK | |
| `platform` | str | `pchome` / `momo` |
| `product_name` | str | |
| `product_url` | str | |
| `sale_price` | int | 限時價格 |
| `original_price` | int | |
| `discount_rate` | float | 折扣率 |
| `start_at` / `end_at` | datetime | 活動期間 |
| `created_at` | datetime | |

---

## 四、爬蟲架構（Trackers）

新增 `src/trackers/` 模組，與現有 `src/crawlers/` 並列：

```
src/
├── crawlers/        # 現有：銀行信用卡資料
└── trackers/        # 新增：購物平台商品追蹤
    ├── base.py          # BaseTracker 抽象基底
    ├── platforms/
    │   ├── pchome.py    # PChome 爬蟲（優先 JSON API）
    │   └── momo.py      # Momo 爬蟲（Playwright + stealth）
    └── utils.py         # 共用解析工具
```

### BaseTracker 介面

```python
class BaseTracker:
    async def search_products(self, keyword: str) -> List[ProductResult]
    async def fetch_product_by_url(self, url: str) -> ProductResult
    async def fetch_price(self, product: TrackedProduct) -> PriceSnapshot
    async def fetch_flash_deals(self) -> List[FlashDeal]
```

### 爬蟲策略

| 平台 | 商品搜尋 | 價格爬取 | 限時瘋搶 |
|------|---------|---------|---------|
| **PChome** | 官方搜尋 API（JSON） | 商品 API（JSON） | 24h 購物 API |
| **Momo** | Playwright 渲染搜尋頁 | Playwright 商品頁 | 限時特賣頁面 |

### 排程整合（新增至 `src/scheduler/runner.py`）

| 排程 | 工作 |
|------|------|
| 每 30 分鐘 | 爬取所有 active 商品最新價格，寫入 price_history |
| 每 1 小時 | 爬取 PChome/Momo 限時瘋搶列表，更新 flash_deals |
| 每次爬取後 | 比對價格變動，若降價或達目標價則觸發通知 |

---

## 五、深度整合——「最佳結帳卡」推薦

### 新增 `calculate_shopping_reward()` 至 `src/recommender/scoring.py`

```python
def calculate_shopping_reward(
    card: CreditCard,
    platform: str,       # "pchome" / "momo"
    amount: int,         # 購買金額
) -> RewardResult:
    # 1. 查詢該卡對此平台是否有專屬 promotion
    # 2. 套用 estimate_monthly_reward() 邏輯
    # 3. 回傳實際回饋金額 + 說明文字
```

### 通知訊息格式

```
🔔 價格警示：Sony WH-1000XM5 耳機

📉 PChome 降價：$8,490 → $6,990（折 82 折）

💳 最佳結帳方式：
  1. 國泰 Cube 卡：回饋 5% = -$350，實付 $6,640
  2. 玉山 Pi 卡：回饋 3% = -$210，實付 $6,780
  3. 台新 @GoGo 卡：回饋 2.8% = -$196，實付 $6,794

🔗 前往購買
```

### 整合流程

```
價格爬取 → 偵測降價
    ↓
呼叫推薦引擎（platform="pchome", amount=商品價格）
    ↓
取得 Top 3 信用卡 + 回饋試算
    ↓
組合通知訊息 → Telegram / Discord
```

### 新增 API 端點

| 端點 | 說明 |
|------|------|
| `GET /api/products` | 列出所有追蹤中商品 |
| `POST /api/products` | 新增追蹤商品（URL 或關鍵字搜尋） |
| `DELETE /api/products/{id}` | 停止追蹤商品 |
| `GET /api/products/{id}/history` | 商品價格歷史 |
| `GET /api/flash-deals` | 當前限時瘋搶列表（含最佳結帳卡） |

---

## 六、前端頁面

沿用現有設計系統（Outfit + Noto Sans TC、glassmorphism、Tailwind CSS v4）。

### 新增頁面

**`/track`（商品追蹤）**
- 搜尋欄：輸入關鍵字或貼上 PChome/Momo 商品 URL
- 搜尋結果列表：商品名稱、平台、現價、加入追蹤按鈕
- 我的追蹤清單：當前價格、歷史最低價、價格走勢折線圖
- 可設定目標價（到達時通知）

**`/deals`（限時瘋搶）**
- 分頁切換：PChome / Momo
- 商品卡片：商品圖、名稱、折扣率、剩餘時間倒數
- 每張卡片顯示「最佳結帳卡 Top 1」，點擊展開 Top 3
- 支援按折扣率 / 剩餘時間排序

### 導覽列

```
首頁 / 信用卡 / 推薦 / 商品追蹤 / 限時瘋搶
```

---

## 七、通知管道

沿用現有 Telegram / Discord 雙管道，共用 `NotificationDispatcher` 與 `NotificationLog` 去重機制。新增通知類型：
- `price_drop`：商品降價
- `target_price_reached`：到達使用者設定目標價
- `flash_deal_new`：新限時瘋搶上架

---

## 八、不在範疇內（YAGNI）

- Email 通知
- Web Push 通知
- 使用者帳號系統（商品追蹤暫以 API 操作為主）
- 跨平台比價（同一商品在 PChome vs Momo 的比較）
