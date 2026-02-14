# Regenerate ETF Classifications

Copy-paste the prompt below into any AI (ChatGPT, Claude, etc.) to regenerate `services/etf_classifications.json`. Save the output directly as that file — the app picks it up on next start.

Add or remove tickers from the list before running if your portfolio has changed.

---

## Prompt

> Generate a JSON file classifying common US-listed ETFs and funds by region and sector. The output should be a single JSON object where each key is a ticker symbol and each value has `region` and `category` breakdowns (percentages summing to 100 each).
>
> Include a `_meta` key at the top with `description`, `instructions`, `valid_regions`, and `valid_categories`.
>
> **Valid regions** (percentages must sum to 100):
> - `US` — United States
> - `DM` — Developed Markets ex-US (Europe, Japan, Australia, Canada, etc.)
> - `EM` — Emerging Markets (China, India, Brazil, etc.)
> - `Global` — Cannot be attributed to a single region (e.g., commodities, gold)
>
> **Valid categories** — GICS-style sectors + special categories (percentages must sum to 100):
> - `Technology`, `Financials`, `Health Care`, `Consumer Discretionary`, `Communication Services`, `Industrials`, `Consumer Staples`, `Energy`, `Utilities`, `Real Estate`, `Materials`
> - `Precious Metals` (gold, silver, platinum, mining stocks for precious metals)
> - `Commodities` (oil, agriculture, broad commodity baskets — NOT mining equities)
> - `Cryptocurrency` (Bitcoin, Ethereum, crypto funds)
> - `Short-Term Treasuries` (US Treasury bonds < 3yr maturity, T-bills)
> - `Long-Term Treasuries` (US Treasury bonds > 3yr maturity)
> - `Cash` (money market funds, cash equivalents)
> - `Other` (corporate bonds, international bonds, anything else)
>
> **Rules:**
> 1. Use ONLY the exact region and category keys listed above.
> 2. For broad index ETFs (e.g., VTI, SPY, QQQ), break down by approximate sector weights of the underlying index.
> 3. For sector ETFs (e.g., XLK, XLE), assign 100% to the matching category.
> 4. Precious metals miners (GDX, GDXJ) → `Precious Metals`, not `Materials`.
> 5. Energy MLPs (AMLP) → `Energy`.
> 6. Aggregate bond funds (BND, AGG) → split across `Short-Term Treasuries`, `Long-Term Treasuries`, and `Other`.
> 7. Corporate/high-yield bonds (LQD, HYG, JNK) → `Other`.
> 8. International bonds (BNDX, EMLC, EMB) → `Other` category with appropriate region split.
>
> **ETFs to include** (cover at minimum these categories):
> - US broad market: VTI, ITOT, SPTM, VOO, SPY, IVV, DIA, SCHB, SCHX, RSP
> - Nasdaq: QQQ, QQQM
> - US small cap: IJR, SCHA, VTWO, IWM, VB
> - US mid cap: SCHM, MDY, VO
> - US sectors: XLK, XLF, XLV, XLY, XLC, XLI, XLP, XLE, XLU, XLRE, FENY, XOP, AMLP
> - Global: VT, ACWI
> - Developed markets: VEA, EFA, IEFA, SCHF, VXUS, IXUS, VIGI
> - DM country: EWS, EWJ, EWG, EWU, EWA, EWC
> - Emerging markets: VWO, EEM, IEMG, SCHE, CQQQ, FLCH, INDA, EWZ, ILF
> - Thematic: ICLN, IXC, GUNR, COPX
> - Short-term treasuries: SHY, VGSH, SCHO, STIP, BSV
> - Long-term treasuries: TLT, IEF, VGIT, VBIL, TIP, TIPS, GOVT, BIV, BLV
> - Aggregate bonds: BND, AGG, SCHZ
> - Corporate bonds: LQD, HYG, JNK, VCSH, VCIT
> - International bonds: BNDX, EMLC, EMB, IAGG
> - Precious metals: GLD, IAU, GLDM, SLV, SIVR, PPLT, GDX, GDXJ
> - Commodities: DBC, GSG, PDBC, COMT, USO
> - Real estate: VNQ, VNQI, IYR, SCHH, RWR
> - Crypto: IBIT, GBTC, ETHE, BITO, FBTC
> - Cash/money market: SPAXX, FDRXX, FCASH, SWVXX, VMFXX, SGOV, SHV, BIL
>
> **Example format** (one entry):
> ```json
> "VTI": {"region": {"US": 100}, "category": {"Technology": 30, "Financials": 13, "Health Care": 12, "Consumer Discretionary": 10, "Communication Services": 9, "Industrials": 9, "Consumer Staples": 6, "Energy": 4, "Utilities": 3, "Real Estate": 2, "Materials": 2}}
> ```
>
> Return ONLY the raw JSON — no markdown fences, no explanation. Use current approximate sector weights.
