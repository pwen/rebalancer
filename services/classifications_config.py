"""
Static classification config: categories, regions, sector weights, and ETF mappings.

Edit this file to add new ETFs or adjust sector breakdowns.
The classifier imports everything from here.
"""

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


# ── Sector-weight templates ──────────────────────────────────────────────
# Approximate sector breakdowns for broad index ETFs.
# Each dict sums to 100.

US_LARGE_CAP = {  # S&P 500 / Total Market
    "Technology": 30, "Financials": 13, "Health Care": 12,
    "Consumer Discretionary": 10, "Communication Services": 9,
    "Industrials": 9, "Consumer Staples": 6, "Energy": 4,
    "Utilities": 3, "Real Estate": 2, "Materials": 2,
}

US_SMALL_CAP = {
    "Industrials": 16, "Financials": 16, "Health Care": 14,
    "Technology": 12, "Consumer Discretionary": 10, "Real Estate": 7,
    "Energy": 5, "Materials": 5, "Consumer Staples": 4,
    "Utilities": 4, "Communication Services": 3, "Other": 4,
}

US_MID_CAP = {
    "Industrials": 16, "Technology": 14, "Financials": 13,
    "Consumer Discretionary": 12, "Health Care": 10, "Real Estate": 6,
    "Materials": 5, "Consumer Staples": 5, "Energy": 5,
    "Utilities": 5, "Communication Services": 4, "Other": 5,
}

NASDAQ_100 = {
    "Technology": 50, "Communication Services": 16,
    "Consumer Discretionary": 13, "Health Care": 7,
    "Industrials": 5, "Consumer Staples": 4, "Financials": 2,
    "Energy": 1, "Utilities": 1, "Other": 1,
}

EQUAL_WEIGHT_500 = {
    "Industrials": 14, "Financials": 13, "Health Care": 12,
    "Consumer Discretionary": 10, "Technology": 9, "Consumer Staples": 7,
    "Real Estate": 7, "Materials": 6, "Utilities": 6,
    "Energy": 5, "Communication Services": 5, "Other": 6,
}

DM_EQUITY = {  # Developed Markets ex-US
    "Financials": 19, "Industrials": 15, "Health Care": 11,
    "Consumer Discretionary": 11, "Technology": 10, "Consumer Staples": 9,
    "Materials": 7, "Energy": 5, "Communication Services": 4,
    "Utilities": 4, "Real Estate": 3, "Other": 2,
}

EM_EQUITY = {  # Emerging Markets
    "Technology": 22, "Financials": 22, "Consumer Discretionary": 13,
    "Communication Services": 9, "Materials": 7, "Energy": 6,
    "Industrials": 6, "Consumer Staples": 6, "Health Care": 4,
    "Utilities": 3, "Real Estate": 2,
}

INTL_EQUITY = {  # Total International (DM ~78% + EM ~22%)
    "Financials": 19, "Technology": 14, "Industrials": 13,
    "Consumer Discretionary": 12, "Health Care": 9, "Consumer Staples": 8,
    "Materials": 7, "Energy": 5, "Communication Services": 5,
    "Utilities": 4, "Real Estate": 2, "Other": 2,
}

GLOBAL_EQUITY = {  # ACWI / VT (US ~60% + DM ~28% + EM ~12%)
    "Technology": 25, "Financials": 15, "Health Care": 10,
    "Consumer Discretionary": 11, "Industrials": 10,
    "Communication Services": 7, "Consumer Staples": 7,
    "Energy": 5, "Materials": 4, "Utilities": 3, "Real Estate": 2, "Other": 1,
}


# ── Builtin ETF / fund classification map ────────────────────────────────
# ~120 common ETFs with sector-level breakdowns.
# To add a new ETF, just add an entry here.

