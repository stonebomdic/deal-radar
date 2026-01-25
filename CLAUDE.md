# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install dependencies (including dev tools)
pip install -e ".[dev]"

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
- `save_card(card_data)` - Upsert logic for credit cards
- `save_promotion(card, promo_data)` - Upsert logic for promotions
- `run()` - Orchestrates the crawl workflow

To add a new bank crawler, create a file in `src/crawlers/banks/` following the pattern in `ctbc.py`.

### CTBC Crawler - Static Data Mode

The CTBC website uses Akamai Bot Manager anti-bot protection, which makes dynamic crawling difficult. The `CtbcCrawler` uses a `use_static_data = True` flag to load pre-defined card and promotion data from constants in `ctbc.py`.

To update CTBC card data:
1. Edit `CTBC_CARDS_DATA` in `src/crawlers/banks/ctbc.py`
2. Edit `CTBC_PROMOTIONS_DATA` for promotions
3. Run `python -m src.cli crawl --bank ctbc` to refresh the database

The static data includes 10 major CTBC credit cards with their features, reward rates, and annual fee information.

### Recommendation Engine

The recommendation system (`src/recommender/`) uses a weighted scoring approach:
- `scoring.py` - Individual score calculators (reward, feature, promotion scores)
- `engine.py` - Orchestrates filtering, scoring, and ranking

Scores are weighted: reward (50%) + feature (30%) + promotion (20%)

### Scheduler

APScheduler runs in the background with the FastAPI app (`src/scheduler/`):
- Daily 02:00 - Promotion crawl
- Daily 04:00 - Cleanup expired promotions
- Weekly Sunday 03:00 - Card info crawl

Jobs use sync database sessions since APScheduler runs in a separate thread.
