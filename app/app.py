# app.py
import os
from flask import Flask
from dotenv import load_dotenv

from apppp.extensions import db, login_manager
from apppp.routes import register_routes
from apppp.models import AppUser  # nodig voor login loader

from supabase import create_client

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

    # DB config
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if DATABASE_URL:
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_size": 1,
            "max_overflow": 0,
            "pool_timeout": 30,
            "pool_pre_ping": True,
        }
    else:
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

    # optional supabase client
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    supabase = None
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            supabase = None

    # register routes
    register_routes(app, supabase=supabase)

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
