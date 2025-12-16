from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, current_user, logout_user, UserMixin
from datetime import datetime
from sqlalchemy.dialects.postgresql import ARRAY, DATERANGE
from collections import Counter
import re
from utils.stopwords import load_stopwords_from_db
from models import AppUser, Employer, RecruiterUser, Student, JobListing, JobLike, Match


# ------------------ APP SETUP ------------------
app = Flask(__name__)
# NOTE: replace the URI below with your real credentials or use environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Group40Ufora%21@db.aicnouxwbuydippwukbs.supabase.co:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'replace-this-with-a-secure-random-value'

# ------------------ DB & LOGIN ------------------
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'



# ------------------ LOGIN MANAGER ------------------
@login_manager.user_loader
def load_user(user_id):
    return AppUser.query.get(int(user_id))


# ------------------ UTILITIES ------------------


def tokenize(text):
    if not text:
        return []

    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in STOPWORDS]



# ------------------ AUTH / REGISTER HELPERS ------------------

def authenticate_user(email, password):
    user = AppUser.query.filter_by(email=email).first()
    if not user:
        return None, "Geen account gevonden."
    if not user.check_password(password):
        return None, "Verkeerd wachtwoord."
    return user, None


def create_user(username, email, password, role='student'):
    user = AppUser(username=username, email=email, role=role)
    user.set_password(password)
    return user


# ------------------ ROUTES ------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/choose_role')
def choose_role():
    return render_template('choose_role.html')


@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user, error = authenticate_user(email, password)
        if error:
            return jsonify({'error': error}), 400
        login_user(user)
        return jsonify({'success': f'Ingelogd als {user.role}!'}), 200
    return render_template('login.html')


