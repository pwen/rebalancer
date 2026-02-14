"""
Live price service using yfinance.

Fetches current market prices for a list of tickers and applies them
to snapshot holdings to compute a live portfolio valuation.
"""

import yfinance as yf


def fetch_live_prices(tickers: list[str]) -> dict[str, float]:
    """
    Fetch current market prices for a list of tickers.

    Returns:
        dict mapping ticker -> current price (or None if unavailable)
    """
    if not tickers:
        return {}

    # yfinance handles batching internally
    data = yf.Tickers(" ".join(tickers))

    prices = {}
    for ticker in tickers:
        try:
            info = data.tickers[ticker].fast_info
            # Use last price (most recent trade price)
            price = getattr(info, "last_price", None)
            if price is None:
                price = getattr(info, "previous_close", None)
            prices[ticker] = round(price, 4) if price else None
        except Exception:
            prices[ticker] = None

    return prices


def apply_live_prices(holdings, live_prices: dict[str, float]) -> list[dict]:
    """
    Take snapshot holdings and apply live prices to compute updated values.

    Args:
        holdings: list of Holding model instances
        live_prices: dict of ticker -> current price

    Returns:
        List of holding-like dicts with updated price/value, plus
        original snapshot price for comparison.
    """
    updated = []
    for h in holdings:
        live_price = live_prices.get(h.ticker)
        if live_price and h.quantity:
            new_value = round(h.quantity * live_price, 2)
            price_change = round(live_price - (h.price or 0), 4)
            price_change_pct = (
                round(price_change / h.price * 100, 2)
                if h.price and h.price > 0
                else 0
            )
        else:
            # Fallback to snapshot price if live price unavailable
            live_price = h.price
            new_value = h.value
            price_change = 0
            price_change_pct = 0

        updated.append({
            "ticker": h.ticker,
            "name": h.name,
            "quantity": h.quantity,
            "snapshot_price": h.price,
            "live_price": live_price,
            "snapshot_value": h.value,
            "live_value": new_value,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "brokerage": h.brokerage,
            "account": h.account,
        })

    return updated
