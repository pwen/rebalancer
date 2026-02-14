import os
from datetime import datetime, timezone, date

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_migrate import Migrate

load_dotenv()

from models import db, Holding, TickerClassification, TargetAllocation, Snapshot, PortfolioAnalysis
from parsers.fidelity import parse_fidelity_csv
from parsers.schwab import parse_schwab_csv
from services.classifier import classify_tickers, reclassify_ticker, VALID_CATEGORIES, VALID_REGIONS
from services.rebalancer import compute_breakdown, suggest_trades
from services.analyzer import generate_analysis
from services.prices import fetch_live_prices, apply_live_prices

app = Flask(__name__)

database_url = os.environ.get("DATABASE_URL", "postgresql://rebalancer:rebalancer@localhost:5432/rebalancer")
# Railway uses postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

db.init_app(app)
migrate = Migrate(app, db)


# ── Pages ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Upload CSV ───────────────────────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_csv():
    """Upload a CSV file from Fidelity or Schwab as a new snapshot."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    brokerage = request.form.get("brokerage", "").lower()
    snapshot_date_str = request.form.get("snapshot_date", "")

    if brokerage not in ("fidelity", "schwab"):
        return jsonify({"error": "Brokerage must be 'fidelity' or 'schwab'"}), 400

    # Parse snapshot date or default to today
    if snapshot_date_str:
        try:
            snapshot_date = date.fromisoformat(snapshot_date_str)
        except ValueError:
            return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400
    else:
        snapshot_date = date.today()

    try:
        content = file.read().decode("utf-8-sig")  # handle BOM
    except UnicodeDecodeError:
        content = file.read().decode("latin-1")

    try:
        if brokerage == "fidelity":
            parsed = parse_fidelity_csv(content)
        else:
            parsed = parse_schwab_csv(content)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if not parsed:
        return jsonify({"error": "No holdings found in CSV"}), 400

    total_value = sum(h["value"] for h in parsed)

    # Create snapshot
    snapshot = Snapshot(
        snapshot_date=snapshot_date,
        brokerage=brokerage,
        filename=file.filename,
        holding_count=len(parsed),
        total_value=round(total_value, 2),
    )
    db.session.add(snapshot)
    db.session.flush()  # get snapshot.id

    for h in parsed:
        holding = Holding(
            snapshot_id=snapshot.id,
            ticker=h["ticker"],
            name=h["name"],
            quantity=h["quantity"],
            price=h["price"],
            value=h["value"],
            cost_basis=h.get("cost_basis"),
            brokerage=h["brokerage"],
            account=h["account"],
        )
        db.session.add(holding)

    db.session.commit()

    # Classify any new tickers
    tickers_with_names = list({(h["ticker"], h["name"]) for h in parsed})
    classify_tickers(tickers_with_names)

    # Auto-generate AI analysis for this snapshot date
    try:
        all_holdings = _get_snapshot_holdings(snapshot_date.isoformat()) or _get_latest_holdings()
        if all_holdings:
            breakdown = compute_breakdown(all_holdings)
            analysis_text = generate_analysis(breakdown)
            PortfolioAnalysis.save_for_date(snapshot_date, analysis_text)
    except Exception as e:
        print(f"[upload] Auto-analysis failed (non-blocking): {e}")

    return jsonify({
        "message": f"Imported {len(parsed)} holdings from {brokerage.title()} ({snapshot_date.isoformat()})",
        "count": len(parsed),
        "snapshot_id": snapshot.id,
    })


# ── Snapshots ────────────────────────────────────────────────────────────

def _get_latest_holdings():
    """Get holdings from the latest snapshot of each brokerage."""
    holdings = []
    for brokerage in ("fidelity", "schwab"):
        latest = (
            Snapshot.query.filter_by(brokerage=brokerage)
            .order_by(Snapshot.snapshot_date.desc(), Snapshot.id.desc())
            .first()
        )
        if latest:
            holdings.extend(latest.holdings)
    return holdings


def _get_snapshot_holdings(snapshot_date_str):
    """Get holdings from a specific snapshot date (latest per brokerage on that date)."""
    try:
        snap_date = date.fromisoformat(snapshot_date_str)
    except ValueError:
        return []

    holdings = []
    for brokerage in ("fidelity", "schwab"):
        snapshot = (
            Snapshot.query.filter_by(brokerage=brokerage, snapshot_date=snap_date)
            .order_by(Snapshot.id.desc())
            .first()
        )
        if snapshot:
            holdings.extend(snapshot.holdings)
    return holdings


def _get_effective_date(snap_date_str=None):
    """Return the effective snapshot date (as a date object) for analysis storage."""
    if snap_date_str:
        try:
            return date.fromisoformat(snap_date_str)
        except ValueError:
            return None
    # For "latest", find the most recent snapshot date
    latest = Snapshot.query.order_by(
        Snapshot.snapshot_date.desc(), Snapshot.id.desc()
    ).first()
    return latest.snapshot_date if latest else None


@app.route("/api/snapshots")
def list_snapshots():
    """Return all snapshots, newest first."""
    snapshots = Snapshot.query.order_by(
        Snapshot.snapshot_date.desc(), Snapshot.id.desc()
    ).all()
    return jsonify([s.to_dict() for s in snapshots])


@app.route("/api/snapshots/<int:snapshot_id>", methods=["DELETE"])
def delete_snapshot(snapshot_id):
    """Delete a snapshot and its holdings."""
    snapshot = Snapshot.query.get_or_404(snapshot_id)
    db.session.delete(snapshot)
    db.session.commit()
    return jsonify({"message": "Snapshot deleted"})


@app.route("/api/snapshots/<int:snapshot_id>", methods=["PATCH"])
def update_snapshot(snapshot_id):
    """Update snapshot metadata (e.g. date)."""
    snapshot = Snapshot.query.get_or_404(snapshot_id)
    data = request.get_json()

    if "snapshot_date" in data:
        from datetime import date as date_cls
        snapshot.snapshot_date = date_cls.fromisoformat(data["snapshot_date"])

    db.session.commit()
    return jsonify(snapshot.to_dict())


@app.route("/api/snapshot-dates")
def list_snapshot_dates():
    """Return distinct snapshot dates for the date picker."""
    dates = (
        db.session.query(Snapshot.snapshot_date)
        .distinct()
        .order_by(Snapshot.snapshot_date.desc())
        .all()
    )
    return jsonify([d[0].isoformat() for d in dates])


# ── Holdings ─────────────────────────────────────────────────────────────

@app.route("/api/holdings")
def list_holdings():
    """Return holdings. Use ?date=YYYY-MM-DD for a specific snapshot."""
    snap_date = request.args.get("date")
    if snap_date:
        holdings = _get_snapshot_holdings(snap_date)
    else:
        holdings = _get_latest_holdings()
    holdings.sort(key=lambda h: h.value, reverse=True)
    return jsonify([h.to_dict() for h in holdings])


# ── Breakdown ────────────────────────────────────────────────────────────

@app.route("/api/dimensions")
def get_dimensions():
    """Return the valid categories and regions."""
    return jsonify({"categories": VALID_CATEGORIES, "regions": VALID_REGIONS})


@app.route("/api/breakdown")
def get_breakdown():
    """Return aggregated portfolio breakdown. Use ?date=YYYY-MM-DD for a specific snapshot."""
    snap_date = request.args.get("date")
    if snap_date:
        holdings = _get_snapshot_holdings(snap_date)
    else:
        holdings = _get_latest_holdings()
    breakdown = compute_breakdown(holdings)

    # Attach saved analysis if available
    effective_date = _get_effective_date(snap_date)
    if effective_date:
        saved = PortfolioAnalysis.get_for_date(effective_date)
        if saved:
            breakdown["analysis"] = saved.analysis
            breakdown["analysis_date"] = saved.created_at.isoformat()

    return jsonify(breakdown)


@app.route("/api/analyze", methods=["POST"])
def analyze_portfolio():
    """Generate AI analysis of the current portfolio and persist it."""
    snap_date = request.args.get("date")
    if snap_date:
        holdings = _get_snapshot_holdings(snap_date)
    else:
        holdings = _get_latest_holdings()

    if not holdings:
        return jsonify({"error": "No holdings found"}), 404

    breakdown = compute_breakdown(holdings)
    analysis_text = generate_analysis(breakdown)

    # Persist
    effective_date = _get_effective_date(snap_date)
    if effective_date:
        PortfolioAnalysis.save_for_date(effective_date, analysis_text)

    return jsonify({"analysis": analysis_text})


# ── Classifications ──────────────────────────────────────────────────────

@app.route("/api/classifications")
def list_classifications():
    """Return all ticker classifications."""
    classifications = TickerClassification.query.order_by(
        TickerClassification.ticker
    ).all()
    return jsonify([c.to_dict() for c in classifications])


@app.route("/api/classifications/<ticker>", methods=["PUT"])
def update_classification(ticker):
    """Manually update a ticker's classification."""
    data = request.json
    classification = TickerClassification.query.filter_by(ticker=ticker.upper()).first()

    if not classification:
        classification = TickerClassification(ticker=ticker.upper())
        db.session.add(classification)

    if "region_breakdown" in data:
        classification.region_breakdown = data["region_breakdown"]
    if "category_breakdown" in data:
        classification.category_breakdown = data["category_breakdown"]
    if "name" in data:
        classification.name = data["name"]

    classification.source = "manual"
    classification.classified_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(classification.to_dict())


