from models import db


class Holding(db.Model):
    __tablename__ = "holdings"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(db.Integer, db.ForeignKey("snapshots.id"), nullable=False)
    ticker = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(200))
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float)
    value = db.Column(db.Float, nullable=False)
    brokerage = db.Column(db.String(50), nullable=False)  # 'fidelity' or 'schwab'
    account = db.Column(db.String(100))

    def to_dict(self):
        return {
            "id": self.id,
            "snapshot_id": self.snapshot_id,
            "ticker": self.ticker,
            "name": self.name,
            "quantity": self.quantity,
            "price": self.price,
            "value": self.value,
            "brokerage": self.brokerage,
            "account": self.account,
        }
