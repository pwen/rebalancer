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

Structure (use these exact headers):

### The Big Picture
One punchy paragraph (~50 words) that names the portfolio's overall philosophy in plain \
language (e.g. "macro-aware, inflation-hedged, value-oriented") and its single biggest bet.

### What This Portfolio Is Saying
Write 2-3 flowing paragraphs (not bullet points). Compare to a standard 60/40 US-centric \
portfolio and explain the key tilts: what you're overweight, underweight, and *why* that \
matters. Weave together:
- The macro thesis (inflation, rates, recession, dollar strength/weakness)
- The geopolitical stance (EM conviction, commodity-producer nations, de-dollarization, \
  US exceptionalism vs global diversification)
- What the cash/treasury buffer means strategically (optionality, dry powder, timing)
- The commodity/precious metals/crypto angle

Frame it as "this portfolio is built for a world where X, Y, Z happen" — paint the \
scenario the investor is positioning for.

### The Risk of Being Wrong
One paragraph on the main scenario where this portfolio underperforms. Be specific — \
what would need to happen in the world for this allocation to look bad? \
(e.g. "US exceptionalism persists, tech keeps grinding higher, and you sit in cash \
watching the S&P rally another 20%")

Write conversationally but with authority. Reference actual percentages from the data \
to ground your analysis, but don't list holdings. Total ~250-300 words.

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