@app.route("/api/classifications/<ticker>/reclassify", methods=["POST"])
def reclassify(ticker):
    """Force re-classify a ticker using AI."""
    classification = TickerClassification.query.filter_by(ticker=ticker.upper()).first()
    name = classification.name if classification else ""
    result = reclassify_ticker(ticker.upper(), name)
    return jsonify(result.get(ticker.upper(), {}))


# ── Targets ──────────────────────────────────────────────────────────────

@app.route("/api/targets")
def list_targets():
    """Return all target allocations."""
    targets = TargetAllocation.query.order_by(
        TargetAllocation.dimension, TargetAllocation.label
    ).all()
    return jsonify([t.to_dict() for t in targets])


@app.route("/api/targets", methods=["PUT"])
def save_targets():
    """Save target allocations (replaces all targets for a dimension)."""
    data = request.json
    dimension = data.get("dimension")
    allocations = data.get("allocations", [])

    if dimension not in ("region", "category"):
        return jsonify({"error": "Dimension must be 'region' or 'category'"}), 400

    # Validate percentages sum to ~100
    total = sum(a.get("target_pct", 0) for a in allocations)
    if abs(total - 100) > 1:
        return jsonify({"error": f"Target percentages must sum to 100 (got {total})"}), 400

    # Replace all targets for this dimension
    TargetAllocation.query.filter_by(dimension=dimension).delete()

    for a in allocations:
        target = TargetAllocation(
            dimension=dimension,
            label=a["label"],
            target_pct=a["target_pct"],
        )
        db.session.add(target)

    db.session.commit()
    return jsonify({"message": f"Saved {len(allocations)} {dimension} targets"})


