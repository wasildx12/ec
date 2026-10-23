from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user")  # user/collector/admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship("Submission", back_populates="user",
                                  foreign_keys="Submission.user_id")
    transactions = db.relationship("Transaction", back_populates="user")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def balance(self):
        """Balance is never stored: it is always the sum of the ledger."""
        total = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)) \
            .filter(Transaction.user_id == self.id).scalar()
        return int(total)


class WasteCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    coins_per_kg = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class CollectionPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("waste_category.id"), nullable=False)
    point_id = db.Column(db.Integer, db.ForeignKey("collection_point.id"), nullable=False)
    claimed_weight_g = db.Column(db.Integer, nullable=False)
    verified_weight_g = db.Column(db.Integer)
    status = db.Column(db.String(20), default="pending", nullable=False)
    note = db.Column(db.String(200))
    reject_reason = db.Column(db.String(200))
    coins_awarded = db.Column(db.Integer, default=0, nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)

    user = db.relationship("User", foreign_keys=[user_id], back_populates="submissions")
    reviewer = db.relationship("User", foreign_keys=[reviewed_by])
    category = db.relationship("WasteCategory")
    point = db.relationship("CollectionPoint")


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    # unique => one submission can never be paid twice
    submission_id = db.Column(db.Integer, db.ForeignKey("submission.id"), unique=True)
    amount = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(20), nullable=False, default="earn")
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="transactions")
