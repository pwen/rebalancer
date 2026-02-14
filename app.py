import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_migrate import Migrate

load_dotenv()

from models import db, Holding, TickerClassification, TargetAllocation
from parsers.fidelity import parse_fidelity_csv
from parsers.schwab import parse_schwab_csv
from services.classifier import classify_tickers, reclassify_ticker
from services.rebalancer import compute_breakdown, suggest_trades

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
    """Upload a CSV file from Fidelity or Schwab."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    brokerage = request.form.get("brokerage", "").lower()

    if brokerage not in ("fidelity", "schwab"):
        return jsonify({"error": "Brokerage must be 'fidelity' or 'schwab'"}), 400

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

    # Remove existing holdings for this brokerage, then insert new
    Holding.query.filter_by(brokerage=brokerage).delete()

    now = datetime.now(timezone.utc)
    for h in parsed:
        holding = Holding(
            ticker=h["ticker"],
            name=h["name"],
            quantity=h["quantity"],
            price=h["price"],
            value=h["value"],
            brokerage=h["brokerage"],
            account=h["account"],
            uploaded_at=now,
        )
        db.session.add(holding)

    db.session.commit()

    # Classify any new tickers
    tickers_with_names = list({(h["ticker"], h["name"]) for h in parsed})
    classify_tickers(tickers_with_names)

    return jsonify({
        "message": f"Imported {len(parsed)} holdings from {brokerage.title()}",
        "count": len(parsed),
    })


# ── Holdings ─────────────────────────────────────────────────────────────

@app.route("/api/holdings")
def list_holdings():
    """Return all holdings."""
    holdings = Holding.query.order_by(Holding.value.desc()).all()
    return jsonify([h.to_dict() for h in holdings])


@app.route("/api/holdings", methods=["DELETE"])
def clear_holdings():
    """Clear all holdings (optionally by brokerage)."""
    brokerage = request.args.get("brokerage")
    if brokerage:
        Holding.query.filter_by(brokerage=brokerage).delete()
    else:
        Holding.query.delete()
    db.session.commit()
    return jsonify({"message": "Holdings cleared"})


# ── Breakdown ────────────────────────────────────────────────────────────

@app.route("/api/breakdown")
def get_breakdown():
    """Return aggregated portfolio breakdown by region and category."""
    holdings = Holding.query.all()
    breakdown = compute_breakdown(holdings)
    return jsonify(breakdown)


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
    """Compute rebalancing recommendations."""
    holdings = Holding.query.all()
    if not holdings:
        return jsonify({"error": "No holdings uploaded yet"}), 400

    breakdown = compute_breakdown(holdings)
    trades = suggest_trades(breakdown)
    return jsonify(trades)


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
