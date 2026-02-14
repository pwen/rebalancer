"""
AI-powered ticker classifier using OpenAI.

Given a list of tickers, classifies each by:
  - Region breakdown: US, Developed Markets (DM), Emerging Markets (EM)
  - Category breakdown: Equities, Fixed Income, Metals, Commodities, Crypto,
                        Real Estate, Cash, etc.

Results are cached in the TickerClassification table.
"""

import json
import os
from datetime import datetime, timezone

from openai import OpenAI

from models import db
from models.classification import TickerClassification

CLASSIFICATION_PROMPT = """You are a financial data expert. For each investment ticker below, provide:
1. **Region breakdown** (percentages summing to 100):
   - US: United States equities/bonds
   - DM: Developed Markets ex-US (Europe, Japan, Australia, Canada, etc.)
   - EM: Emerging Markets (China, India, Brazil, etc.)
   - Global: Cannot be attributed to a single region (e.g., commodities, gold)

2. **Category breakdown** (percentages summing to 100):
   - Equities
   - Fixed Income
   - Metals (gold, silver, etc.)
   - Commodities (oil, agriculture, broad commodities)
   - Crypto
   - Real Estate (REITs)
   - Cash

For ETFs, base the breakdown on their underlying holdings composition.
For individual stocks, classify by the company's primary market and sector.

Return ONLY valid JSON — no markdown, no explanation. Format:
{
  "TICKER": {
    "region": {"US": 60, "DM": 30, "EM": 10},
    "category": {"Equities": 100}
  }
}

Tickers to classify:
"""


def classify_tickers(tickers_with_names: list[tuple[str, str]]) -> dict:
    """
    Classify a batch of tickers using OpenAI.

    Args:
        tickers_with_names: list of (ticker, name) tuples

    Returns:
        dict mapping ticker -> {"region": {...}, "category": {...}}
    """
    if not tickers_with_names:
        return {}

    # Check which tickers already have classifications
    tickers = [t for t, _ in tickers_with_names]
    existing = TickerClassification.query.filter(
        TickerClassification.ticker.in_(tickers)
    ).all()
    existing_map = {c.ticker: c for c in existing}

    # Find tickers that need classification
    to_classify = [
        (t, n) for t, n in tickers_with_names if t not in existing_map
    ]

    if to_classify:
        # Build the prompt
        ticker_list = "\n".join(
            f"- {ticker} ({name})" for ticker, name in to_classify
        )
        prompt = CLASSIFICATION_PROMPT + ticker_list

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key or api_key == "sk-your-key-here":
            # No API key — use fallback classification
            ai_results = _fallback_classify(to_classify)
        else:
            ai_results = _call_openai(prompt, api_key)

        # Save to database
        for ticker, name in to_classify:
            result = ai_results.get(ticker, _default_classification())
            classification = TickerClassification(
                ticker=ticker,
                name=name,
                region_breakdown=result.get("region", {"US": 100}),
                category_breakdown=result.get("category", {"Equities": 100}),
                classified_at=datetime.now(timezone.utc),
                source="ai" if api_key and api_key != "sk-your-key-here" else "fallback",
            )
            db.session.merge(classification)

        db.session.commit()

    # Reload all classifications
    all_classifications = TickerClassification.query.filter(
        TickerClassification.ticker.in_(tickers)
    ).all()

    return {
        c.ticker: {
            "region": c.region_breakdown,
            "category": c.category_breakdown,
            "source": c.source,
        }
        for c in all_classifications
    }


def _call_openai(prompt: str, api_key: str) -> dict:
    """Call OpenAI API and parse the response."""
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    return json.loads(content)


def reclassify_ticker(ticker: str, name: str) -> dict:
    """Force reclassify a single ticker (delete cache and re-run AI)."""
    TickerClassification.query.filter_by(ticker=ticker).delete()
    db.session.commit()
    return classify_tickers([(ticker, name)])


def _default_classification():
    """Default classification when AI is unavailable."""
    return {"region": {"US": 100}, "category": {"Equities": 100}}


def _fallback_classify(tickers_with_names: list[tuple[str, str]]) -> dict:
    """
    Simple rule-based fallback when no OpenAI key is configured.
    Covers common ETFs; defaults everything else to US Equities.
    """
    KNOWN = {
        # US Total Market
        "VTI": {"region": {"US": 100}, "category": {"Equities": 100}},
        "ITOT": {"region": {"US": 100}, "category": {"Equities": 100}},
        "SPTM": {"region": {"US": 100}, "category": {"Equities": 100}},
        "VOO": {"region": {"US": 100}, "category": {"Equities": 100}},
        "SPY": {"region": {"US": 100}, "category": {"Equities": 100}},
        "IVV": {"region": {"US": 100}, "category": {"Equities": 100}},
        "QQQ": {"region": {"US": 100}, "category": {"Equities": 100}},
        # International Developed
        "VXUS": {"region": {"DM": 78, "EM": 22}, "category": {"Equities": 100}},
        "VEA": {"region": {"DM": 100}, "category": {"Equities": 100}},
        "EFA": {"region": {"DM": 100}, "category": {"Equities": 100}},
        "IEFA": {"region": {"DM": 100}, "category": {"Equities": 100}},
        "IXUS": {"region": {"DM": 75, "EM": 25}, "category": {"Equities": 100}},
        # Emerging Markets
        "VWO": {"region": {"EM": 100}, "category": {"Equities": 100}},
        "EEM": {"region": {"EM": 100}, "category": {"Equities": 100}},
        "IEMG": {"region": {"EM": 100}, "category": {"Equities": 100}},
        # Bonds
        "BND": {"region": {"US": 100}, "category": {"Fixed Income": 100}},
        "AGG": {"region": {"US": 100}, "category": {"Fixed Income": 100}},
        "BNDX": {"region": {"DM": 70, "EM": 30}, "category": {"Fixed Income": 100}},
        "TLT": {"region": {"US": 100}, "category": {"Fixed Income": 100}},
        "VGIT": {"region": {"US": 100}, "category": {"Fixed Income": 100}},
        "TIPS": {"region": {"US": 100}, "category": {"Fixed Income": 100}},
        # Gold / Metals
        "GLD": {"region": {"Global": 100}, "category": {"Metals": 100}},
        "IAU": {"region": {"Global": 100}, "category": {"Metals": 100}},
        "SLV": {"region": {"Global": 100}, "category": {"Metals": 100}},
        "GLDM": {"region": {"Global": 100}, "category": {"Metals": 100}},
        # Commodities
        "DBC": {"region": {"Global": 100}, "category": {"Commodities": 100}},
        "GSG": {"region": {"Global": 100}, "category": {"Commodities": 100}},
        "PDBC": {"region": {"Global": 100}, "category": {"Commodities": 100}},
        # Real Estate
        "VNQ": {"region": {"US": 100}, "category": {"Real Estate": 100}},
        "VNQI": {"region": {"DM": 60, "EM": 40}, "category": {"Real Estate": 100}},
        "IYR": {"region": {"US": 100}, "category": {"Real Estate": 100}},
        # Crypto
        "GBTC": {"region": {"Global": 100}, "category": {"Crypto": 100}},
        "IBIT": {"region": {"Global": 100}, "category": {"Crypto": 100}},
        "ETHE": {"region": {"Global": 100}, "category": {"Crypto": 100}},
        "BITO": {"region": {"Global": 100}, "category": {"Crypto": 100}},
    }

    results = {}
    for ticker, name in tickers_with_names:
        if ticker in KNOWN:
            results[ticker] = KNOWN[ticker]
        else:
            # Default: assume US equity
            results[ticker] = _default_classification()

    return results
