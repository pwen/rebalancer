# Portfolio Rebalancer

Aggregate holdings from Fidelity & Schwab, classify by region & category using AI, set target allocations, and get rebalancing recommendations.

## Quick Start

```bash
# 1. Start Postgres
make db

# 2. Install deps & init migrations
uv sync
uv run flask db init
uv run flask db migrate -m "initial"
uv run flask db upgrade

# 3. Set your OpenAI API key in .env (optional — fallback classifier works without it)
# OPENAI_API_KEY=sk-...

# 4. Run
make run
# → http://localhost:5002
```

## Usage

1. **Export CSVs** from Fidelity (Positions → Download) and/or Schwab (Positions → Export)
2. **Upload** each CSV on the web UI
3. **View breakdown** — AI classifies each ticker by region & category
4. **Set targets** — define your desired allocation percentages
5. **Rebalance** — see exactly what to buy and sell

## Commands

| Command | Description |
|---------|-------------|
| `make run` | Run Flask dev server (port 5002) |
| `make db` | Start Postgres container |
| `make migrate m="msg"` | Create migration |
| `make upgrade` | Apply migrations |
| `make docker-up` | Run full stack in Docker |
| `make docker-down` | Stop Docker containers |

## Deploy to Railway

Same pattern as Kexian — push to GitHub, connect repo on Railway, add PostgreSQL database, set `DATABASE_URL` and `OPENAI_API_KEY` variables.
