from flask import Flask, render_template
from flask_login import LoginManager
from config import Config
from models import db, User, WasteCategory, CollectionPoint

DEFAULT_CATEGORIES = [("Plastic", 10), ("Paper", 5), ("Glass", 8), ("Metal", 15), ("E-waste", 25)]


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    login = LoginManager(app)
    login.login_view = "auth.login"
    login.login_message = "Please log in first."

    @login.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes import auth, user, collector, admin
    for module in (auth, user, collector, admin):
        app.register_blueprint(module.bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(403)
    def forbidden(_):
        return render_template("error.html", code=403, text="You don't have access to this page."), 403

    @app.errorhandler(404)
    def missing(_):
        return render_template("error.html", code=404, text="We couldn't find that page."), 404

    with app.app_context():
        db.create_all()
        if not WasteCategory.query.first():  # first run: give the app usable defaults
            db.session.add_all(WasteCategory(name=n, coins_per_kg=r) for n, r in DEFAULT_CATEGORIES)
            db.session.add(CollectionPoint(name="Central Eco Hub", address="Main Boulevard, City Centre"))
            db.session.commit()
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
