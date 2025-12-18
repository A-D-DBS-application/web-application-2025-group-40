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


<<<<<<< HEAD

class Employer(db.Model):
    __tablename__ = 'employer'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    contact_person = db.Column(db.String(120))
    btw_number = db.Column(db.String(60))
    description = db.Column(db.Text)
    contact_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recruiters = db.relationship('RecruiterUser', back_populates='employer')
    job_listings = db.relationship('JobListing', back_populates='employer')



class JobListing(db.Model):
    __tablename__ = 'job_listing'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)
    client = db.Column(db.String(140), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(120))

    employer = db.relationship('Employer', back_populates='job_listings')
    matches = db.relationship('Match', back_populates='job')



class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listing.id'), nullable=False)
    matched_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('AppUser', back_populates='matches')
    job = db.relationship('JobListing', back_populates='matches')



class Dislike(db.Model):
    __tablename__ = 'dislike'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listing.id'), nullable=False)
    disliked_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('AppUser', backref='dislikes')
    job = db.relationship('JobListing', backref='dislikes')



# -----------------------
# Helper utilities
# -----------------------

STOPWORDS = set()


def get_current_recruiter():
    """Return the RecruiterUser for the currently logged-in recruiter, or None."""
    from flask_login import current_user
    try:
        if not (current_user.is_authenticated and getattr(current_user, 'role', None) == 'recruiter'):
            return None
        return RecruiterUser.query.filter_by(user_id=current_user.id).first()
    except Exception:
        return None


def get_employer_for_current_user():
    """Return Employer linked to current_user if recruiter, else None."""
    rec = get_current_recruiter()
    return rec.employer if rec and getattr(rec, 'employer', None) else None


def recruiter_owns_job(job):
    """Return True when the current user is a recruiter and owns the job's employer."""
    rec = get_current_recruiter()
    return bool(rec and rec.employer and job and rec.employer.id == job.employer_id)


def populate_jobs_display_fields(jobs):
    """Attach convenience attributes used by templates: client, company_name, match_count."""
    for job in jobs:
        job.client = getattr(job, 'client', None)
        job.company_name = job.employer.name if job.employer else 'Onbekend'
        job.match_count = len(job.matches or [])


def get_unseen_jobs_for_user(user):
    """Return JobListing rows the given user hasn't matched/liked yet.
    If the user has no matches, return all jobs.
    """
    matched_job_ids = [m.job_id for m in getattr(user, 'matches', [])] if getattr(user, 'matches', None) else []
    if matched_job_ids:
        jobs = JobListing.query.filter(~JobListing.id.in_(matched_job_ids)).all()
    else:
        jobs = JobListing.query.all()
    return jobs
=======
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
>>>>>>> 49f70cb7b4f42340d657c23ae3dd599625c44994
