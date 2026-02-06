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

# Lint code
ruff check src/ tests/

# Auto-fix lint issues
ruff check --fix src/ tests/

# Format code
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

# Start API server
python -m src.cli serve
```

Supported bank codes: `ctbc` (中國信託), `esun` (玉山銀行), `sinopac` (永豐銀行), `cathay` (國泰世華), `fubon` (富邦銀行), `taishin` (台新銀行), `firstbank` (第一銀行), `hncb` (華南銀行), `megabank` (兆豐銀行), `ubot` (聯邦銀行)

## Frontend Commands

```bash
# Install frontend dependencies (requires Node.js 18+)
cd frontend && npm install

# Start frontend dev server
npm run dev --prefix frontend

# Build frontend
npm run build --prefix frontend
```

The frontend is a Next.js 14+ app with Tailwind CSS. It proxies API requests to `localhost:8000`.

## Docker Commands

```bash
# Build and run with docker-compose
docker-compose up --build

# Production mode
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
```

## Architecture Overview

### Dual Database Session Pattern

The codebase uses **two different SQLAlchemy session patterns**:

1. **Async sessions** (`AsyncSession`) - Used by FastAPI API endpoints via dependency injection (`get_db()` in `src/db/database.py`)
2. **Sync sessions** (`Session`) - Used by crawlers and scheduler jobs, created via `create_engine()` with the sync database URL (replacing `+aiosqlite` with empty string)

When working with crawlers or scheduled jobs, always use sync sessions. When working with API endpoints, use async sessions.

### Crawler Pattern

All bank crawlers inherit from `BaseCrawler` (`src/crawlers/base.py`) and must implement:
- `fetch_cards() -> List[CreditCard]`
- `fetch_promotions() -> List[Promotion]`

The base class provides:
- `bank` property - Auto-creates or fetches the Bank record
- `save_card(card_data)` - Upsert logic for credit cards (deduplicates by bank_id + name, validates card names)
- `save_promotion(card, promo_data)` - Upsert logic for promotions (deduplicates by card_id + title)
- `run()` - Orchestrates the crawl workflow
- `is_valid_card_name(name)` - Filters out invalid card names (navigation items, overview pages)

All crawlers use **Playwright with `playwright-stealth`** for browser automation. Each crawler manages its own browser lifecycle with `_init_browser()` / `_close_browser()` methods.

**Crawler Utilities** (`src/crawlers/utils.py`): Shared functions for text cleaning and promotion extraction:
- `clean_text()` - Removes noise characters and normalizes whitespace
- `extract_promotions_from_text()` - Unified promotion extraction with noise filtering
- `detect_promotion_category()` - Categorizes promotions (dining, transport, overseas, etc.)

To add a new bank crawler:
1. Create a file in `src/crawlers/banks/` following the pattern in existing crawlers (e.g., `esun.py`)
2. Set class attributes: `bank_name`, `bank_code`, `base_url`
3. Implement `fetch_cards()` and `fetch_promotions()`, using shared utilities from `utils.py`
4. Register the crawler in `src/crawlers/banks/__init__.py` and `src/cli.py`

### Recommendation Engine

The recommendation system (`src/recommender/`) uses a weighted scoring approach:
- `scoring.py` - Individual score calculators (reward, feature, promotion, annual_fee_roi)
- `engine.py` - Orchestrates filtering, scoring, and ranking

Scoring weights: reward (40%) + feature (25%) + promotion (15%) + annual_fee_roi (20%)

Key functions:
- `estimate_monthly_reward()` - Shared helper for calculating expected rewards with limit awareness
- `calculate_total_score()` - Combines all score components

### Scheduler

APScheduler runs in the background with the FastAPI app (`src/scheduler/`):
- Daily 02:00 - Promotion crawl
- Daily 04:00 - Cleanup expired promotions
- Weekly Sunday 03:00 - Card info crawl

Jobs use sync database sessions since APScheduler runs in a separate thread.
