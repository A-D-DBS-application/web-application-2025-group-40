from flask import Flask
from .models import db
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    with app.app_context():
        db.create_all()  # Create sql tables for our data models

    # Do not automatically import or register routes on package import.
    # Route registration is performed explicitly by importing the desired
    # routes module from the application entrypoint (app.py).

    return app