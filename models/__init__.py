from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.snapshot import Snapshot
from models.holding import Holding
from models.classification import TickerClassification
from models.target import TargetAllocation
