from datetime import datetime, timezone, date
from models import db


class PortfolioAnalysis(db.Model):
    """Persisted AI analysis for a snapshot date."""

    __tablename__ = "portfolio_analyses"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False, index=True)
    analysis = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat(),
            "analysis": self.analysis,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def get_for_date(cls, snap_date):
        """Get the latest analysis for a given date."""
        return cls.query.filter_by(snapshot_date=snap_date).order_by(
            cls.id.desc()
        ).first()

    @classmethod
    def save_for_date(cls, snap_date, analysis_text):
        """Save (or replace) analysis for a date."""
        existing = cls.query.filter_by(snapshot_date=snap_date).all()
        for e in existing:
            db.session.delete(e)

        record = cls(snapshot_date=snap_date, analysis=analysis_text)
        db.session.add(record)
        db.session.commit()
        return record
