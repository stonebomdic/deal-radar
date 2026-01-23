# 信用卡爬蟲系統設計文件

> 建立日期：2026-01-23

## 專案概述

建立一個台灣信用卡資訊爬蟲系統，涵蓋：
- 信用卡優惠資訊爬取
- 信用卡產品比較
- 特定通路優惠查詢
- 根據需求綜合評比推薦

## 技術決策

| 項目 | 選擇 | 原因 |
|-----|------|------|
| 語言 | Python 3.11+ | 豐富的爬蟲生態系，適合資料處理 |
| API 框架 | FastAPI | 高效能、自動產生 API 文件 |
| 資料庫 | SQLite | 輕量、無需額外設定，適合初期 |
| 爬蟲 | requests + BeautifulSoup + Playwright | 混合策略，兼顧效率和彈性 |
| 排程 | APScheduler | 內建於應用程式，簡單直接 |

## 專案結構

```
credit-card-crawler/
├── src/
│   ├── crawlers/           # 爬蟲模組
│   │   ├── base.py         # 爬蟲基類
│   │   ├── banks/          # 各銀行爬蟲
│   │   │   ├── cathay.py   # 國泰世華
│   │   │   ├── ctbc.py     # 中國信託
│   │   │   ├── esun.py     # 玉山銀行
│   │   │   └── ...
│   │   └── utils.py        # 爬蟲工具函式
│   │
│   ├── models/             # 資料模型
│   │   ├── card.py         # 信用卡
│   │   ├── promotion.py    # 優惠活動
│   │   └── category.py     # 消費類別
│   │
│   ├── api/                # FastAPI 路由
│   │   ├── cards.py        # 信用卡查詢
│   │   ├── promotions.py   # 優惠查詢
│   │   └── recommend.py    # 推薦 API
│   │
│   ├── recommender/        # 推薦引擎
│   │   ├── engine.py       # 推薦邏輯
│   │   └── scoring.py      # 評分計算
│   │
│   └── db/                 # 資料庫
│       ├── database.py     # 連線管理
│       └── migrations/     # 資料庫遷移
│
├── scheduler/              # 排程任務
├── tests/                  # 測試
├── data/                   # SQLite 檔案
└── config/                 # 設定檔
```

## 資料模型

### Bank（銀行）
| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | Integer | 主鍵 |
| name | String | 銀行名稱 |
| code | String | 銀行代碼 |
| website | String | 官網網址 |
| logo_url | String | Logo 圖片網址 |

### CreditCard（信用卡）
| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | Integer | 主鍵 |
| bank_id | Integer | 外鍵：銀行 |
| name | String | 卡片名稱 |
| card_type | String | 卡片等級（御璽/白金/無限卡） |
| annual_fee | Integer | 年費 |
| annual_fee_waiver | String | 免年費條件 |
| image_url | String | 卡面圖片 |
| apply_url | String | 申請連結 |
| min_income | Integer | 最低年收入要求 |
| features | JSON | 權益（機場接送、貴賓室等） |
| base_reward_rate | Float | 基本回饋率 |
| updated_at | DateTime | 更新時間 |

### Promotion（優惠活動）
| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | Integer | 主鍵 |
| card_id | Integer | 外鍵：信用卡 |
| title | String | 優惠標題 |
| description | Text | 優惠說明 |
| category | String | 消費類別 |
| reward_type | String | 回饋類型（現金/點數/里程） |
| reward_rate | Float | 回饋率 |
| reward_limit | Integer | 回饋上限 |
| min_spend | Integer | 最低消費門檻 |
| start_date | Date | 開始日期 |
| end_date | Date | 結束日期 |
| terms | Text | 注意事項 |
| source_url | String | 來源網址 |

### Category（消費類別）
| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | Integer | 主鍵 |
| name | String | 類別名稱 |
| icon | String | 圖示 |
| keywords | JSON | 比對關鍵字 |

## 爬蟲架構

