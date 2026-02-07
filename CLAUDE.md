# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install dependencies (including dev tools)
pip install -e ".[dev]"

# Install Playwright browsers (required for crawlers)
playwright install chromium

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_models.py -v

# Run a specific test
pytest tests/test_models.py::test_create_bank -v

# Lint (ruff may not be on PATH — use python3 -m ruff if bare ruff fails)
ruff check src/ tests/
ruff check --fix src/ tests/
ruff format src/ tests/
```

## CLI Commands

```bash
# Initialize database
python -m src.cli init

# Seed bank data
python -m src.cli seed

# Run crawler (all banks or specific)
python -m src.cli crawl
python -m src.cli crawl --bank ctbc

# Start API server (port 8000)
python -m src.cli serve
```

Supported bank codes: `ctbc` (中國信託), `esun` (玉山銀行), `sinopac` (永豐銀行), `cathay` (國泰世華), `fubon` (富邦銀行), `taishin` (台新銀行), `firstbank` (第一銀行), `hncb` (華南銀行), `megabank` (兆豐銀行), `ubot` (聯邦銀行)

## Frontend Commands

```bash
# Install frontend dependencies (requires Node.js 18+)
cd frontend && npm install

# Start frontend dev server (port 3000, proxies API to localhost:8000)
npm run dev --prefix frontend

# Build frontend
npm run build --prefix frontend
```

## Docker Commands

```bash
docker-compose up --build                                           # development
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up  # production
```

The entrypoint script (`scripts/entrypoint.sh`) auto-runs `init` and `seed` on first launch.

## Architecture Overview

### Dual Database Session Pattern

The codebase uses **two different SQLAlchemy session patterns**:

1. **Async sessions** (`AsyncSession`) — FastAPI API endpoints via `get_db()` dependency in `src/db/database.py`
2. **Sync sessions** (`Session`) — Crawlers, scheduler jobs, and the recommendation engine. Created by replacing `+aiosqlite` with empty string in the database URL.

The recommend API endpoint (`src/api/recommend.py`) is a notable case: the route handler is async but internally creates a sync session because `RecommendationEngine` uses sync ORM queries.

### Crawler System

All 10 bank crawlers in `src/crawlers/banks/` inherit from `BaseCrawler` (`src/crawlers/base.py`) and implement:
- `fetch_cards() -> List[CreditCard]`
- `fetch_promotions() -> List[Promotion]`

The base class provides upsert logic (`save_card`, `save_promotion`) that deduplicates by composite keys (bank_id+name for cards, card_id+title for promotions).

**Two crawler types exist:**
- 9 web crawlers (esun, cathay, sinopac, fubon, taishin, firstbank, hncb, megabank, ubot) — use Playwright with `playwright-stealth` for JavaScript-rendered pages. Each manages its own browser lifecycle via `_init_browser()` / `_close_browser()`.
- 1 API crawler (ctbc) — fetches JSON directly via `httpx`, no browser needed. Uses `_parse_card_json()` instead of `_extract_features()`.

**Shared utilities** (`src/crawlers/utils.py`) — all 9 web crawlers delegate feature extraction to `extract_common_features(text)`, which returns a dict with keys like `reward_type`, `mobile_pay`, `lounge_access`, `streaming`, `dining`, etc. Promotions are extracted via `extract_promotions_from_text()` which returns `title`, `description`, `reward_rate`, `reward_type`, `reward_limit`, `min_spend`.

To add a new bank crawler:
1. Create `src/crawlers/banks/<code>.py` following existing patterns (e.g., `esun.py`)
2. Set class attributes: `bank_name`, `bank_code`, `base_url`
3. Implement `fetch_cards()` and `fetch_promotions()`, using shared utilities from `utils.py`
4. Register in `src/crawlers/banks/__init__.py` and `src/cli.py`

### Key Data Conventions

- `lounge_access` is the canonical feature key (not `lounge`). `scoring.py` has a backward-compat fallback checking both.
- `CreditCard.features` is a JSON column — a flat dict of booleans/strings populated by `extract_common_features()`.
- `Promotion` has `reward_type` ("cashback"/"miles"/"points"), `reward_limit` (int), and `min_spend` (int) columns — these are populated by crawlers via utility functions.

### Recommendation Engine

Located in `src/recommender/`. Weighted scoring:
- `scoring.py` — Individual calculators: reward (40%), feature (25%), promotion (15%), annual_fee_roi (20%)
- `engine.py` — Orchestrates filtering, scoring, ranking, and reason generation

`estimate_monthly_reward()` is a shared helper used by both `calculate_reward_score()` and `calculate_annual_fee_roi()`. It iterates spending categories, finds the best promotion rate per category, and applies reward limits.

`calculate_feature_score()` maps 14 user preference strings to card feature checks. Supported preferences: `no_annual_fee`, `airport_pickup`, `lounge_access`, `cashback`, `miles`, `high_reward`, `travel`, `dining`, `mobile_pay`, `online_shopping`, `new_cardholder`, `installment`, `streaming`, `travel_insurance`.

### API Endpoints

Defined in `src/api/cards.py` and `src/api/recommend.py`, mounted via `src/api/router.py`:

- `GET /api/banks` — List all banks
- `GET /api/banks/{bank_id}` — Single bank
- `GET /api/cards?page=&size=&bank_id=&card_type=` — Paginated card list
- `GET /api/cards/{card_id}` — Card detail
- `GET /api/cards/{card_id}/promotions` — Card promotions
- `POST /api/recommend` — Get personalized recommendations (body: `spending_habits`, `monthly_amount`, `preferences`, `limit`)
- `GET /health` — Health check
- `GET /api/admin/status` — Scheduler status (requires `X-Admin-Key` header in production)

### Scheduler

APScheduler background jobs (`src/scheduler/runner.py`), all using sync sessions:

| Schedule | Job |
|----------|-----|
| Daily 02:00 | Promotion crawl |
| Weekly Sun 03:00 | Card info crawl |
| Daily 04:00 | Cleanup expired promotions |
| Daily 06:00 | Notify new promotions (Telegram/Discord) |
| Daily 09:00 | Notify expiring promotions (3-day warning) |

### Notifications

`src/notifications/` supports Telegram and Discord channels. `NotificationDispatcher` handles deduplication via `NotificationLog` (unique constraint on type+reference_id+channel). Configured via `.env` settings (`TELEGRAM_BOT_TOKEN`, `DISCORD_WEBHOOK_URL`, etc.).

### Frontend

Next.js app (App Router) in `frontend/`. Pages: homepage (`/`), card listing (`/cards`), recommendation wizard (`/recommend`). Design system uses Outfit + Noto Sans TC fonts, glassmorphism, and Tailwind CSS v4.

### Configuration

Settings loaded from `.env` via pydantic-settings (`src/config.py`). Key settings: `ENVIRONMENT` (development/production), `DATABASE_URL`, `CORS_ORIGINS` (comma-separated, empty = localhost only), `ADMIN_API_KEY`, `NOTIFICATION_ENABLED`, crawler delay/retry tuning.

### Ruff Configuration

Line length 100, target Python 3.9+, selected rules: E (errors), F (pyflakes), I (isort), N (naming), W (warnings). Configured in `pyproject.toml`.
