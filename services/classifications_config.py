"""
Static classification config: categories, regions, and AI prompt.

ETF classifications live in etf_classifications.json (same directory).
To regenerate, ask AI to output fresh JSON matching that format.
"""

import json
from pathlib import Path

# ── Valid dimensions ──────────────────────────────────────────────────────

VALID_CATEGORIES = [
    "Short-Term Treasuries",
    "Long-Term Treasuries",
    "Cash",
    "Technology",
    "Financials",
    "Health Care",
    "Consumer Discretionary",
    "Communication Services",
    "Industrials",
    "Consumer Staples",
    "Energy",
    "Utilities",
    "Real Estate",
    "Materials",
    "Precious Metals",
    "Commodities",
    "Cryptocurrency",
    "Other",
]

VALID_REGIONS = ["US", "DM", "EM", "Global"]


# ── Builtin ETF / fund classification map (loaded from JSON) ─────────────

_JSON_PATH = Path(__file__).parent / "etf_classifications.json"

def _load_builtin_map() -> dict:
    """Load ETF classification map from JSON, skipping the _meta key."""
    with open(_JSON_PATH) as f:
        data = json.load(f)
    data.pop("_meta", None)
    return data

BUILTIN_MAP = _load_builtin_map()


# ── AI prompt template ───────────────────────────────────────────────────

CLASSIFICATION_PROMPT = """You are a financial data expert. For each ticker below, classify it using ONLY these allowed values.

Allowed REGIONS (percentages must sum to 100):
  - US: United States
  - DM: Developed Markets ex-US (Europe, Japan, Australia, Canada, etc.)
  - EM: Emerging Markets (China, India, Brazil, etc.)
  - Global: Cannot be attributed to a single region (e.g., commodities, gold)

Allowed CATEGORIES — GICS-style sectors + special categories (percentages must sum to 100):
  - Technology (software, semiconductors, hardware)
  - Financials (banks, insurance, capital markets)
  - Health Care (pharma, biotech, medical devices)
  - Consumer Discretionary (retail, autos, apparel, restaurants)
  - Communication Services (media, telecom, social platforms)
  - Industrials (aerospace, defense, machinery, transport)
  - Consumer Staples (food, beverages, household products)
  - Energy (oil & gas, pipelines, energy services)
  - Utilities (electric, gas, water utilities)
  - Real Estate (REITs, real estate services)
  - Materials (chemicals, mining, construction materials)
  - Precious Metals (gold, silver, platinum, mining stocks for precious metals)
  - Commodities (oil, agriculture, broad commodity baskets — NOT mining equities)
  - Cryptocurrency (Bitcoin, Ethereum, crypto funds)
  - Short-Term Treasuries (US Treasury bonds with maturity < 3 years, T-bills, short TIPS)
  - Long-Term Treasuries (US Treasury bonds with maturity > 3 years, intermediate/long TIPS)
  - Cash (money market funds, cash equivalents)
  - Other (anything that doesn't fit above — corporate bonds, international bonds, etc.)

Rules:
- Use ONLY the category and region keys listed above, exactly as spelled.
- Percentages in each breakdown must sum to exactly 100.
- For ETFs, base the breakdown on underlying holdings sector composition.
- For individual stocks, classify by the company's primary business sector.
- Precious metals mining stocks (GDX, GDXJ) go under Precious Metals, not Materials.
- Energy MLPs go under Energy.

Return ONLY valid JSON — no markdown, no explanation. Format:
{
  "TICKER": {
    "region": {"US": 60, "DM": 30, "EM": 10},
    "category": {"Technology": 100}
  }
}

Tickers to classify:
"""
