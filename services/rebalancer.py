"""
Rebalancing engine.

Given current holdings with classifications and target allocations,
compute the drift and recommend trades to rebalance.
"""

from models.holding import Holding
from models.classification import TickerClassification
from models.target import TargetAllocation


def compute_breakdown(holdings: list[Holding]) -> dict:
    """
    Compute the aggregated portfolio breakdown by region and category.

    Returns:
        {
            "total_value": 100000,
            "by_region": {"US": {"value": 60000, "pct": 60.0}, ...},
            "by_category": {"Equities": {"value": 80000, "pct": 80.0}, ...},
            "holdings": [
                {"ticker": "VTI", "value": 50000, "region": {...}, "category": {...}},
                ...
            ]
        }
    """
    classifications = {
        c.ticker: c
        for c in TickerClassification.query.all()
    }

    total_value = sum(h.value for h in holdings)
    if total_value == 0:
        return {
            "total_value": 0,
            "by_region": {},
            "by_category": {},
            "holdings": [],
        }

    region_totals = {}
    category_totals = {}
    holding_details = []

    # Aggregate same-ticker holdings across brokerages
    ticker_values = {}
    for h in holdings:
        if h.ticker not in ticker_values:
            ticker_values[h.ticker] = {
                "ticker": h.ticker,
                "name": h.name,
                "value": 0,
                "quantity": 0,
                "brokerages": set(),
            }
        ticker_values[h.ticker]["value"] += h.value
        ticker_values[h.ticker]["quantity"] += h.quantity
        ticker_values[h.ticker]["brokerages"].add(h.brokerage)

    for ticker, info in ticker_values.items():
        value = info["value"]
        classification = classifications.get(ticker)

        if classification:
            region_bd = classification.region_breakdown or {"US": 100}
            category_bd = classification.category_breakdown or {"Equities": 100}
        else:
            region_bd = {"US": 100}
            category_bd = {"Equities": 100}

        # Distribute value across regions
        for region, pct in region_bd.items():
            region_totals[region] = region_totals.get(region, 0) + value * pct / 100

        # Distribute value across categories
        for cat, pct in category_bd.items():
            category_totals[cat] = category_totals.get(cat, 0) + value * pct / 100

        holding_details.append(
            {
                "ticker": ticker,
                "name": info["name"],
                "value": round(value, 2),
                "pct": round(value / total_value * 100, 2),
                "quantity": info["quantity"],
                "brokerages": sorted(info["brokerages"]),
                "region": region_bd,
                "category": category_bd,
            }
        )

    # Sort by value descending
    holding_details.sort(key=lambda x: x["value"], reverse=True)

    return {
        "total_value": round(total_value, 2),
        "by_region": {
            k: {"value": round(v, 2), "pct": round(v / total_value * 100, 2)}
            for k, v in sorted(region_totals.items(), key=lambda x: -x[1])
        },
        "by_category": {
            k: {"value": round(v, 2), "pct": round(v / total_value * 100, 2)}
            for k, v in sorted(category_totals.items(), key=lambda x: -x[1])
        },
        "holdings": holding_details,
    }


def compute_rebalance(breakdown: dict, dimension: str = "category") -> list[dict]:
    """
    Compute rebalancing trades needed to reach target allocations.

    Args:
        breakdown: output of compute_breakdown()
        dimension: 'region' or 'category'

    Returns:
        List of dicts:
        [
            {
                "label": "Equities",
                "current_pct": 80.0,
                "target_pct": 60.0,
                "current_value": 80000,
                "target_value": 60000,
                "drift": 20.0,
                "action": "sell",
                "amount": 20000
            },
            ...
        ]
    """
    total_value = breakdown["total_value"]
    if total_value == 0:
        return []

    current = breakdown[f"by_{dimension}"]
    targets = {
        t.label: t.target_pct
        for t in TargetAllocation.query.filter_by(dimension=dimension).all()
    }

    if not targets:
        return []

    # Collect all labels from both current and targets
    all_labels = sorted(set(list(current.keys()) + list(targets.keys())))

    result = []
    for label in all_labels:
        current_pct = current.get(label, {}).get("pct", 0) if isinstance(current.get(label), dict) else 0
        current_value = current.get(label, {}).get("value", 0) if isinstance(current.get(label), dict) else 0
        target_pct = targets.get(label, 0)
        target_value = total_value * target_pct / 100
        drift = round(current_pct - target_pct, 2)
        amount = round(abs(current_value - target_value), 2)

        result.append(
            {
                "label": label,
                "current_pct": round(current_pct, 2),
                "target_pct": round(target_pct, 2),
                "current_value": round(current_value, 2),
                "target_value": round(target_value, 2),
                "drift": drift,
                "action": "sell" if drift > 0.5 else ("buy" if drift < -0.5 else "hold"),
                "amount": amount,
            }
        )

    # Sort by absolute drift descending
    result.sort(key=lambda x: abs(x["drift"]), reverse=True)
    return result


def suggest_trades(breakdown: dict) -> dict:
    """
    Suggest specific trades to rebalance both region and category.

    Returns:
        {
            "region": [rebalance items...],
            "category": [rebalance items...],
            "summary": "Sell $X of US Equities, Buy $Y of EM Equities..."
        }
    """
    region_rebal = compute_rebalance(breakdown, "region")
    category_rebal = compute_rebalance(breakdown, "category")

    # Build human-readable summary
    actions = []
    for item in category_rebal:
        if item["action"] == "sell":
            actions.append(f"Sell ${item['amount']:,.0f} of {item['label']}")
        elif item["action"] == "buy":
            actions.append(f"Buy ${item['amount']:,.0f} of {item['label']}")

    for item in region_rebal:
        if item["action"] == "sell":
            actions.append(f"Reduce {item['label']} by ${item['amount']:,.0f}")
        elif item["action"] == "buy":
            actions.append(f"Increase {item['label']} by ${item['amount']:,.0f}")

    return {
        "region": region_rebal,
        "category": category_rebal,
        "summary": "; ".join(actions) if actions else "Portfolio is balanced!",
    }
