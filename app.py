# app.py
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         login_required, logout_user, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
from dotenv import load_dotenv

# laad .env (optioneel)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_KEY:", SUPABASE_KEY)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

# Database config: gebruik DATABASE_URL wanneer beschikbaar (bv. Postgres),
# anders fallback naar sqlite voor development.
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tinderjobs.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# -----------------------
# MODELS (volgens ER)
# -----------------------

class AppUser(UserMixin, db.Model):
    __tablename__ = 'app_user'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' of 'recruiter'
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relaties
    student = db.relationship('Student', uselist=False, back_populates='user')
    recruiter = db.relationship('RecruiterUser', uselist=False, back_populates='user')
    matches = db.relationship('Match', back_populates='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Flask-Login vereist .get_id(); UserMixin levert dat.


class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('app_user.id'), nullable=False)
    first_name = db.Column(db.String(60))
    last_name = db.Column(db.String(60))

    user = db.relationship('AppUser', back_populates='student')


class RecruiterUser(db.Model):
    __tablename__ = 'recruiter_user'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    employer_id = db.Column(db.BigInteger, db.ForeignKey('employer.id'), nullable=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('app_user.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    user = db.relationship('AppUser', back_populates='recruiter')
    employer = db.relationship('Employer', back_populates='recruiters')


class Employer(db.Model):
    __tablename__ = 'employer'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(120))
    description = db.Column(db.Text)
    contact_email = db.Column(db.String(120))
    is_agency = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recruiters = db.relationship('RecruiterUser', back_populates='employer')
    job_listings = db.relationship('JobListing', back_populates='employer')


class JobListing(db.Model):
    __tablename__ = 'job_listing'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    employer_id = db.Column(db.BigInteger, db.ForeignKey('employer.id'), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(120))
    salary = db.Column(db.Numeric, nullable=True)
    periode = db.Column(db.String(80))  # houd simpel (tekst)
    # requirements als comma-separated string (of later JSON/ARRAY)
    requirements = db.Column(db.Text)

    employer = db.relationship('Employer', back_populates='job_listings')
    matches = db.relationship('Match', back_populates='job')
    sectors = db.relationship('JobListingSector', back_populates='job')


class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('app_user.id'), nullable=False)
    job_id = db.Column(db.BigInteger, db.ForeignKey('job_listing.id'), nullable=False)
    matched_at = db.Column(db.DateTime, default=datetime.utcnow)
    notification_sent = db.Column(db.Boolean, default=False)
    notification_sent_at = db.Column(db.DateTime, nullable=True)
    notification_message = db.Column(db.Text, nullable=True)

    user = db.relationship('AppUser', back_populates='matches')
    job = db.relationship('JobListing', back_populates='matches')


class JobListingSector(db.Model):
    __tablename__ = 'job_listing_sector'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    job_id = db.Column(db.BigInteger, db.ForeignKey('job_listing.id'), nullable=False)
    sector_id = db.Column(db.BigInteger, db.ForeignKey('sector.id'), nullable=False)

    job = db.relationship('JobListing', back_populates='sectors')
    sector = db.relationship('Sector', back_populates='job_links')


class Sector(db.Model):
    __tablename__ = 'sector'
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    job_links = db.relationship('JobListingSector', back_populates='sector')


# -----------------------
# Login loader
# -----------------------
@login_manager.user_loader
def load_user(user_id):
    try:
        return AppUser.query.get(int(user_id))
    except Exception:
        return None


# -----------------------
# ROUTES (eenvoudig)
# -----------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login_bedrijf', methods=['GET', 'POST'])
def login_bedrijf():
    if request.method == 'POST':
        # hier zou je normaal login-validatie doen
        return redirect(url_for('bedrijf_home'))
    return render_template('login_bedrijf.html')

@app.route('/login_student', methods=['GET', 'POST'])
def login_student():
    return render_template('login_student.html')

@app.route('/recruiter_dashboard')
def recruiter_dashboard_view():
    return render_template('recruiter_dashboard.html')

@app.route('/save_profile', methods=['POST'])
def save_profile():
    # hier zou je normaal de form data opslaan
    # bv. companyName = request.form['companyName']
    # vatNumber = request.form['vatNumber']
    # etc.

    # na opslaan → terug naar homepage bedrijf
    return redirect(url_for('bedrijf_home'))

@app.route('/vacature/nieuw')
def vacature_nieuw():
    # Render de pagina waar een nieuwe vacature kan worden aangemaakt
    return render_template('vacatures_bedrijf.html')

@app.route('/vacature/opslaan', methods=['POST'])
def vacature_opslaan():
    # hier kan je de form data ophalen
    job_title = request.form['jobTitle']
    location = request.form['location']
    description = request.form['description']
    # normaal zou je dit opslaan in een database

    flash("Vacature succesvol geplaatst ✅")
    return redirect(url_for('bedrijf_home'))

@app.route('/bedrijf')
def bedrijf_home():
    bedrijf_naam = "ACME BV"
    vacatures = []  # of echte data
    return render_template('HomePage_bedrijf.html',
                           bedrijf_naam=bedrijf_naam,
                           vacatures=vacatures)


@app.route('/registratie_bedrijf', methods=['GET', 'POST'])
def registratie_bedrijf():
    if request.method == 'POST':
        print("POST ontvangen:", request.form)  # <- zie dit in je terminal
        # haal velden op (namen moeten matchen met je 'name' in HTML)
        company_name = request.form['companyName']
        vat_number   = request.form['vatNumber']
        email        = request.form['email']
        password     = request.form['password']
        contact_name = request.form['contactName']
        contact_phone= request.form.get('contactPhone', '')

        # hier eventueel opslaan...
        return redirect(url_for('login_bedrijf'))

    return render_template('registratie_bedrijf.html')