@app.route('/login_bedrijf', methods=['GET', 'POST'])
def login_bedrijf():
    """Login voor recruiters/bedrijven —zelfde flow als student login maar controleert rol."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user, error = authenticate_user(email, password)
        if error:
            return jsonify({'error': error}), 400

        # Zorg dat alleen recruiters/bedrijven via deze route kunnen inloggen
        if not user or user.role != 'recruiter':
            return jsonify({'error': 'Geen bedrijf/recruiter account gevonden voor deze inloggegevens.'}), 403

        login_user(user)
        return jsonify({'success': f'Ingelogd als {user.role}!'}), 200
    return render_template('login_bedrijf.html')


@app.route('/logout')
@login_required
def logout_route():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register_route():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')

        existing_user = AppUser.query.filter((AppUser.email == email) | (AppUser.username == username)).first()
        if existing_user:
            return jsonify({'error': 'Dit emailadres of username is al gebruikt.'}), 400

        new_user = create_user(username=username, email=email, password=password, role=role)
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return jsonify({'success': 'Account aangemaakt en ingelogd!'}), 201
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'Kon account niet aanmaken.'}), 500

    return render_template('register.html')


@app.route('/register_bedrijf', methods=['GET', 'POST'])
def register_company_route():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        company_name = request.form.get('company_name', 'Onbekend')

        if AppUser.query.filter((AppUser.email == email) | (AppUser.username == username)).first():
            return jsonify({'error': 'Email of username al in gebruik.'}), 400

        try:
            new_employer = Employer(name=company_name)
            db.session.add(new_employer)
            db.session.flush()

            recruiter = create_user(username=username, email=email, password=password, role='recruiter')
            db.session.add(recruiter)
            db.session.flush()

            recruiter_link = RecruiterUser(employer_id=new_employer.id, user_id=recruiter.id, is_admin=True)
            db.session.add(recruiter_link)
            db.session.commit()

            login_user(recruiter)
            return jsonify({'success': f"Bedrijf '{company_name}' aangemaakt met recruiter {username}"}), 201
        except IntegrityError:
            db.session.rollback()
            return jsonify({'error': 'Kon bedrijf niet registreren.'}), 500

    return render_template('registratie_bedrijf.html')


@app.route('/api/vacatures', methods=['GET'])
def get_vacatures():
    vacatures = [
        {"id": 1, "title": "Student Kassamedewerker", "description": "Weekendjob in supermarkt", "location": "Gent"},
        {"id": 2, "title": "IT Support Student", "description": "Helpdesk op campus", "location": "Antwerpen"},
        {"id": 3, "title": "Barista", "description": "Studentenjob in koffiebar", "location": "Leuven"}
    ]
    return jsonify(vacatures)


@app.route('/api/notificatie', methods=['POST'])
def send_notificatie():
    data = request.json or {}
    vacature_id = data.get('vacatureId')
    app.logger.info(f"Student heeft vacature {vacature_id} geliket!")
    return jsonify({'message': 'Notificatie verzonden'}), 200


@app.route('/jobs/<int:job_id>/like', methods=['POST'])
@login_required
def like_job(job_id):
    user_id = current_user.id
    job = JobListing.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job bestaat niet'}), 404

    existing = JobLike.query.filter_by(user_id=user_id, job_id=job_id).first()
    if existing:
        return jsonify({'message': 'Job is al geliked'}), 200

    like = JobLike(user_id=user_id, job_id=job_id)
    db.session.add(like)
    db.session.commit()
    return jsonify({'message': 'Job geliked'}), 201


# ------------------ RECRUITER: LIST & DELETE OWN JOBS ------------------
@app.route('/api/my-jobs', methods=['GET'])
@login_required
def get_my_jobs():
    # Haal employer ids waar huidige gebruiker recruiter voor is
    recruiter_links = RecruiterUser.query.filter_by(user_id=current_user.id).all()
    employer_ids = [link.employer_id for link in recruiter_links]

    if not employer_ids:
        return jsonify([]), 200

    jobs = JobListing.query.filter(JobListing.employer_id.in_(employer_ids)).all()
    result = []
    for job in jobs:
        result.append({
            'id': int(job.id),
            'title': job.title,
            'location': job.location,
            'description': job.description or ''
        })
    return jsonify(result), 200


@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    job = JobListing.query.get(job_id)
    if not job:
        app.logger.info('Delete attempt failed: job %s not found (user %s)', job_id, getattr(current_user, 'id', None))
        return jsonify({'error': 'Job bestaat niet'}), 404

    app.logger.info('Delete attempt for job %s (employer_id=%s) by user %s', job_id, job.employer_id, getattr(current_user, 'id', None))

    # Controleer of huidige gebruiker recruiter is voor het bedrijf van de vacature
    recruiter_link = RecruiterUser.query.filter_by(
        user_id=current_user.id,
        employer_id=job.employer_id
    ).first()

    if not recruiter_link:
        app.logger.info('Delete denied: user %s is not recruiter for employer %s', current_user.id, job.employer_id)
        return jsonify({'error': 'Je hebt geen toestemming om deze vacature te verwijderen'}), 403

    try:
        # Verwijder gerelateerde likes en matches
        JobLike.query.filter_by(job_id=job_id).delete()
        Match.query.filter_by(job_id=job_id).delete()

        db.session.delete(job)
        db.session.commit()
        app.logger.info('Vacature %s verwijderd door user %s', job_id, current_user.id)
        return jsonify({'message': 'Vacature verwijderd'}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.exception('Fout bij verwijderen vacature %s', job_id)
        # stuur foutmelding terug (veilig: korte boodschap)
        return jsonify({'error': 'Interne serverfout bij verwijderen (zie server logs)'}), 500

@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    job = JobListing.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job bestaat niet'}), 404

    # Check of huidige recruiter eigenaar is van dit bedrijf
    recruiter_link = RecruiterUser.query.filter_by(
        user_id=current_user.id,
        employer_id=job.employer_id
    ).first()
    
    if not recruiter_link:
        return jsonify({'error': 'Je hebt geen toestemming om deze vacature te verwijderen'}), 403

    try:
        # Verwijder gerelateerde likes en matches
        JobLike.query.filter_by(job_id=job_id).delete()
        Match.query.filter_by(job_id=job_id).delete()
        
        # Verwijder de job
        db.session.delete(job)
        db.session.commit()
        return jsonify({'message': 'Vacature verwijderd'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Fout bij verwijdering: {str(e)}'}), 500
        


# ------------------ RECOMMENDATION LOGIC ------------------

def get_recommendations_for_user(user_id, limit=10):
    liked = JobLike.query.filter_by(user_id=user_id).all()
    if not liked:
        return JobListing.query.order_by(JobListing.created_at.desc()).limit(limit).all()

    liked_job_ids = [l.job_id for l in liked]
    liked_jobs = JobListing.query.filter(JobListing.id.in_(liked_job_ids)).all()

    description_word_counts = Counter()
    user_locations = set()
    liked_title_words = set()

    for job in liked_jobs:
        description_word_counts.update(tokenize(job.description))
        if job.location:
            user_locations.add(job.location.lower())
        liked_title_words.update(tokenize(job.title))

    all_jobs = JobListing.query.filter(~JobListing.id.in_(liked_job_ids)).all()
    scored = []

    for job in all_jobs:
        score = 0
        job_words = tokenize(job.description)
        word_overlap = sum(description_word_counts[w] for w in job_words if w in description_word_counts)
        score += word_overlap * 1.5

        if job.location and job.location.lower() in user_locations:
            score += 2

        job_title_words = tokenize(job.title)
        title_overlap = len(liked_title_words.intersection(job_title_words))
        score += title_overlap * 1

        if score > 0:
            scored.append((score, job))

    scored.sort(key=lambda x: x[0], reverse=True)
    recommendations = [job for score, job in scored[:limit]]
    return recommendations


@app.route('/recommend/jobs', methods=['GET'])
@login_required
def recommend_jobs_route():
    user_id = current_user.id
    recs = get_recommendations_for_user(user_id)
    result = []
    for r in recs:
        result.append({
            'id': int(r.id),
            'title': r.title,
            'location': r.location,
            'description': (r.description[:200] if r.description else '')
        })
    return jsonify(result), 200

STOPWORDS = load_stopwords_from_db()

def extract_keywords(text):
    if not text:
        return []

    words = re.findall(r"\w+", text.lower())

    return [w for w in words if w not in STOPWORDS]

# ------------------ DB DEBUG (ONE-TIME USE) ------------------
# with app.app_context():
#     db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
