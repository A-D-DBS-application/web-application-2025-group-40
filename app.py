# app.py
import os
from flask import Flask
from dotenv import load_dotenv
from supabase import create_client

from apppp.extensions import db, login_manager
from apppp.routes import register_routes

# Zorg dat models “bekend” zijn bij SQLAlchemy vóór db.create_all()
from apppp.models import AppUser  # noqa: F401

load_dotenv()  # leest .env in vanuit project root


def create_app():
    app = Flask(__name__)

    # Secret key
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

    # Database config
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 1,
            "max_overflow": 0,
            "pool_timeout": 30,
            "pool_pre_ping": True,
        }
    else:
        # fallback local sqlite (alleen voor lokaal testen)
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tinderjobs.db"
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)

    # login loader
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return AppUser.query.get(int(user_id))
        except Exception:
            return None

    # optional supabase client (voor storage / API, niet nodig voor DB connectie)
    supabase = None
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
        except Exception:
            supabase = None

    # routes
    register_routes(app, supabase=supabase)

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
