import os
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from supabase import create_client
from dotenv import load_dotenv

# Load environment
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 3,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 0,
        'connect_args': {'connect_timeout': 10}
    }
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tinderjobs.db'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Login manager (single instance)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login_student'


# Optional Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None
        app.logger.exception('Kon Supabase client niet initialiseren')
else:
    supabase = None
    app.logger.warning('Supabase credentials niet gevonden; Supabase operaties zijn uitgeschakeld')


# Import canonical models/helpers and attach db to app
from apppp.models import db, AppUser  # noqa: E402
db.init_app(app)


# login loader (AppUser from apppp.models)
@login_manager.user_loader
def load_user(user_id):
    try:
        return AppUser.query.get(int(user_id))
    except Exception:
        return None



from apppp.routes import *  # noqa: E402,F401,F403

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)