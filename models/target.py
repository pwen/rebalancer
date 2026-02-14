from models import db


class TargetAllocation(db.Model):
    """User-defined target allocation percentages."""

    __tablename__ = "target_allocations"

    id = db.Column(db.Integer, primary_key=True)
    dimension = db.Column(
        db.String(20), nullable=False
    )  # 'region' or 'category'
    label = db.Column(db.String(50), nullable=False)  # 'US', 'Equities', etc.
    target_pct = db.Column(db.Float, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("dimension", "label", name="uq_dimension_label"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "dimension": self.dimension,
            "label": self.label,
            "target_pct": self.target_pct,
        }
