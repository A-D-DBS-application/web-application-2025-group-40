from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY, DATERANGE

db = SQLAlchemy()


from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, UniqueConstraint



from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy



class AppUser(db.Model):
    __tablename__ = 'app_user'
    id = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(50), nullable=False)
    lastName = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # hashed wachtwoord






    # relaties
    matches = db.relationship('Match', backref='user', lazy=True)
    recruiter_links = db.relationship('RecruiterUser', backref='user', lazy=True)
    student_profile = db.relationship('Student', backref='user', uselist=False)
    liked_jobs = db.relationship("Joblike", back_populates="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<AppUser {self.email}>'
    
    def authenticatie(email, password):
        # Zoekt een gebruiker op basis van email en controleert het wachtwoord.
        # Geeft het User object terug bij succes, anders None.
        # 1. Zoek de gebruiker op basis van het unieke e-mailadres
        user = user.query.filter_by(email=email).first()

        # 2. Controleer of de gebruiker bestaat en of het wachtwoord klopt
        if user and user.check_password(password):
            return user
        
        return None

    def __repr__(self):
        return f'<User {self.email}>'


class Employer(db.Model):
    __tablename__ = 'employer'

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    description = db.Column(db.Text)
    contact_email = db.Column(db.String(255))
    is_agency = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # relaties
    job_listings = db.relationship('JobListing', backref='employer', lazy=True)
    recruiters = db.relationship('RecruiterUser', backref='employer', lazy=True)

    def __repr__(self):
        return f'<Employer {self.name}>'


class Sector(db.Model):
    __tablename__ = 'sector'

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)

    job_links = db.relationship('JobListingSector', backref='sector', lazy=True)

    def __repr__(self):
        return f'<Sector {self.name}>'


class JobListing(db.Model):
    __tablename__ = 'job_listing'

    id = db.Column(db.BigInteger, primary_key=True)
    employer_id = db.Column(db.BigInteger, db.ForeignKey('employer.id'))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    salary = db.Column(db.Numeric)
    periode = db.Column(DATERANGE)
    requirements = db.Column(ARRAY(db.Text))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # relaties
    matches = db.relationship('Match', backref='job', lazy=True)
    sectors = db.relationship('JobListingSector', backref='job', lazy=True)

    def __repr__(self):
        return f'<JobListing {self.title}>'


class JobListingSector(db.Model):
    __tablename__ = 'job_listing_sector'

    job_id = db.Column(db.BigInteger, db.ForeignKey('job_listing.id'), primary_key=True)
    sector_id = db.Column(db.BigInteger, db.ForeignKey('sector.id'), primary_key=True)

    def __repr__(self):
        return f'<JobListingSector job_id={self.job_id} sector_id={self.sector_id}>'


class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('app_user.id'))
    job_id = db.Column(db.BigInteger, db.ForeignKey('job_listing.id'))
    matched_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    notification_sent = db.Column(db.Boolean, default=False)
    notification_sent_at = db.Column(db.DateTime(timezone=True))
    notification_message = db.Column(db.Text)

    def __repr__(self):
        return f'<Match user_id={self.user_id} job_id={self.job_id}>'


class RecruiterUser(db.Model):
    __tablename__ = 'recruiter_user'

    employer_id = db.Column(db.BigInteger, db.ForeignKey('employer.id'), primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('app_user.id'), primary_key=True)
    is_admin = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<RecruiterUser employer_id={self.employer_id} user_id={self.user_id}>'


class Student(db.Model):
    __tablename__ = 'student'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('app_user.id'))
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}>'

class Joblike(db.Model):
    __tablename__ = 'joblike'

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('app_user.id'), nullable=False)
    job_id = db.Column(db.BigInteger, db.ForeignKey('job_listing.id'), nullable=False)
    created_at = db.Column(db.DateTime(), server_default=db.func.now())

    # relaties
    user = db.relationship("AppUser", back_populates="liked_jobs")

    def __repr__(self):
        return f'<Joblike user_id={self.user_id} job_id={self.job_id}>'