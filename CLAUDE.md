# CLAUDE.md – Project Notes

## Package Management
- **Use `uv`** for all dependency management (`uv sync`, `uv run`)
- **Never use `pip` or `pip3`** directly — they will fail due to PEP 668
- After adding a dependency to `pyproject.toml`, run `uv sync` to install it
- To run any Python command: `uv run python ...`

## Python
- The system Python is `python3` (Homebrew, `/opt/homebrew/bin/python3`)
- There is no `python` alias — always use `python3` or `uv run python`

## Common Commands (see Makefile)
- `make run` — start Flask dev server on port 5002
- `make db` — start Postgres container only
- `make migrate m="description"` — generate a new Alembic migration
- `make upgrade` — apply pending migrations
- `make downgrade` — roll back last migration
- `make docker-up` — run full stack (app + db) in Docker
- `make docker-down` — stop Docker containers
- `make docker-build` — rebuild Docker images (no cache)

## Database
- PostgreSQL 16 via Docker Compose (port 5433 → 5432)
- Credentials: `rebalancer / rebalancer`, database: `rebalancer`
- Start with `make db` or `docker compose up db -d`
- Default local URL: `postgresql://rebalancer:rebalancer@localhost:5433/rebalancer`

## Stack
- Flask 3.x, Flask-SQLAlchemy, Flask-Migrate (Alembic)
- Perplexity AI (via OpenAI client, `PERPLEXITY_API_KEY`) for ticker classification & portfolio analysis
- yfinance for live price fetching
- Frontend: single-file vanilla JS SPA (`static/js/app.js`, `templates/index.html`, `static/css/style.css`)
- Deployment: Railway (Dockerfile-based), gunicorn

## Environment Variables
- `DATABASE_URL` — PostgreSQL connection string (auto-fixes `postgres://` → `postgresql://` for Railway)
- `PERPLEXITY_API_KEY` — Perplexity API key for AI classification and analysis (optional; fallback classifier works without it)

## Models (`models/`)
- **Snapshot** — point-in-time CSV upload: snapshot_date, brokerage (fidelity/schwab), filename, holding_count, total_value; has-many Holdings
- **Holding** — single position: snapshot_id (FK), ticker, name, quantity, price, value, cost_basis, brokerage, account
- **TickerClassification** — cached AI classification: ticker (unique), name, region_breakdown (JSON), category_breakdown (JSON), source (ai/manual/builtin/fallback)
- **TargetAllocation** — user-defined targets: dimension (region/category), label, target_pct; unique on (dimension, label)
- **PortfolioAnalysis** — persisted AI analysis: snapshot_date, analysis (text), created_at; class methods `get_for_date()`, `save_for_date()`

## API Routes (all in `app.py`)
- `GET /` — serve SPA
- `POST /api/upload` — upload CSV (form: file, brokerage, snapshot_date); auto-classifies new tickers & generates AI analysis
- `GET /api/snapshots` — list all snapshots
- `DELETE /api/snapshots/<id>` — delete snapshot + holdings
- `PATCH /api/snapshots/<id>` — update snapshot metadata (date)
- `GET /api/snapshot-dates` — distinct dates for date picker
- `GET /api/holdings?date=` — holdings for a date (or latest)
- `GET /api/dimensions` — valid categories & regions
- `GET /api/breakdown?date=` — aggregated portfolio breakdown by region & category
- `POST /api/analyze?date=` — generate & persist AI analysis
- `GET /api/classifications` — all ticker classifications
- `PUT /api/classifications/<ticker>` — manual classification update
- `POST /api/classifications/<ticker>/reclassify` — force AI reclassification
- `GET /api/targets` — target allocations
- `PUT /api/targets` — save targets (dimension + allocations array, must sum to 100)
- `GET /api/rebalance?date=` — rebalancing recommendations
- `GET /api/live-prices?date=` — live prices vs snapshot prices
- `GET /api/live-breakdown?date=` — breakdown using live prices
- `GET /api/live-rebalance?date=` — rebalance using live prices
- `GET /api/trends` — time-series data across all snapshot dates

## Services (`services/`)
- **classifier.py** — `classify_tickers()`, `reclassify_ticker()`; priority: DB cache → builtin map → Perplexity AI → fallback (US/Other)
- **classifications_config.py** — `VALID_CATEGORIES` (18 GICS-style + special), `VALID_REGIONS` (US/DM/EM/Global), `BUILTIN_MAP` (loaded from `etf_classifications.json`), `CLASSIFICATION_PROMPT`
- **etf_classifications.json** — curated ETF/fund classification map; see `prompts/REGENERATE_ETF_MAP.md` for regeneration
- **rebalancer.py** — `compute_breakdown()` (aggregate holdings by region/category), `compute_rebalance()` (drift from targets), `suggest_trades()` (human-readable recommendations)
- **analyzer.py** — `generate_analysis()` — sends breakdown to Perplexity for narrative portfolio analysis (Markdown)
- **prices.py** — `fetch_live_prices()` (yfinance), `apply_live_prices()` (compute deltas vs snapshot)

## Parsers (`parsers/`)
- **fidelity.py** — `parse_fidelity_csv()` — parses Fidelity position exports; handles BOM, cash-equivalent tickers (SPAXX, FDRXX, etc.)
- **schwab.py** — `parse_schwab_csv()` — parses Schwab position exports; extracts account name from pre-header lines

## Classification Dimensions
- **Regions**: US, DM (Developed ex-US), EM (Emerging), Global
- **Categories**: Short-Term Treasuries, Long-Term Treasuries, Cash, Technology, Financials, Health Care, Consumer Discretionary, Communication Services, Industrials, Consumer Staples, Energy, Utilities, Real Estate, Materials, Precious Metals, Commodities, Cryptocurrency, Other

## Key Patterns
- All routes in `app.py` (no separate routes/ directory) — monolithic route file
- Snapshot-date-based architecture: `?date=YYYY-MM-DD` param selects snapshot; omit for latest
- Latest = most recent snapshot per brokerage (Fidelity + Schwab combined)
- Live prices create virtual Holding objects (not persisted) for breakdown computation
- Multi-stage Docker build with `uv` for dependency management
- Startup command: `flask db upgrade && gunicorn` (auto-migrate on deploy)
