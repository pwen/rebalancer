"""
Parse Fidelity CSV position exports.

Typical Fidelity CSV header:
Account Number,Account Name,Symbol,Description,Quantity,Last Price,Current Value
"""

import csv
import io
import re

# Money-market / cash-equivalent tickers where price = $1.00 and shares = value
_CASH_TICKERS = {"SPAXX", "FDRXX", "FCASH", "SWVXX", "FZFXX", "SPRXX"}


def parse_fidelity_csv(file_content: str) -> list[dict]:
    """Parse a Fidelity positions CSV and return normalized holdings."""
    holdings = []

    # Fidelity CSVs sometimes have a BOM or header junk — skip until we find the header row
    lines = file_content.strip().splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if "Symbol" in line and ("Quantity" in line or "Current Value" in line):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            "Could not find header row in Fidelity CSV. "
            "Expected columns: Symbol, Description, Quantity, Last Price, Current Value"
        )

    csv_text = "\n".join(lines[header_idx:])
    reader = csv.DictReader(io.StringIO(csv_text))

    for row in reader:
        ticker = (row.get("Symbol") or "").strip().strip("*")
        if not ticker or ticker.startswith("***"):
            continue

        # Skip non-position rows
        if ticker.upper() in ("CASH", "PENDING ACTIVITY", "CORE"):
            continue
        if "pending" in ticker.lower():
            continue

        name = (row.get("Description") or row.get("Security Description") or "").strip()
        quantity = _parse_number(row.get("Quantity") or row.get("Shares") or "0")
        price = _parse_number(row.get("Last Price") or row.get("Last Price Change") or "0")
        value = _parse_number(row.get("Current Value") or row.get("Market Value") or "0")

        # Skip rows with no value
        if value == 0 and quantity == 0:
            continue

        # Money-market funds: price is always $1, shares = dollar value
        if ticker.upper() in _CASH_TICKERS and value and (not quantity or not price):
            price = 1.0
            quantity = value

        cost_basis = _parse_number(
            row.get("Cost Basis Total") or row.get("Cost Basis") or "0"
        )

        # For money-market funds, cost basis equals the current value
        if ticker.upper() in _CASH_TICKERS and not cost_basis and value:
            cost_basis = value

        account = (row.get("Account Name") or row.get("Account Number") or "").strip()

        holdings.append(
            {
                "ticker": ticker.upper(),
                "name": name,
                "quantity": quantity,
                "price": price,
                "value": value,
                "cost_basis": cost_basis,
                "brokerage": "fidelity",
                "account": account,
            }
        )

    return holdings


def _parse_number(s: str) -> float:
    """Parse a number string, stripping $, commas, etc."""
    if not s:
        return 0.0
    s = s.strip()
    s = re.sub(r"[$,]", "", s)
    s = s.replace("--", "0")
    try:
        return float(s)
    except ValueError:
        return 0.0
