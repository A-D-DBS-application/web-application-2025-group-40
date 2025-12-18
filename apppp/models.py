from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY, DATERANGE
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ---------------------------------------------------
# USER MODEL
# ---------------------------------------------------

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

# Create an uninitialized SQLAlchemy instance; the application will call db.init_app(app)
db = SQLAlchemy()


# -----------------------
# Models (canonical, moved from app.py)
# -----------------------


class AppUser(UserMixin, db.Model):
    __tablename__ = 'app_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'recruiter'
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    student = db.relationship('Student', uselist=False, back_populates='user')
    recruiter = db.relationship('RecruiterUser', uselist=False, back_populates='user')
    matches = db.relationship('Match', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login compatibility properties/methods
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        # If you later add a column to deactivate users, change this to
        # return bool(self.active) or similar.
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        # Flask-Login expects a unicode id
        return str(self.id) if self.id is not None else None



class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    first_name = db.Column(db.String(60))
    last_name = db.Column(db.String(60))

    user = db.relationship('AppUser', back_populates='student')



class RecruiterUser(db.Model):
    __tablename__ = 'recruiter_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    user = db.relationship('AppUser', back_populates='recruiter')
    employer = db.relationship('Employer', back_populates='recruiters')


    def __repr__(self):
        return f'<Joblike user_id={self.user_id} job_id={self.job_id}>'
    

# ---------------------------------------------------
# STOPWORD
# ---------------------------------------------------
    
class Stopword(db.Model):
        __tablename__ = 'stopwords'
        id = db.Column(db.Integer, primary_key=True)
        word = db.Column(db.String(50), unique=True, nullable=False)
        
        def __repr__(self):
            return f'<Stopword {self.word}>'    
