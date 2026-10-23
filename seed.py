"""Run once:  python seed.py   -> creates demo accounts and sample data."""
from datetime import datetime, timedelta
from app import app
from models import db, User, WasteCategory, CollectionPoint, Submission
from services.rewards import approve_submission

DEMO = [("Admin", "admin@ecocoin.test", "admin123", "admin"),
        ("Carla Collector", "collector@ecocoin.test", "collect123", "collector"),
        ("Dana Demo", "user@ecocoin.test", "user123", "user")]

with app.app_context():
    for name, email, pw, role in DEMO:
        if not User.query.filter_by(email=email).first():
            u = User(name=name, email=email, role=role)
            u.set_password(pw)
            db.session.add(u)
    db.session.add(CollectionPoint(name="Green Park Depot", address="Park Road 12")) \
        if CollectionPoint.query.count() < 2 else None
    db.session.commit()

    user = User.query.filter_by(email="user@ecocoin.test").first()
    collector = User.query.filter_by(email="collector@ecocoin.test").first()
    point = CollectionPoint.query.first()
    if not Submission.query.filter_by(user_id=user.id).first():
        for i, (cat, kg) in enumerate([("Plastic", 3.2), ("Paper", 6), ("Glass", 2.5), ("Metal", 1.4)]):
            c = WasteCategory.query.filter_by(name=cat).first()
            s = Submission(user_id=user.id, category_id=c.id, point_id=point.id,
                           claimed_weight_g=int(kg * 1000),
                           created_at=datetime.utcnow() - timedelta(days=6 - i * 2))
            db.session.add(s)
            db.session.commit()
            approve_submission(s, collector, int(kg * 1000))
        # back-date the ledger so the chart has a timeline
        from models import Transaction
        for t, s in zip(Transaction.query.order_by(Transaction.id).all(),
                        Submission.query.order_by(Submission.id).all()):
            t.created_at = s.created_at
        e = WasteCategory.query.filter_by(name="E-waste").first()
        db.session.add(Submission(user_id=user.id, category_id=e.id, point_id=point.id,
                                  claimed_weight_g=800, note="Old phone chargers"))
        db.session.commit()
    print("Done. Logins: admin@ecocoin.test/admin123, collector@ecocoin.test/collect123, user@ecocoin.test/user123")