BUILTIN_MAP = {
    # ── US Broad Market (Large Cap) ───────────────────────────────────
    "VTI":  {"region": {"US": 100}, "category": US_LARGE_CAP},
    "ITOT": {"region": {"US": 100}, "category": US_LARGE_CAP},
    "SPTM": {"region": {"US": 100}, "category": US_LARGE_CAP},
    "VOO":  {"region": {"US": 100}, "category": US_LARGE_CAP},
    "SPY":  {"region": {"US": 100}, "category": US_LARGE_CAP},
    "IVV":  {"region": {"US": 100}, "category": US_LARGE_CAP},
    "DIA":  {"region": {"US": 100}, "category": US_LARGE_CAP},
    "SCHB": {"region": {"US": 100}, "category": US_LARGE_CAP},
    "SCHX": {"region": {"US": 100}, "category": US_LARGE_CAP},
    "RSP":  {"region": {"US": 100}, "category": EQUAL_WEIGHT_500},
    "QQQ":  {"region": {"US": 100}, "category": NASDAQ_100},
    "QQQM": {"region": {"US": 100}, "category": NASDAQ_100},

    # ── US Small / Mid Cap ────────────────────────────────────────────
    "IJR":  {"region": {"US": 100}, "category": US_SMALL_CAP},
    "SCHA": {"region": {"US": 100}, "category": US_SMALL_CAP},
    "VTWO": {"region": {"US": 100}, "category": US_SMALL_CAP},
    "IWM":  {"region": {"US": 100}, "category": US_SMALL_CAP},
    "VB":   {"region": {"US": 100}, "category": US_SMALL_CAP},
    "SCHM": {"region": {"US": 100}, "category": US_MID_CAP},
    "MDY":  {"region": {"US": 100}, "category": US_MID_CAP},
    "VO":   {"region": {"US": 100}, "category": US_MID_CAP},

    # ── US Sector ETFs ────────────────────────────────────────────────
    "XLK":  {"region": {"US": 100}, "category": {"Technology": 100}},
    "XLF":  {"region": {"US": 100}, "category": {"Financials": 100}},
    "XLV":  {"region": {"US": 100}, "category": {"Health Care": 100}},
    "XLY":  {"region": {"US": 100}, "category": {"Consumer Discretionary": 100}},
    "XLC":  {"region": {"US": 100}, "category": {"Communication Services": 100}},
    "XLI":  {"region": {"US": 100}, "category": {"Industrials": 100}},
    "XLP":  {"region": {"US": 100}, "category": {"Consumer Staples": 100}},
    "XLE":  {"region": {"US": 100}, "category": {"Energy": 100}},
    "XLU":  {"region": {"US": 100}, "category": {"Utilities": 100}},
    "XLRE": {"region": {"US": 100}, "category": {"Real Estate": 100}},
    "FENY": {"region": {"US": 100}, "category": {"Energy": 100}},
    "XOP":  {"region": {"US": 100}, "category": {"Energy": 100}},
    "AMLP": {"region": {"US": 100}, "category": {"Energy": 100}},

    # ── Global / World Equities ───────────────────────────────────────
    "VT":   {"region": {"US": 60, "DM": 28, "EM": 12}, "category": GLOBAL_EQUITY},
    "ACWI": {"region": {"US": 60, "DM": 28, "EM": 12}, "category": GLOBAL_EQUITY},

    # ── International Developed (DM) ─────────────────────────────────
    "VEA":  {"region": {"DM": 100}, "category": DM_EQUITY},
    "EFA":  {"region": {"DM": 100}, "category": DM_EQUITY},
    "IEFA": {"region": {"DM": 100}, "category": DM_EQUITY},
    "SCHF": {"region": {"DM": 100}, "category": DM_EQUITY},
    "VXUS": {"region": {"DM": 78, "EM": 22}, "category": INTL_EQUITY},
    "IXUS": {"region": {"DM": 75, "EM": 25}, "category": INTL_EQUITY},
    "VIGI": {"region": {"DM": 80, "EM": 20}, "category": INTL_EQUITY},

    # DM Country ETFs
    "EWS":  {"region": {"DM": 100}, "category": {
        "Financials": 35, "Industrials": 15, "Real Estate": 15,
        "Technology": 10, "Communication Services": 10,
        "Consumer Discretionary": 5, "Health Care": 5, "Consumer Staples": 3, "Utilities": 2,
    }},
    "EWJ":  {"region": {"DM": 100}, "category": {
        "Industrials": 20, "Consumer Discretionary": 16, "Technology": 16,
        "Financials": 10, "Health Care": 8, "Communication Services": 8,
        "Materials": 7, "Consumer Staples": 7, "Real Estate": 3,
        "Utilities": 3, "Energy": 2,
    }},
    "EWG":  {"region": {"DM": 100}, "category": {
        "Industrials": 20, "Financials": 18, "Consumer Discretionary": 12,
        "Technology": 12, "Health Care": 10, "Materials": 8,
        "Utilities": 5, "Consumer Staples": 5, "Communication Services": 5,
        "Energy": 3, "Other": 2,
    }},
    "EWU":  {"region": {"DM": 100}, "category": {
        "Financials": 20, "Consumer Staples": 14, "Health Care": 12,
        "Energy": 12, "Industrials": 10, "Materials": 8,
        "Communication Services": 5, "Consumer Discretionary": 5,
        "Utilities": 5, "Technology": 5, "Other": 4,
    }},
    "EWA":  {"region": {"DM": 100}, "category": {
        "Financials": 30, "Materials": 20, "Health Care": 8,
        "Real Estate": 8, "Energy": 5, "Industrials": 5,
        "Consumer Staples": 5, "Consumer Discretionary": 5,
        "Communication Services": 5, "Technology": 5, "Utilities": 4,
    }},
    "EWC":  {"region": {"DM": 100}, "category": {
        "Financials": 35, "Energy": 15, "Materials": 10,
        "Industrials": 10, "Technology": 10, "Consumer Discretionary": 5,
        "Communication Services": 5, "Utilities": 3, "Health Care": 3,
        "Consumer Staples": 2, "Real Estate": 2,
    }},

    # ── Emerging Markets (EM) ─────────────────────────────────────────
    "VWO":  {"region": {"EM": 100}, "category": EM_EQUITY},
    "EEM":  {"region": {"EM": 100}, "category": EM_EQUITY},
    "IEMG": {"region": {"EM": 100}, "category": EM_EQUITY},
    "SCHE": {"region": {"EM": 100}, "category": EM_EQUITY},

    # EM Country / Region ETFs
    "CQQQ": {"region": {"EM": 100}, "category": {
        "Technology": 75, "Communication Services": 15, "Consumer Discretionary": 10,
    }},
    "FLCH": {"region": {"EM": 100}, "category": {
        "Technology": 25, "Communication Services": 15, "Financials": 15,
        "Consumer Discretionary": 15, "Industrials": 10, "Materials": 5,
        "Energy": 5, "Health Care": 5, "Consumer Staples": 3, "Utilities": 2,
    }},
    "INDA": {"region": {"EM": 100}, "category": {
        "Financials": 25, "Technology": 20, "Consumer Discretionary": 10,
        "Energy": 10, "Industrials": 8, "Materials": 7,
        "Consumer Staples": 7, "Health Care": 5, "Communication Services": 5,
        "Utilities": 3,
    }},
    "EWZ":  {"region": {"EM": 100}, "category": {
        "Financials": 25, "Energy": 15, "Materials": 15,
        "Consumer Staples": 12, "Utilities": 10, "Industrials": 8,
        "Health Care": 5, "Communication Services": 5,
        "Consumer Discretionary": 3, "Technology": 2,
    }},
    "ILF":  {"region": {"EM": 100}, "category": {
        "Financials": 25, "Materials": 15, "Energy": 12,
        "Consumer Staples": 12, "Utilities": 8, "Industrials": 8,
        "Health Care": 5, "Communication Services": 5,
        "Consumer Discretionary": 5, "Technology": 3, "Other": 2,
    }},

    # ── Thematic / Global Sector ──────────────────────────────────────
    "ICLN": {"region": {"US": 30, "DM": 40, "EM": 30}, "category": {
        "Utilities": 60, "Industrials": 25, "Technology": 10, "Other": 5,
    }},
    "IXC":  {"region": {"US": 50, "DM": 40, "EM": 10}, "category": {"Energy": 100}},
    "GUNR": {"region": {"US": 30, "DM": 40, "EM": 30}, "category": {
        "Materials": 30, "Energy": 30, "Industrials": 15,
        "Consumer Staples": 10, "Utilities": 10, "Other": 5,
    }},
    "COPX": {"region": {"US": 15, "DM": 40, "EM": 45}, "category": {"Materials": 100}},

    # ── Short-Term Treasuries ─────────────────────────────────────────
    "SHY":  {"region": {"US": 100}, "category": {"Short-Term Treasuries": 100}},
    "VGSH": {"region": {"US": 100}, "category": {"Short-Term Treasuries": 100}},
    "SCHO": {"region": {"US": 100}, "category": {"Short-Term Treasuries": 100}},
    "STIP": {"region": {"US": 100}, "category": {"Short-Term Treasuries": 100}},
    "BSV":  {"region": {"US": 100}, "category": {"Short-Term Treasuries": 60, "Other": 40}},

    # ── Long-Term Treasuries ──────────────────────────────────────────
    "TLT":  {"region": {"US": 100}, "category": {"Long-Term Treasuries": 100}},
    "IEF":  {"region": {"US": 100}, "category": {"Long-Term Treasuries": 100}},
    "VGIT": {"region": {"US": 100}, "category": {"Long-Term Treasuries": 100}},
    "VBIL": {"region": {"US": 100}, "category": {"Long-Term Treasuries": 100}},
    "TIP":  {"region": {"US": 100}, "category": {"Long-Term Treasuries": 100}},
    "TIPS": {"region": {"US": 100}, "category": {"Long-Term Treasuries": 100}},
    "GOVT": {"region": {"US": 100}, "category": {"Short-Term Treasuries": 40, "Long-Term Treasuries": 60}},
    "BIV":  {"region": {"US": 100}, "category": {"Long-Term Treasuries": 50, "Other": 50}},
    "BLV":  {"region": {"US": 100}, "category": {"Long-Term Treasuries": 50, "Other": 50}},

    # ── Aggregate / Mixed Bonds ───────────────────────────────────────
    "BND":  {"region": {"US": 100}, "category": {"Short-Term Treasuries": 20, "Long-Term Treasuries": 30, "Other": 50}},
    "AGG":  {"region": {"US": 100}, "category": {"Short-Term Treasuries": 20, "Long-Term Treasuries": 30, "Other": 50}},
    "SCHZ": {"region": {"US": 100}, "category": {"Short-Term Treasuries": 20, "Long-Term Treasuries": 30, "Other": 50}},

    # ── Corporate Bonds → Other ───────────────────────────────────────
    "LQD":  {"region": {"US": 100}, "category": {"Other": 100}},
    "HYG":  {"region": {"US": 100}, "category": {"Other": 100}},
    "JNK":  {"region": {"US": 100}, "category": {"Other": 100}},
    "VCSH": {"region": {"US": 100}, "category": {"Other": 100}},
    "VCIT": {"region": {"US": 100}, "category": {"Other": 100}},

    # ── International Fixed Income → Other ────────────────────────────
    "BNDX": {"region": {"DM": 70, "EM": 30}, "category": {"Other": 100}},
    "EMLC": {"region": {"EM": 100}, "category": {"Other": 100}},
    "EMB":  {"region": {"EM": 100}, "category": {"Other": 100}},
    "IAGG": {"region": {"DM": 70, "EM": 30}, "category": {"Other": 100}},

    # ── Precious Metals ───────────────────────────────────────────────
    "GLD":  {"region": {"Global": 100}, "category": {"Precious Metals": 100}},
    "IAU":  {"region": {"Global": 100}, "category": {"Precious Metals": 100}},
    "GLDM": {"region": {"Global": 100}, "category": {"Precious Metals": 100}},
    "SLV":  {"region": {"Global": 100}, "category": {"Precious Metals": 100}},
    "SIVR": {"region": {"Global": 100}, "category": {"Precious Metals": 100}},
    "PPLT": {"region": {"Global": 100}, "category": {"Precious Metals": 100}},
    "GDX":  {"region": {"Global": 100}, "category": {"Precious Metals": 100}},
    "GDXJ": {"region": {"Global": 100}, "category": {"Precious Metals": 100}},

    # ── Commodities ───────────────────────────────────────────────────
    "DBC":  {"region": {"Global": 100}, "category": {"Commodities": 100}},
    "GSG":  {"region": {"Global": 100}, "category": {"Commodities": 100}},
    "PDBC": {"region": {"Global": 100}, "category": {"Commodities": 100}},
    "COMT": {"region": {"Global": 100}, "category": {"Commodities": 100}},
    "USO":  {"region": {"Global": 100}, "category": {"Commodities": 100}},

    # ── Real Estate ───────────────────────────────────────────────────
    "VNQ":  {"region": {"US": 100}, "category": {"Real Estate": 100}},
    "VNQI": {"region": {"DM": 60, "EM": 40}, "category": {"Real Estate": 100}},
    "IYR":  {"region": {"US": 100}, "category": {"Real Estate": 100}},
    "SCHH": {"region": {"US": 100}, "category": {"Real Estate": 100}},
    "RWR":  {"region": {"US": 100}, "category": {"Real Estate": 100}},

    # ── Cryptocurrency ────────────────────────────────────────────────
    "IBIT": {"region": {"Global": 100}, "category": {"Cryptocurrency": 100}},
    "GBTC": {"region": {"Global": 100}, "category": {"Cryptocurrency": 100}},
    "ETHE": {"region": {"Global": 100}, "category": {"Cryptocurrency": 100}},
    "BITO": {"region": {"Global": 100}, "category": {"Cryptocurrency": 100}},
    "FBTC": {"region": {"Global": 100}, "category": {"Cryptocurrency": 100}},

    # ── Cash / Money Market ───────────────────────────────────────────
    "SPAXX": {"region": {"US": 100}, "category": {"Cash": 100}},
    "FDRXX": {"region": {"US": 100}, "category": {"Cash": 100}},
    "FCASH": {"region": {"US": 100}, "category": {"Cash": 100}},
    "SWVXX": {"region": {"US": 100}, "category": {"Cash": 100}},
    "VMFXX": {"region": {"US": 100}, "category": {"Cash": 100}},
    "SGOV":  {"region": {"US": 100}, "category": {"Cash": 100}},
    "SHV":   {"region": {"US": 100}, "category": {"Cash": 100}},
    "BIL":   {"region": {"US": 100}, "category": {"Cash": 100}},
}


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
