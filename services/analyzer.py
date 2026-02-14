"""
Portfolio AI analysis — sends holdings data to Perplexity and returns
a formatted analysis covering risk, world-view, geopolitics, and macro themes.
"""

import json
import os
import re

from openai import OpenAI


ANALYSIS_PROMPT = """\
You are a thoughtful investment strategist writing for a sophisticated individual investor \
(not an institution). Analyze this portfolio and write a clear, narrative-style analysis \
in **Markdown**. No jargon like "equity beta" or "duration risk" — instead, explain what \
the portfolio *says* about the investor's view of the world, as if you're talking to a \
smart friend over coffee.

Structure:

First, write one punchy paragraph (<50 words, NO header) that names the portfolio's \
overall philosophy in plain language (e.g. "macro-aware, inflation-hedged, value-oriented") \
and its single biggest bet. This is the opening — just start writing, no "## Big Picture" header.

## What This Portfolio Is Saying
One single flowing paragraph, under 120 words (not bullet points). Compare to a standard \
60/40 US-centric portfolio and explain the key tilts: what you're overweight, underweight, \
and *why* that matters. Weave together the macro thesis, the geopolitical stance, what the \
cash/treasury buffer means strategically, and the commodity/precious metals/crypto angle. \
Frame it as "this portfolio is built for a world where X, Y, Z happen."

Then, without any header, write one final paragraph (under 75 words) on the main risk — \
what would need to happen in the world for this allocation to look bad? Start it with \
something like "The risk is…" or "Where this falls apart is…" — no "## The Risk" header.

Write conversationally but with authority. Do NOT reference specific percentages, \
dollar amounts, or numbers — use plain English descriptors like "nearly half", \
"a significant allocation", "heavily overweight", "a small slice" instead. \
Do NOT include any citation references like [1], [2], [5] etc. No footnotes or sources.

Portfolio data:
"""


def generate_analysis(breakdown: dict) -> str:
    """
    Call Perplexity to generate a portfolio analysis.

    Args:
        breakdown: the full breakdown dict from compute_breakdown()

    Returns:
        Markdown-formatted analysis string
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not api_key or api_key.startswith("pplx-your"):
        return "**API key not configured.** Set PERPLEXITY_API_KEY in your .env file."

    # Build a compact data summary for the prompt
    total = breakdown["total_value"]
    lines = [f"Total portfolio value: ${total:,.2f}\n"]

    lines.append("### Category Breakdown")
    for cat, info in breakdown["by_category"].items():
        lines.append(f"- {cat}: {info['pct']}% (${info['value']:,.0f})")

    lines.append("\n### Region Breakdown")
    for reg, info in breakdown["by_region"].items():
        lines.append(f"- {reg}: {info['pct']}% (${info['value']:,.0f})")

    lines.append("\n### Top Holdings (by value)")
    for h in breakdown["holdings"][:25]:
        cat_str = ", ".join(f"{k} {v}%" for k, v in (h.get("category") or {}).items())
        reg_str = ", ".join(f"{k} {v}%" for k, v in (h.get("region") or {}).items())
        lines.append(
            f"- {h['ticker']}: ${h['value']:,.0f} ({h['pct']}%) "
            f"| type={h.get('security_type', '?')} | cat=[{cat_str}] | reg=[{reg_str}]"
        )

    data_text = "\n".join(lines)
    prompt = ANALYSIS_PROMPT + data_text

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.perplexity.ai",
    )

    try:
        response = client.chat.completions.create(
            model="sonar",
            messages=[
                {
                    "role": "system",
                    "content": "You are a portfolio analyst. Return well-formatted Markdown. No JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"**Analysis failed:** {e}"
