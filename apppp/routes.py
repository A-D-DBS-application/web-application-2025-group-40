from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db, App_user

main = Blueprint('main', __name__)

@main.route('/')
def index():
    user = None
    if 'user_id' in session:
        user = App_user.query.get(session['user_id'])
    return render_template('index.html', username=user.username if user else None)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        role = request.form['role']

        # Controleer of email al bestaat
        if App_user.query.filter_by(email=email).first():
            return 'Email already registered'

        new_user = App_user(username=username, email=email, role=role)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        return redirect(url_for('main.index'))
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        user = App_user.query.filter_by(email=email).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('main.index'))
        return 'User not found'
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.index'))
