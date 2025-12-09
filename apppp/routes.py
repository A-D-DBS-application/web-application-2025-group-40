from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, current_user
import re #voor algoritme#
from collections import Counter #voor algoritme#

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Group40Ufora%21@db.aicnouxwbuydippwukbs.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# ------------------ MODELS ------------------

from models import db, AppUser, Employer, RecruiterUser, JobLike, JobListing

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

    #checken of job bestaat en of die niet al geliked is#
@app.route('/jobs/<int:job_id>/like', methods=['POST']) 
@login_required
def like_job(job_id):
    user_id = current_user.id

    # check of job bestaat
    job = JobListing.query.get(job_id)
    if not job:
        return jsonify({"error": "Job bestaat niet"}), 404

    # check of like al bestaat
    existing = JobLike.query.filter_by(user_id=user_id, job_id=job_id).first()
    if existing:
        return jsonify({"message": "Job is al geliked"}), 200

    # like aanmaken
    like = JobLike(user_id=user_id, job_id=job_id)
    db.session.add(like)
    db.session.commit()

    return jsonify({"message": "Job geliked"}), 201

@app.route("/recommend/jobs", methods=["GET"])
@login_required
def recommend_jobs():
    user_id = current_user.id
    recs = get_recommendations_for_user(user_id)

    result = []
    for r in recs:
        result.append({
            "id": r.id,
            "title": r.title,
            "location": r.location,
            "description": r.description[:200] if r.description else ""
        })

    return jsonify(result), 200


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
    

STOPWORDS = {
    "de","het","een","en","van","met","je","jij","u","ik","hij","zij","we","wij","ze",
    "die","dat","dit","daar","hier","als","maar","om","te","is","in","op","voor","naar",
    "door","aan","tot","uit","bij","ook","wat","hoe","waar","wanneer","wel","niet","geen",
    "zijn","was","wordt","heb","heeft","hebben","kan","kunnen","moet","moeten","zal","zullen"
}

def tokenize(text):
    #Haalt woorden op, maakt lowercase, verwijdert stopwoorden.#
    if not text:
        return []

    # woorden extraheren#
    words = re.findall(r'\w+', text.lower())

    # stopwoorden verwijderen#
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]

    return filtered


def get_recommendations_for_user(user_id, limit=10):
    # 1. Gelijk liked jobs ophalen
    liked = JobLike.query.filter_by(user_id=user_id).all()
    if not liked:
        return JobListing.query.order_by(JobListing.created_at.desc()).limit(limit).all()

    liked_job_ids = [l.job_id for l in liked]
    liked_jobs = JobListing.query.filter(JobListing.id.in_(liked_job_ids)).all()

    # 2. Verzamel woorden uit descriptions van gelikete jobs
    description_word_counts = Counter()
    user_locations = set()
    liked_title_words = set()

    for job in liked_jobs:
        # woorden uit description
        description_word_counts.update(tokenize(job.description))

        # locatie opslaan
        if job.location:
            user_locations.add(job.location.lower())

        # titelwoorden opslaan
        liked_title_words.update(tokenize(job.title))

    # 3. Score andere jobs
    all_jobs = JobListing.query.filter(~JobListing.id.in_(liked_job_ids)).all()
    scored = []

    for job in all_jobs:
        score = 0

        # --- A: description similarity ---
        job_words = tokenize(job.description)
        word_overlap = sum(description_word_counts[w] for w in job_words if w in description_word_counts)
        score += word_overlap * 1.5    # redelijk gewicht

        # --- B: locatie match ---
        if job.location and job.location.lower() in user_locations:
            score += 2

        # --- C: titel similarity ---
        job_title_words = tokenize(job.title)
        title_overlap = len(liked_title_words.intersection(job_title_words))
        score += title_overlap * 1

        if score > 0:
            scored.append((score, job))

    # 4. sorteer
    scored.sort(key=lambda x: x[0], reverse=True)

    # 5. limit
    recommendations = [job for score, job in scored[:limit]]

    return recommendations


# ------------------ MAIN ------------------

if __name__ == "__main__":
    app.run(debug=True)
