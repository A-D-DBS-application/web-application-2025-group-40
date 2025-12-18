# apppp/models.py
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db



class AppUser(UserMixin, db.Model):
    __tablename__ = 'app_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' of 'recruiter'
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', uselist=False, back_populates='user')
    recruiter = db.relationship('RecruiterUser', uselist=False, back_populates='user')
    matches = db.relationship('Match', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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