### 基類設計
```python
class BaseCrawler:
    bank_name: str
    bank_code: str

    def fetch_cards(self) -> List[CreditCard]
    def fetch_promotions(self) -> List[Promotion]
    def parse_card(self, html) -> CreditCard
    def parse_promotion(self, html) -> Promotion
    def save_to_db(self, data)
```

### 爬取策略
| 資料類型 | 更新頻率 | 爬取方式 |
|---------|---------|---------|
| 信用卡基本資訊 | 每週 | 靜態爬取 (requests) |
| 優惠活動 | 每日 | 依網站決定 |
| 通路優惠 | 每日 | 靜態爬取為主 |

### 反爬蟲對策
- 隨機延遲：請求間隔 2-5 秒
- User-Agent 輪換
- 必要時使用 Playwright 模擬瀏覽器
- 重試機制：失敗時最多重試 3 次

## 推薦引擎

### 輸入參數
```json
{
  "spending_habits": {
    "dining": 0.25,
    "online_shopping": 0.35,
    "transport": 0.15,
    "overseas": 0.10,
    "others": 0.15
  },
  "monthly_amount": 30000,
  "preferences": ["no_annual_fee", "cashback"]
}
```

### 推薦流程
1. **篩選階段**：排除不符合基本條件的卡
2. **評分階段**：計算回饋分數、權益分數、優惠分數
3. **排序輸出**：綜合分數排序，回傳 Top N 推薦

### 評分公式
```
總分 = 回饋分數 × 0.5 + 權益分數 × 0.3 + 優惠分數 × 0.2

回饋分數 = Σ (消費類別比例 × 該類別回饋率 × 月消費金額)
權益分數 = 符合偏好數量 / 總偏好數量 × 100
優惠分數 = 當前有效優惠數量 × 優惠品質權重
```

## API 設計

### 信用卡查詢
- `GET /api/cards` - 列出所有信用卡（分頁）
- `GET /api/cards/{id}` - 單張卡片詳細資訊
- `GET /api/cards/search?q=...` - 搜尋信用卡
- `GET /api/banks` - 列出所有銀行
- `GET /api/banks/{id}/cards` - 特定銀行的所有卡片

### 優惠查詢
- `GET /api/promotions` - 列出所有優惠（分頁）
- `GET /api/promotions/{id}` - 單一優惠詳情
- `GET /api/promotions/category/{cat}` - 依類別查詢優惠
- `GET /api/cards/{id}/promotions` - 特定卡片的優惠

### 推薦系統
- `POST /api/recommend` - 取得個人化推薦

### 管理
- `POST /api/admin/crawl/{bank}` - 手動觸發特定銀行爬蟲
- `GET /api/admin/status` - 系統狀態與最後更新時間

### 共用參數
- 分頁：`?page=1&size=20`
- 排序：`?sort=reward_rate&order=desc`
- 篩選：`?category=dining&bank=ctbc`

## 排程任務

| 任務 | 頻率 | 時間 | 內容 |
|-----|------|------|------|
| 優惠更新 | 每日 | 02:00 | 爬取優惠活動、清理過期資料 |
| 卡片更新 | 每週 | 週日 03:00 | 更新信用卡基本資訊 |
| 健康檢查 | 每小時 | - | 檢查資料庫連線、記錄狀態 |

## 依賴套件

### 爬蟲
- requests
- beautifulsoup4
- playwright
- lxml

### API
- fastapi
- uvicorn
- pydantic

### 資料庫
- sqlalchemy
- alembic
- aiosqlite

### 排程
- apscheduler

### 工具
- python-dotenv
- loguru
- pytest
- httpx
- ruff
- pre-commit

## 目標銀行（初期）

1. 中國信託
2. 國泰世華
3. 玉山銀行
4. 台新銀行
5. 富邦銀行
6. 永豐銀行
7. 台北富邦
8. 聯邦銀行
9. 第一銀行
10. 華南銀行

## 下一步

1. 建立專案基礎架構
2. 設計並建立資料庫 schema
3. 實作第一個銀行爬蟲（建議從中國信託開始）
4. 建立基本 API
5. 實作推薦引擎
6. 逐步加入其他銀行爬蟲