# ── Rebalance ────────────────────────────────────────────────────────────

@app.route("/api/rebalance")
def get_rebalance():
    """Compute rebalancing recommendations. Use ?date=YYYY-MM-DD for a specific snapshot."""
    snap_date = request.args.get("date")
    if snap_date:
        holdings = _get_snapshot_holdings(snap_date)
    else:
        holdings = _get_latest_holdings()

    if not holdings:
        return jsonify({"error": "No holdings uploaded yet"}), 400

    breakdown = compute_breakdown(holdings)
    trades = suggest_trades(breakdown)
    return jsonify(trades)


# ── Live Prices ──────────────────────────────────────────────────────────

@app.route("/api/live-prices")
def get_live_prices():
    """Fetch live prices for holdings in the latest (or specified) snapshot."""
    snap_date = request.args.get("date")
    if snap_date:
        holdings = _get_snapshot_holdings(snap_date)
    else:
        holdings = _get_latest_holdings()

    if not holdings:
        return jsonify({"error": "No holdings found"}), 400

    tickers = list({h.ticker for h in holdings})
    live_prices = fetch_live_prices(tickers)
    updated = apply_live_prices(holdings, live_prices)

    snapshot_total = sum(h.value for h in holdings)
    live_total = sum(u["live_value"] for u in updated)

    return jsonify({
        "snapshot_total": round(snapshot_total, 2),
        "live_total": round(live_total, 2),
        "total_change": round(live_total - snapshot_total, 2),
        "total_change_pct": round((live_total - snapshot_total) / snapshot_total * 100, 2) if snapshot_total else 0,
        "holdings": sorted(updated, key=lambda x: x["live_value"], reverse=True),
    })


