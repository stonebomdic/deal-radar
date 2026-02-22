# Deal Radar

台灣信用卡優惠 + 購物商場好康追蹤系統

## 功能

- 爬取台灣 10 家主要銀行信用卡資訊
- 信用卡優惠活動查詢與分類
- 根據消費習慣智慧推薦最適合的信用卡
- PChome / Momo 商品價格追蹤與到價通知
- 即時特賣（Flash Deals）整合
- RESTful API 提供資料查詢
- Next.js 前端介面
- 排程自動更新信用卡資料與商品價格
- Telegram / Discord 推播通知
- Docker 容器化部署

## 支援銀行

| 銀行代碼 | 銀行名稱 |
|----------|----------|
| `ctbc` | 中國信託 |
| `esun` | 玉山銀行 |
| `taishin` | 台新銀行 |
| `cathay` | 國泰世華 |
| `fubon` | 富邦銀行 |
| `sinopac` | 永豐銀行 |
| `firstbank` | 第一銀行 |
| `hncb` | 華南銀行 |
| `megabank` | 兆豐銀行 |
| `ubot` | 聯邦銀行 |

## 快速開始

### 環境需求

- Python 3.9+
- Node.js 20+
- pip

### 安裝步驟

```bash
# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 安裝 Python 依賴
pip install -e ".[dev]"

# 安裝 Playwright 瀏覽器（爬蟲與 Momo 追蹤器需要）
playwright install chromium

# 安裝前端依賴
cd frontend && npm install && cd ..
```

### 初始化與執行

```bash
# 初始化資料庫
python3 -m src.cli init

# 匯入銀行種子資料
python3 -m src.cli seed

# 執行爬蟲（所有銀行或指定銀行）
python3 -m src.cli crawl
python3 -m src.cli crawl --bank esun

# 啟動後端 API 服務
python3 -m src.cli serve

# 啟動前端開發伺服器（另開終端）
npm run dev --prefix frontend
```

服務啟動後：
- 後端 API: http://localhost:8000
- 前端介面: http://localhost:3000
- API 文件: http://localhost:8000/docs

## Docker 部署

```bash
# 開發環境
docker-compose up --build

# 生產環境
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## CLI 指令

```bash
python3 -m src.cli <command>
```

| 指令 | 說明 |
|------|------|
| `init` | 初始化資料庫表格結構 |
| `seed` | 匯入預設銀行資料 |
| `crawl` | 執行爬蟲（`--bank` 指定銀行） |
| `serve` | 啟動 API 服務 |

## API 端點

### 信用卡與銀行

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/health` | 健康檢查 |
| GET | `/api/banks` | 取得所有銀行列表 |
| GET | `/api/banks/{bank_id}` | 取得單一銀行資訊 |
| GET | `/api/cards` | 取得信用卡列表（支援分頁、篩選） |
| GET | `/api/cards/{card_id}` | 取得單一信用卡詳情 |
| GET | `/api/cards/{card_id}/promotions` | 取得信用卡優惠活動 |
| POST | `/api/recommend` | 取得信用卡推薦 |

### 商品追蹤

| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/products` | 取得追蹤中的商品列表 |
| POST | `/api/products` | 新增追蹤商品（`url` 或 `keyword`） |
| DELETE | `/api/products/{id}` | 停止追蹤商品 |
| GET | `/api/products/{id}/history` | 取得商品價格歷史 |
| GET | `/api/flash-deals` | 取得即時特賣（`?platform=` 可篩選） |

### 查詢參數

`GET /api/cards` 支援以下查詢參數：
- `page` - 頁碼（預設 1）
- `size` - 每頁筆數（預設 20，最大 100）
- `bank_id` - 篩選特定銀行
- `card_type` - 篩選卡片類型

### 推薦 API 範例

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "spending_habits": {
      "dining": 0.3,
      "online_shopping": 0.3,
      "travel": 0.2,
      "convenience_store": 0.1,
      "supermarket": 0.1
    },
    "monthly_amount": 30000,
    "preferences": ["no_annual_fee", "high_reward"],
    "limit": 5
  }'
```

## 推薦引擎

系統使用加權評分演算法，綜合考量以下因素：

| 評分項目 | 權重 | 說明 |
|----------|------|------|
| 回饋評分 | 40% | 根據消費類別計算預期回饋 |
| 功能評分 | 25% | 卡片特色與用戶偏好匹配度 |
| 年費 ROI | 20% | 年費與預期回饋的投資報酬率 |
| 優惠評分 | 15% | 當前優惠活動加成 |

### 支援的消費類別

`dining`, `online_shopping`, `travel`, `overseas`, `convenience_store`, `supermarket`, `department_store`, `transport`, `mobile_pay`, `entertainment`, `insurance`, `medical`

### 支援的偏好設定

`no_annual_fee`, `high_reward`, `airport_lounge`, `travel_insurance`, `mileage`, `mobile_payment`, `streaming`, `ecommerce`

## 專案結構

```
deal-radar/
├── src/
│   ├── api/                 # FastAPI 路由與 schemas
│   ├── crawlers/            # 爬蟲模組
│   │   ├── banks/           # 各銀行爬蟲實作（10 家）
│   │   ├── base.py          # 爬蟲基類
│   │   └── utils.py         # 共用工具（文字清理、優惠擷取）
│   ├── trackers/            # 電商價格追蹤模組
│   │   ├── platforms/       # PChome / Momo 追蹤器
│   │   ├── base.py          # 追蹤器基類
│   │   └── utils.py         # 價格快照、特賣刷新工具
│   ├── db/                  # 資料庫模組
│   ├── models/              # ORM 模型
│   ├── notifications/       # Telegram / Discord 推播
│   ├── recommender/         # 推薦引擎
│   │   ├── engine.py        # 推薦邏輯
│   │   └── scoring.py       # 評分函式
│   ├── scheduler/           # 排程系統
│   │   ├── jobs.py          # 排程任務實作
│   │   └── runner.py        # APScheduler 設定
│   ├── cli.py               # CLI 入口
│   ├── config.py            # 設定檔
│   └── main.py              # FastAPI 應用程式入口
├── frontend/                # Next.js 前端
│   ├── src/
│   │   ├── app/             # App Router 頁面（/, /cards, /recommend, /track, /deals）
│   │   └── components/      # React 元件
│   └── package.json
├── tests/                   # 測試檔案
├── docker-compose.yml       # Docker 配置
├── pyproject.toml           # Python 專案設定
├── CLAUDE.md                # Claude Code 開發指南
└── README.md
```

## 開發

### 執行測試

```bash
python3 -m pytest tests/ -v
```

### 程式碼檢查

```bash
python3 -m ruff check src/ tests/
python3 -m ruff check --fix src/ tests/
python3 -m ruff format src/ tests/
```

## 環境變數

可透過環境變數或 `.env` 檔案設定：

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `DATABASE_URL` | 資料庫連線字串 | `sqlite+aiosqlite:///./data/credit_cards.db` |
| `ENVIRONMENT` | 執行環境 | `development` |
| `API_HOST` | API 監聽位址 | `0.0.0.0` |
| `API_PORT` | API 監聽埠號 | `8000` |
| `CORS_ORIGINS` | 允許的 CORS 來源（逗號分隔） | 空（僅 localhost） |
| `ADMIN_API_KEY` | 管理端點金鑰 | — |
| `NOTIFICATION_ENABLED` | 是否啟用推播通知 | `false` |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | — |
| `DISCORD_WEBHOOK_URL` | Discord Webhook URL | — |

## License

MIT
