"""
Parse Schwab CSV position exports.

Typical Schwab CSV format:
- First line(s) may have account info
- Header row: Symbol, Name, Quantity, Price, Market Value, ...
- May have a "Totals" row at the bottom
"""

import csv
import io
import re

# Money-market / cash-equivalent tickers where price = $1.00 and shares = value
_CASH_TICKERS = {"SPAXX", "FDRXX", "FCASH", "SWVXX", "FZFXX", "SPRXX"}


def parse_schwab_csv(file_content: str) -> list[dict]:
    """Parse a Schwab positions CSV and return normalized holdings."""
    holdings = []

    lines = file_content.strip().splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Symbol" in line and ("Quantity" in line or "Market Value" in line):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            "Could not find header row in Schwab CSV. "
            "Expected columns: Symbol, Name, Quantity, Price, Market Value"
        )

    # Extract account name from lines before header if present
    account = ""
    for line in lines[:header_idx]:
        line = line.strip().strip('"')
        if line and not line.startswith(","):
            account = line
            break

    csv_text = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(csv_text))

    for row in reader:
        ticker = (row.get("Symbol") or "").strip().strip('"')
        if not ticker:
            continue

        # Skip totals and summary rows (keep SWVXX — it's a money market fund)
        if ticker.upper() in (
            "ACCOUNT TOTAL",
            "CASH & CASH INVESTMENTS",
            "CASH",
        ):
            continue
        if "total" in ticker.lower():
            continue

        name = (row.get("Description") or row.get("Name") or "").strip().strip('"')
        quantity = _parse_number(
            row.get("Qty (Quantity)") or row.get("Quantity") or row.get("Shares") or "0"
        )
        price = _parse_number(row.get("Price") or row.get("Last Price") or "0")
        value = _parse_number(
            row.get("Mkt Val (Market Value)") or row.get("Market Value")
            or row.get("Current Value") or "0"
        )

        cost_basis = _parse_number(
            row.get("Cost Basis") or row.get("Cost Basis Total") or "0"
        )

        if value == 0 and quantity == 0:
            continue

        # Money-market funds: price is always $1, shares = dollar value
        if ticker.upper() in _CASH_TICKERS and value and (not quantity or not price):
            price = 1.0
            quantity = value
        if ticker.upper() in _CASH_TICKERS and not cost_basis and value:
            cost_basis = value

        holdings.append(
            {
                "ticker": ticker.upper(),
                "name": name,
                "quantity": quantity,
                "price": price,
                "value": value,
                "cost_basis": cost_basis,
                "brokerage": "schwab",
                "account": account,
            }
        )

    return holdings


def _parse_number(s: str) -> float:
    """Parse a number string, stripping $, commas, quotes, etc."""
    if not s:
        return 0.0
    s = s.strip().strip('"')
    s = re.sub(r"[$,]", "", s)
    s = s.replace("--", "0").replace("N/A", "0")
    try:
        return float(s)
    except ValueError:
        return 0.0
