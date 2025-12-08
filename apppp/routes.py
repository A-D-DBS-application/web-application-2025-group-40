from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Group40Ufora%21@db.aicnouxwbuydippwukbs.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------ MODELS ------------------

from models import db, AppUser, Employer, RecruiterUser

db.init_app(app)
# 2 maal opslaan van gegevens die al in models.py stonden, is niet nodig. Gewoon importeren.

# ------------------ ROUTES ------------------

@app.route('/choose_role')
def choose_role():
    return render_template('choose_role.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        result = login_user(data['email'], data['password'])
        return jsonify(result)
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        result = register_user(
            username=data.get('username'),
            email=data['email'],
            password=data['password'],
            role=data.get('role', 'student')  # standaard student
        )
        return jsonify(result)
    return render_template('register.html')

@app.route('/register_bedrijf', methods=['GET', 'POST'])
def register_bedrijf():
    if request.method == 'POST':
        data = request.form
        result = register_company(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            company_name=data.get('company_name', 'Onbekend')
        )
        return jsonify(result)
    return render_template('registratie_bedrijf.html')

@app.route("/api/vacatures", methods=["GET"])
def get_vacatures():
    vacatures = [
        {"id": 1, "title": "Student Kassamedewerker", "description": "Weekendjob in supermarkt", "location": "Gent"},
        {"id": 2, "title": "IT Support Student", "description": "Helpdesk op campus", "location": "Antwerpen"},
        {"id": 3, "title": "Barista", "description": "Studentenjob in koffiebar", "location": "Leuven"}
    ]
    return jsonify(vacatures)

@app.route("/api/notificatie", methods=["POST"])
def send_notificatie():
    data = request.json
    vacature_id = data.get("vacatureId")
    print(f"Student heeft vacature {vacature_id} geliket!")
    return jsonify({"message": "Notificatie verzonden"}), 200

# ------------------ FUNCTIES ------------------

def register_user(username, email, password, role="student"):
    existing_user = AppUser.query.filter_by(email=email).first()
    if existing_user:
        return {"error": "Dit emailadres is al gebruikt."}

    new_user = AppUser(username=username, email=email, role=role)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return {"success": "Account aangemaakt!"}
    except IntegrityError:
        db.session.rollback()
        return {"error": "Dit emailadres of username is al gebruikt."}

def login_user(email, password):
    user = AppUser.query.filter_by(email=email).first()
    if not user:
        return {"error": "Geen account gevonden."}
    if not user.check_password(password):
        return {"error": "Verkeerd wachtwoord."}
    return {"success": f"Ingelogd als {user.role}!"}

def register_company(username, email, password, company_name):
    # 1. Maak employer aan
    new_employer = Employer()
    db.session.add(new_employer)
    db.session.flush()

    # 2. Maak recruiter user aan
    recruiter = AppUser(
        username=username,
        email=email,
        role="recruiter"
    )
    recruiter.set_password(password)
    db.session.add(recruiter)
    db.session.flush()

    # 3. Koppel recruiter aan employer
    recruiter_link = RecruiterUser(
        employer_id=new_employer.id,
        user_id=recruiter.id,
        is_admin=True
    )
    db.session.add(recruiter_link)

    try:
        db.session.commit()
        return {"success": f"Bedrijf '{company_name}' aangemaakt met recruiter {username}"}
    except IntegrityError:
        db.session.rollback()
        return {"error": "Kon bedrijf niet registreren"}

# ------------------ MAIN ------------------

if __name__ == "__main__":
    app.run(debug=True)
