from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY, DATERANGE
db = SQLAlchemy()

class App_user(db.Model):
    __tablename__ = 'app_user'  

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(80), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  

    def __repr__(self):
        return f'<User {self.username}>'
        
class JobListing(db.Model):
    __tablename__ = 'job_listing'  # exact zoals in Supabase

    id = db.Column(db.BigInteger, primary_key=True)
    employer_id = db.Column(db.BigInteger, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(255), nullable=True)
    salary = db.Column(db.Numeric, nullable=True)
    periode = db.Column(DATERANGE, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    requirements = db.Column(ARRAY(db.Text), nullable=True)
    auto_accept = db.Column(db.Boolean, nullable=True)

    def __repr__(self):
        return f'<JobListing {self.title}>'
