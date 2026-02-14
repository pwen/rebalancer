"""
Ticker classifier.

Classification priority:
  1. DB cache  — already classified, skip
  2. BUILTIN_MAP — curated ETF/fund mappings (source="builtin")
  3. Perplexity AI — only for unknown tickers (source="ai")
  4. Fallback — defaults to US / Other (source="fallback")

Categories, regions, ETF mappings, and the AI prompt are in
services/classifications_config.py.
"""

import json
import os
import re
from datetime import datetime, timezone

from openai import OpenAI

from models import db
from models.classification import TickerClassification
from services.classifications_config import (
    BUILTIN_MAP,
    CLASSIFICATION_PROMPT,
    VALID_CATEGORIES,
    VALID_REGIONS,
)


def classify_tickers(tickers_with_names: list[tuple[str, str]]) -> dict:
    """
    Classify tickers. Uses DB cache → builtin map → AI → fallback.

    Args:
        tickers_with_names: list of (ticker, name) tuples

    Returns:
        dict mapping ticker -> {"region": {...}, "category": {...}, "source": ...}
    """
    if not tickers_with_names:
        return {}

    tickers = [t for t, _ in tickers_with_names]

    # 1) Check DB cache
    existing = TickerClassification.query.filter(
        TickerClassification.ticker.in_(tickers)
    ).all()
    existing_map = {c.ticker: c for c in existing}

    to_classify = [
        (t, n) for t, n in tickers_with_names if t not in existing_map
    ]

    if to_classify:
        # 2) Resolve from builtin map first
        need_ai = []
        for ticker, name in to_classify:
            if ticker in BUILTIN_MAP:
                _save_classification(ticker, name, BUILTIN_MAP[ticker], source="builtin")
            else:
                need_ai.append((ticker, name))

        # 3) Call AI for remaining unknowns
        if need_ai:
            api_key = os.environ.get("PERPLEXITY_API_KEY", "")
            has_key = api_key and not api_key.startswith("pplx-your")

            if has_key:
                ai_results = _call_perplexity(need_ai, api_key)
            else:
                ai_results = {}

            for ticker, name in need_ai:
                raw = ai_results.get(ticker)
                if raw:
                    result = _normalize(raw)
                    _save_classification(ticker, name, result, source="ai")
                else:
                    _save_classification(ticker, name, _default_classification(), source="fallback")

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


def _save_classification(ticker: str, name: str, data: dict, source: str):
    """Merge a classification into the DB (not yet committed)."""
    classification = TickerClassification(
        ticker=ticker,
        name=name,
        region_breakdown=data.get("region", {"US": 100}),
        category_breakdown=data.get("category", {"Other": 100}),
        classified_at=datetime.now(timezone.utc),
        source=source,
    )
    db.session.merge(classification)


def _call_perplexity(tickers_with_names: list[tuple[str, str]], api_key: str) -> dict:
    """Call Perplexity API for unknown tickers. Returns raw parsed JSON."""
    ticker_list = "\n".join(
        f"- {ticker} ({name})" for ticker, name in tickers_with_names
    )
    prompt = CLASSIFICATION_PROMPT + ticker_list

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai",
    )

    try:
        response = client.chat.completions.create(
            model="sonar",
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. No markdown, no explanation."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        content = response.choices[0].message.content
        # Perplexity may wrap JSON in markdown code blocks
        if "```" in content:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                content = match.group(1).strip()
        return json.loads(content)
    except Exception as e:
        print(f"[classifier] Perplexity API error: {e}")
        return {}


def _normalize(data: dict) -> dict:
    """Validate and normalize a classification against allowed values."""
    region = {}
    for key in VALID_REGIONS:
        if key in data.get("region", {}):
            region[key] = data["region"][key]
    if not region:
        region = {"US": 100}
    else:
        total = sum(region.values())
        if total > 0 and total != 100:
            region = {k: round(v * 100 / total) for k, v in region.items()}

    category = {}
    for key in VALID_CATEGORIES:
        if key in data.get("category", {}):
            category[key] = data["category"][key]
    if not category:
        category = {"Other": 100}
    else:
        total = sum(category.values())
        if total > 0 and total != 100:
            category = {k: round(v * 100 / total) for k, v in category.items()}

    return {"region": region, "category": category}


def reclassify_ticker(ticker: str, name: str) -> dict:
    """Force reclassify a single ticker (delete cache and re-run AI)."""
    TickerClassification.query.filter_by(ticker=ticker).delete()
    db.session.commit()
    return classify_tickers([(ticker, name)])


def _default_classification():
    """Default classification for unknown tickers."""
    return {"region": {"US": 100}, "category": {"Other": 100}}