@app.route("/api/live-breakdown")
def get_live_breakdown():
    """Compute breakdown using live prices instead of snapshot prices."""
    snap_date = request.args.get("date")
    if snap_date:
        holdings = _get_snapshot_holdings(snap_date)
    else:
        holdings = _get_latest_holdings()

    if not holdings:
        return jsonify({"error": "No holdings found"}), 400

    tickers = list({h.ticker for h in holdings})
    live_prices = fetch_live_prices(tickers)

    # Create virtual holdings with live prices
    virtual_holdings = []
    for h in holdings:
        live_price = live_prices.get(h.ticker)
        virtual = Holding(
            ticker=h.ticker,
            name=h.name,
            quantity=h.quantity,
            price=live_price if live_price else h.price,
            value=round(h.quantity * live_price, 2) if live_price and h.quantity else h.value,
            brokerage=h.brokerage,
            account=h.account,
        )
        virtual_holdings.append(virtual)

    breakdown = compute_breakdown(virtual_holdings)

    # Add snapshot comparison
    snapshot_total = sum(h.value for h in holdings)
    breakdown["snapshot_total"] = round(snapshot_total, 2)
    breakdown["total_change"] = round(breakdown["total_value"] - snapshot_total, 2)
    breakdown["total_change_pct"] = (
        round((breakdown["total_value"] - snapshot_total) / snapshot_total * 100, 2)
        if snapshot_total else 0
    )

    return jsonify(breakdown)


@app.route("/api/live-rebalance")
def get_live_rebalance():
    """Compute rebalancing recommendations using live prices."""
    snap_date = request.args.get("date")
    if snap_date:
        holdings = _get_snapshot_holdings(snap_date)
    else:
        holdings = _get_latest_holdings()

    if not holdings:
        return jsonify({"error": "No holdings found"}), 400

    tickers = list({h.ticker for h in holdings})
    live_prices = fetch_live_prices(tickers)

    virtual_holdings = []
    for h in holdings:
        live_price = live_prices.get(h.ticker)
        virtual = Holding(
            ticker=h.ticker,
            name=h.name,
            quantity=h.quantity,
            price=live_price if live_price else h.price,
            value=round(h.quantity * live_price, 2) if live_price and h.quantity else h.value,
            brokerage=h.brokerage,
            account=h.account,
        )
        virtual_holdings.append(virtual)

    breakdown = compute_breakdown(virtual_holdings)
    trades = suggest_trades(breakdown)
    return jsonify(trades)


# ── Trends ───────────────────────────────────────────────────────────────

BOND_CASH_CATEGORIES = {"Cash", "Short-Term Treasuries", "Long-Term Treasuries"}

@app.route("/api/trends")
def get_trends():
    """Return time-series data across all snapshot dates for trend charts."""
    # Get all distinct snapshot dates
    dates = (
        db.session.query(Snapshot.snapshot_date)
        .distinct()
        .order_by(Snapshot.snapshot_date.asc())
        .all()
    )

    results = []
    for (snap_date,) in dates:
        holdings = _get_snapshot_holdings(snap_date.isoformat())
        if not holdings:
            continue
        breakdown = compute_breakdown(holdings)
        total = breakdown["total_value"]
        if total == 0:
            continue

        # Category allocations as percentages
        categories = {k: v["pct"] for k, v in breakdown["by_category"].items()}

        # Cash + treasury buffer %
        buffer_pct = sum(
            v["pct"] for k, v in breakdown["by_category"].items()
            if k in BOND_CASH_CATEGORIES
        )

        results.append({
            "date": snap_date.isoformat(),
            "total_value": round(total, 2),
            "categories": categories,
            "cash_buffer_pct": round(buffer_pct, 2),
        })

    return jsonify(results)


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5002,
        extra_files=[
            "templates/index.html",
            "static/css/style.css",
            "static/js/app.js",
        ],
    )
