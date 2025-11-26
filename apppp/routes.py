1  from flask import Flask, render_template, session, redirect, url_for
2  from models import db, Match, AppUser, JobListing, Employer, RecruiterUser, Student
3  from datetime import datetime, timedelta
4  from sqlalchemy import func
5  from config import Config


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.route('/choose_role')
def choose_role():
    return render_template('choose_role.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/match_page')
def match_page():
    return render_template('match_page.html')


if __name__ == "__main__":
    app.run(debug=True)

