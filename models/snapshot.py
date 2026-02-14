from datetime import datetime, timezone, date
from models import db


class Snapshot(db.Model):
    """A point-in-time capture of portfolio holdings from a CSV upload."""

    __tablename__ = "snapshots"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False)
    brokerage = db.Column(db.String(50), nullable=False)  # 'fidelity' or 'schwab'
    filename = db.Column(db.String(200))
    holding_count = db.Column(db.Integer, default=0)
    total_value = db.Column(db.Float, default=0)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    holdings = db.relationship("Holding", backref="snapshot", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat(),
            "brokerage": self.brokerage,
            "filename": self.filename,
            "holding_count": self.holding_count,
            "total_value": self.total_value,
            "created_at": self.created_at.isoformat(),
        }
