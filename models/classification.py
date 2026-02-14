from datetime import datetime, timezone
from models import db


class TickerClassification(db.Model):
    """Cached AI classification for a ticker — region and category breakdown."""

    __tablename__ = "ticker_classifications"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200))
    # JSON: {"US": 60, "DM": 30, "EM": 10}
    region_breakdown = db.Column(db.JSON, nullable=False, default=dict)
    # JSON: {"Equities": 80, "Fixed Income": 20}
    category_breakdown = db.Column(db.JSON, nullable=False, default=dict)
    classified_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    source = db.Column(
        db.String(20), default="ai"
    )  # 'ai', 'manual', 'builtin'

    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "name": self.name,
            "region_breakdown": self.region_breakdown,
            "category_breakdown": self.category_breakdown,
            "source": self.source,
        }
