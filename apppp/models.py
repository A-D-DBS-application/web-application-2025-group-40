from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'app_user'  

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    role = db.Column(db.String(80), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  


    def __repr__(self):
        return f'<User {self.username}>'
