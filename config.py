import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # On a real server, set SECRET_KEY as an environment variable.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "ecocoin.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