@app.route('/registratie_student', methods=['GET', 'POST'])
def registratie_student():
    if request.method == 'POST':
        # handle student registration
        return redirect(url_for('login_student'))
    return render_template('registratie_student.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')

        if not email or not password or not role:
            flash("Vul email, wachtwoord en rol in.", "danger")
            return redirect(url_for('register'))

        if AppUser.query.filter_by(email=email).first():
            flash("E-mail bestaat al.", "danger")
            return redirect(url_for('register'))

        user = AppUser(email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        if role == 'student':
            student = Student(user_id=user.id, first_name=first_name, last_name=last_name)
            db.session.add(student)
            db.session.commit()
        # voor recruiter: later kan recruiter-account aan employer gekoppeld worden

        flash("Account aangemaakt. Log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = AppUser.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Inloggen gelukt.", "success")
            # route naar dashboard afhankelijk van rol
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('recruiter_dashboard'))
        else:
            flash("Foute email of wachtwoord!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Uitgelogd.", "info")
    return redirect(url_for('login'))


# Student swipe dashboard (eenvoudig: lijst van jobs en like button)
@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        abort(403)
    # toon jobs die nog niet gematcht zijn met deze user
    matched_job_ids = [m.job_id for m in current_user.matches]
    jobs = JobListing.query.filter(~JobListing.id.in_(matched_job_ids)).all()
    return render_template('student_dashboard.html', jobs=jobs)


# Recruiter dashboard: overzicht eigen vacatures
@app.route('/recruiter')
@login_required
def recruiter_dashboard():
    if current_user.role != 'recruiter':
        abort(403)
    # vind recruiter record en bijhorende employer jobs (vereenvoudigd)
    rec = current_user.recruiter
    jobs = []
    if rec and rec.employer:
        jobs = rec.employer.job_listings
    return render_template('recruiter_dashboard.html', jobs=jobs)


# Create job (recruiter)
@app.route('/jobs/create', methods=['GET', 'POST'])
@login_required
def create_job():
    if current_user.role != 'recruiter':
        abort(403)
    rec = current_user.recruiter
    if not rec or not rec.employer:
        flash("Je moet gekoppeld zijn aan een werkgever om vacatures te plaatsen.", "danger")
        return redirect(url_for('recruiter_dashboard'))

    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        salary = request.form.get('salary') or None
        periode = request.form.get('periode')
        description = request.form.get('description')
        requirements = request.form.get('requirements')  # comma-separated

        job = JobListing(
            employer_id=rec.employer.id,
            title=title,
            location=location,
            salary=salary,
            periode=periode,
            description=description,
            requirements=requirements
        )
        db.session.add(job)
        db.session.commit()
        flash("Vacature aangemaakt.", "success")
        return redirect(url_for('recruiter_dashboard'))

    return render_template('create_job.html')


# Job detail
@app.route('/jobs/<int:job_id>')
@login_required
def job_detail(job_id):
    job = JobListing.query.get_or_404(job_id)
    return render_template('job_detail.html', job=job)


# Student likes a job -> create match
@app.route('/jobs/<int:job_id>/like', methods=['POST'])
@login_required
def like_job(job_id):
    if current_user.role != 'student':
        abort(403)
    job = JobListing.query.get_or_404(job_id)

    # check of match al bestaat
    existing = Match.query.filter_by(user_id=current_user.id, job_id=job.id).first()
    if existing:
        flash("Je hebt deze job al geliked.", "info")
        return redirect(url_for('student_dashboard'))

    m = Match(user_id=current_user.id, job_id=job.id)
    db.session.add(m)
    db.session.commit()
    flash("Match geregistreerd! Wacht op bevestiging van recruiter.", "success")
    return redirect(url_for('student_dashboard'))


# Matches overzicht (voor recruiter: alle matches voor jobs van hun employer)
@app.route('/matches')
@login_required
def match_page():
    if current_user.role == 'recruiter':
        rec = current_user.recruiter
        matches = []
        if rec and rec.employer:
            # alle matches voor employer jobs
            for job in rec.employer.job_listings:
                for m in job.matches:
                    matches.append(m)
        return render_template('match_page.html', matches=matches)
    else:
        # student: toon eigen matches
        matches = current_user.matches
        return render_template('match_page.html', matches=matches)


# Employer profile
@app.route('/employer/<int:employer_id>')
@login_required
def employer_profile(employer_id):
    emp = Employer.query.get_or_404(employer_id)
    return render_template('employer_profile.html', employer=emp)


# eenvoudige helper route om demo data aan te maken (optioneel)
@app.route('/_init_demo')
def init_demo():
    # enkel als er nog geen sectors bestaan
    if Sector.query.first():
        return "Demo al geïnitialiseerd."
    s1 = Sector(name='Horeca')
    s2 = Sector(name='Retail')
    db.session.add_all([s1, s2])
    db.session.commit()
    return "Demo sectors aangemaakt."

@app.route("/test-supabase")
def test_supabase():
    try:
        response = supabase.table("app_user").select("*").limit(1).execute()
        return f"Connected to Supabase! Sample data: {response.data}"
    except Exception as e:
        return f"Supabase connection failed: {str(e)}"


# -----------------------
# START
# -----------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # voor dev: debug True
    app.run(debug=True)
