import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user,
                         login_required, logout_user, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
from dotenv import load_dotenv

# laad .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    # Configure connection pool for Supabase
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 3,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'max_overflow': 0,
        'connect_args': {'connect_timeout': 10}
    }
else:
    # Use SQLite for local development to avoid Supabase connection limits
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tinderjobs.db'
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# If using a remote Postgres (e.g. Supabase) reduce pool size to avoid connection limits
if DATABASE_URL and DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 1,
        'max_overflow': 0,
        'pool_timeout': 30,
        'pool_pre_ping': True
    }

db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)
# als student login vereist is redirect naar login_student
login_manager.login_view = 'login_student'

# ------------------ Supabase client (optional) ------------------
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        supabase = None
        app.logger.exception('Kon Supabase client niet initialiseren')
else:
    supabase = None
    app.logger.warning('Supabase credentials niet gevonden; Supabase operaties zijn uitgeschakeld')


# -----------------------
# MODELS (volgens ER)
# -----------------------

class AppUser(UserMixin, db.Model):
    __tablename__ = 'app_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
    location = db.Column(db.String(120))
    contact_person = db.Column(db.String(120))
    btw_number = db.Column(db.String(60))
    description = db.Column(db.Text)
    contact_email = db.Column(db.String(120))
    is_agency = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recruiters = db.relationship('RecruiterUser', back_populates='employer')
    job_listings = db.relationship('JobListing', back_populates='employer')


class JobListing(db.Model):
    __tablename__ = 'job_listing'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('employer.id'), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(120))
    salary = db.Column(db.Numeric, nullable=True)
    periode = db.Column(db.String(80))
    requirements = db.Column(db.Text)
    posted_company_name = db.Column(db.String(200))
    client = db.Column(db.String(140))
    is_active = db.Column(db.Boolean, default=True)

    employer = db.relationship('Employer', back_populates='job_listings')
    matches = db.relationship('Match', back_populates='job')
    sectors = db.relationship('JobListingSector', back_populates='job')


class Match(db.Model):
    __tablename__ = 'match'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('app_user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listing.id'), nullable=False)
    matched_at = db.Column(db.DateTime, default=datetime.utcnow)
    notification_sent = db.Column(db.Boolean, default=False)
    notification_sent_at = db.Column(db.DateTime, nullable=True)
    notification_message = db.Column(db.Text, nullable=True)

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


class JobListingSector(db.Model):
    __tablename__ = 'job_listing_sector'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_listing.id'), nullable=False)
    sector_id = db.Column(db.Integer, db.ForeignKey('sector.id'), nullable=False)

    job = db.relationship('JobListing', back_populates='sectors')
    sector = db.relationship('Sector', back_populates='job_links')


class Sector(db.Model):
    __tablename__ = 'sector'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
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
        email = request.form.get('email')
        password = request.form.get('password')
        user = AppUser.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Foute email of wachtwoord!", "danger")
            return redirect(url_for('login_bedrijf'))
        if user.role != 'recruiter':
            flash("Dit account is geen bedrijf/recruiter account.", "danger")
            return redirect(url_for('login_bedrijf'))
        login_user(user)
        flash("Inloggen gelukt.", "success")
        # Redirect company login to the recruiter dashboard
        return redirect(url_for('recruiter_dashboard_view'))

    return render_template('login_bedrijf.html')


# student login - POST verwerkt, redirect naar vacatures_student
@app.route('/login_student', methods=['GET', 'POST'])
def login_student():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = AppUser.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Foute email of wachtwoord!", "danger")
            return redirect(url_for('login_student'))
        if user.role != 'student':
            flash("Dit account is geen student account.", "danger")
            return redirect(url_for('login_student'))
        login_user(user)
        return redirect('/vacatures_student')
    return render_template('login_student.html')


@app.route('/recruiter_dashboard')
def recruiter_dashboard_view():
    # If a recruiter is logged in, show vacatures for their employer; otherwise fallback to ACME BV
    jobs = []
    employer = None
    try:
        if current_user.is_authenticated and getattr(current_user, 'role', None) == 'recruiter':
            rec = RecruiterUser.query.filter_by(user_id=current_user.id).first()
            if rec and rec.employer:
                employer = rec.employer
    except Exception:
        employer = None

    if not employer:
        # fallback to default employer (if exists)
        employer = Employer.query.filter_by(name='ACME BV').first()

    if employer:
        jobs = JobListing.query.filter_by(employer_id=employer.id, is_active=True).all()

    # compute simple stats
    active_job_count = len(jobs)
    total_matches = 0
    matches_last_7_days = 0
    cutoff = datetime.utcnow() - timedelta(days=7)
    for job in jobs:
        # job.matches is a relationship (may be empty)
        jm = job.matches or []
        total_matches += len(jm)
        for m in jm:
            if m.matched_at and m.matched_at >= cutoff:
                matches_last_7_days += 1

    avg_matches_per_job = (total_matches / active_job_count) if active_job_count > 0 else 0

    stats = {
        'active_job_count': active_job_count,
        'total_matches': total_matches,
        'matches_last_7_days': matches_last_7_days,
        'avg_matches_per_job': avg_matches_per_job
    }

    # pass employer to template so dashboard can show recruiter/company contact details
    return render_template('recruiter_dashboard.html', stats=stats, jobs=jobs, employer=employer)


@app.route('/recruiter_profiel', methods=['GET', 'POST'])
@login_required
def recruiter_profiel():
    # Only recruiters may access this page
    if getattr(current_user, 'role', None) != 'recruiter':
        abort(403)

    user = current_user
    rec = getattr(user, 'recruiter', None)
    employer = rec.employer if rec else None

    if request.method == 'POST':
        # User fields
        email = request.form.get('email')
        password = request.form.get('password')

        # Employer/company fields
        company_name = request.form.get('company_name')
        contact_person = request.form.get('contact_person')
        description = request.form.get('description')
        contact_email = request.form.get('contact_email')
        btw_number = request.form.get('btw_number')
        is_agency = True if request.form.get('is_agency') == 'on' else False

        # validate unique email
        if email and email != user.email:
            if AppUser.query.filter_by(email=email).first():
                flash('Email is al in gebruik.', 'danger')
                return redirect(url_for('recruiter_profiel'))
            user.email = email

        if password:
            user.set_password(password)

        # ensure employer exists
        if not employer:
            # create new employer and link recruiter
            employer = Employer(name=company_name or 'Onbekend', contact_person=contact_person, description=description, contact_email=contact_email, is_agency=is_agency, btw_number=btw_number)
            db.session.add(employer)
            db.session.flush()
            if rec:
                rec.employer_id = employer.id
                db.session.add(rec)
        else:
            # update employer fields
            if company_name:
                employer.name = company_name
            employer.contact_person = contact_person
            employer.description = description
            employer.contact_email = contact_email
            employer.btw_number = btw_number
            employer.is_agency = is_agency
            db.session.add(employer)

        db.session.add(user)
        db.session.commit()
        flash('Profiel bijgewerkt.', 'success')
        return redirect(url_for('recruiter_dashboard_view'))

    # GET
    return render_template('recruiter_profiel.html', user=user, employer=employer)


@app.route('/save_profile', methods=['POST'])
def save_profile():
    return redirect(url_for('bedrijf_home'))


@app.route('/vacature/nieuw')
@login_required
def vacature_nieuw():
    # Only recruiters can place vacancies; pass employer info to template so the company name can be fixed
    employer = None
    if getattr(current_user, 'role', None) == 'recruiter':
        rec = RecruiterUser.query.filter_by(user_id=current_user.id).first()
        if rec and rec.employer:
            employer = rec.employer
    return render_template('vacatures_bedrijf.html', employer=employer)


@app.route('/vacature/opslaan', methods=['POST'])
def vacature_opslaan():
    job_title = request.form.get('jobTitle')
    location = request.form.get('location')
    description = request.form.get('description')
    client = request.form.get('client')
    company_name = request.form.get('companyName', 'ACME BV')  # Get company name from form, fallback to ACME BV
    
    # Find or create employer with the provided company name
    employer = Employer.query.filter_by(name=company_name).first()
    if not employer:
        employer = Employer(name=company_name, location=location)
        db.session.add(employer)
        db.session.commit()

    # create the job and persist
    job = JobListing(employer_id=employer.id,
                     title=job_title,
                     description=description,
                     location=location,
                     client=client)
    db.session.add(job)
    db.session.commit()

    flash("Vacature succesvol geplaatst ✅")
    # redirect to the public recruiter dashboard which will show posted vacatures
    return redirect('/recruiter_dashboard')


@app.route('/jobs/<int:job_id>/likes', methods=['GET'])
@login_required
def job_likes(job_id):
    # Only recruiters may view likes for their own job
    if getattr(current_user, 'role', None) != 'recruiter':
        return jsonify({'error': 'Toegang geweigerd'}), 403

    rec = RecruiterUser.query.filter_by(user_id=current_user.id).first()
    job = JobListing.query.get(job_id)
    if not job or not getattr(job, 'is_active', True):
        return jsonify({'error': 'Vacature niet gevonden'}), 404
    if not job:
        return jsonify({'error': 'Vacature niet gevonden'}), 404

    # ensure recruiter belongs to the employer that posted the job
    if not rec or not rec.employer or rec.employer.id != job.employer_id:
        return jsonify({'error': 'Toegang geweigerd'}), 403

    # Find users who liked (Match) this job
    matches = Match.query.filter_by(job_id=job.id).all()
    result = []
    for m in matches:
        user = AppUser.query.get(m.user_id)
        # try to include student name if present
        student = getattr(user, 'student', None)
        name = None
        if student:
            name = f"{student.first_name or ''} {student.last_name or ''}".strip()
        result.append({
            'user_id': user.id,
            'email': user.email,
            'name': name,
            'matched_at': m.matched_at.isoformat() if m.matched_at else None
        })

    return jsonify({'job_id': job.id, 'title': job.title, 'likes': result})


@app.route('/bedrijf')
def bedrijf_home():
    # Redirect to the recruiter dashboard — HomePage_bedrijf.html removed
    return redirect(url_for('recruiter_dashboard_view'))

    # Show company home, prefer the employer tied to the logged-in recruiter
    vacatures = []
    bedrijf_naam = "ACME BV"
    try:
        if current_user.is_authenticated and getattr(current_user, 'role', None) == 'recruiter':
            rec = RecruiterUser.query.filter_by(user_id=current_user.id).first()
            if rec and rec.employer:
                bedrijf_naam = rec.employer.name
    except Exception:
        # ignore and fall back to default
        pass

    return render_template('HomePage_bedrijf.html',
                           bedrijf_naam=bedrijf_naam,
                           vacatures=vacatures)


@app.route('/registratie_bedrijf', methods=['GET', 'POST'])
def registratie_bedrijf():
    if request.method == 'POST':
        company_name = request.form.get('companyName')
        vat_number   = request.form.get('vatNumber')
        email        = request.form.get('email')
        password     = request.form.get('password')
        contact_name = request.form.get('contactName')
        contact_phone= request.form.get('contactPhone', '')
        # Controleer of e-mail al bestaat lokaal
        if AppUser.query.filter_by(email=email).first():
            flash("Email is al in gebruik.", "danger")
            return redirect(url_for('registratie_bedrijf'))

        # Controleer ook in Supabase (indien geconfigureerd)
        if supabase:
            try:
                existing = supabase.table('app_user').select('id').eq('email', email).execute()
                if existing and getattr(existing, 'data', None) and len(existing.data) > 0:
                    flash("Email is al in gebruik (Supabase).", "danger")
                    return redirect(url_for('registratie_bedrijf'))
            except Exception:
                app.logger.exception('Fout bij check Supabase email')

        try:
            # 1) Schrijf naar Supabase als beschikbaar
            sup_emp_id = None
            sup_user_id = None
            if supabase:
                try:
                    timestamp = datetime.utcnow().isoformat()
                    # Insert employer
                    res_emp = supabase.table('employer').insert({
                        'name': company_name,
                        'contact_email': email,
                        'created_at': timestamp
                    }).execute()
                    if getattr(res_emp, 'error', None):
                        raise Exception(f"Supabase employer insert fout: {res_emp.error}")
                    sup_emp_id = res_emp.data[0].get('id') if res_emp.data else None

                    # Insert app_user (bewaar hashed password)
                    pwd_hash = generate_password_hash(password)
                    res_user = supabase.table('app_user').insert({
                        'email': email,
                        'role': 'recruiter',
                        'password_hash': pwd_hash,
                        'created_at': timestamp
                    }).execute()
                    if getattr(res_user, 'error', None):
                        raise Exception(f"Supabase user insert fout: {res_user.error}")
                    sup_user_id = res_user.data[0].get('id') if res_user.data else None

                    # Insert recruiter link
                    res_link = supabase.table('recruiter_user').insert({
                        'employer_id': sup_emp_id,
                        'user_id': sup_user_id,
                        'is_admin': True
                    }).execute()
                    if getattr(res_link, 'error', None):
                        raise Exception(f"Supabase recruiter_user insert fout: {res_link.error}")
                except Exception as se:
                    app.logger.exception('Supabase opslaan mislukt: %s', se)
                    flash('Kon gegevens niet naar Supabase schrijven. Probeer later.', 'danger')
                    return redirect(url_for('registratie_bedrijf'))

            # 2) Schrijf lokaal via SQLAlchemy (zodat de app huidige auth blijft gebruiken)
            employer = Employer(name=company_name, contact_email=email)
            db.session.add(employer)
            db.session.flush()

            user = AppUser(email=email, role='recruiter')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            rec = RecruiterUser(employer_id=employer.id, user_id=user.id, is_admin=True)
            db.session.add(rec)
            db.session.commit()

            flash("Account aangemaakt. Je kunt nu inloggen.", "success")
            return redirect(url_for('login_bedrijf'))
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Fout bij registratie bedrijf: %s', e)
            flash("Kon bedrijf niet registreren. Probeer opnieuw.", "danger")
            return redirect(url_for('registratie_bedrijf'))
    return render_template('registratie_bedrijf.html')


@app.route('/registratie_student', methods=['GET', 'POST'])
def registratie_student():
    if request.method == 'POST':
        # eenvoudige registratie: maak AppUser + Student en login direct naar vacatures_student
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')

        if AppUser.query.filter_by(email=email).first():
            flash("Email is al in gebruik.", "danger")
            return redirect(url_for('registratie_student'))

        user = AppUser(email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.id, first_name=first_name, last_name=last_name)
        db.session.add(student)
    db.session.commit()
    # After registration, require explicit login on the student login page
    flash("Account aangemaakt. Log in om verder te gaan.", "success")
    return redirect(url_for('login_student'))

    return render_template('registratie_student.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = AppUser.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Inloggen gelukt.", "success")
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
    # After logout, send user back to the initial homepage
    return redirect(url_for('index'))


# Student swipe dashboard
@app.route('/student_dashboard', methods=['GET', 'POST'])
@login_required
def student_dashboard():
    if current_user.role != 'student':
        abort(403)

    # Handle profile update (including password change) via POST
    if request.method == 'POST':
        first_name = request.form.get('firstName', '').strip()
        last_name = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('passwordConfirm', '')

        # Basic validation
        if password and password != password_confirm:
            return jsonify({'error': 'Wachtwoorden komen niet overeen'}), 400

        # Update AppUser email if changed and not taken
        if email and email != current_user.email:
            if AppUser.query.filter_by(email=email).first():
                return jsonify({'error': 'Email al in gebruik'}), 400
            current_user.email = email

        # Update password if provided
        if password:
            current_user.set_password(password)

        # Update Student profile
        student = getattr(current_user, 'student', None)
        if not student:
            student = Student(user_id=current_user.id, first_name=first_name, last_name=last_name)
            db.session.add(student)
        else:
            student.first_name = first_name
            student.last_name = last_name
            db.session.add(student)

        try:
            db.session.add(current_user)
            db.session.commit()
            return jsonify({'success': True}), 200
        except Exception as e:
            app.logger.exception('Fout bij opslaan student profiel')
            db.session.rollback()
            return jsonify({'error': 'Opslaan mislukt'}), 500

    # GET: render dashboard and pass server-side profile
    matched_job_ids = [m.job_id for m in current_user.matches]
    jobs = JobListing.query.filter(~JobListing.id.in_(matched_job_ids)).all()
    student = getattr(current_user, 'student', None)
    return render_template('student_dashboard.html', jobs=jobs, user=current_user, student=student)





@app.route('/student_dashboard_view')
@login_required
def student_dashboard_view():
    """Shared view of the student dashboard that can be used after bedrijf login.
    This does not enforce the role==student check so recruiters can be redirected here.
    """
    matched_job_ids = [m.job_id for m in current_user.matches] if getattr(current_user, 'matches', None) else []
    # only include active jobs for students
    if matched_job_ids:
        jobs = JobListing.query.filter(~JobListing.id.in_(matched_job_ids), JobListing.is_active == True).all()
    else:
        jobs = JobListing.query.filter(JobListing.is_active == True).all()
    # allow viewing as recruiter (no role check) but still provide student info if present
    student = getattr(current_user, 'student', None)
    return render_template('student_dashboard.html', jobs=jobs, user=current_user, student=student)



# Backwards-compatibility route: redirect /recruiter -> /recruiter_dashboard
@app.route('/recruiter')
@login_required
def recruiter_redirect():
    return redirect(url_for('recruiter_dashboard_view'))


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
        requirements = request.form.get('requirements')
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
    job = JobListing.query.get(job_id)
    if not job or not getattr(job, 'is_active', True):
        abort(404)
    # reuse vacancy detail template for students
    job.company_name = job.employer.name if job.employer else "Onbekend"
    liked = False
    if current_user.is_authenticated and hasattr(current_user, 'id'):
        liked = Match.query.filter_by(user_id=current_user.id, job_id=job.id).first() is not None
    return render_template('vacature_student.html', job=job, liked=liked)


# Student likes a job -> create match
@app.route('/jobs/<int:job_id>/like', methods=['POST'])
@login_required
def like_job(job_id):
    if current_user.role != 'student':
        abort(403)
    job = JobListing.query.get(job_id)
    if not job or not getattr(job, 'is_active', True):
        abort(404)
    existing = Match.query.filter_by(user_id=current_user.id, job_id=job.id).first()
    if existing:
        return redirect('/vacatures_student')
    m = Match(user_id=current_user.id, job_id=job.id)
    db.session.add(m)
    db.session.commit()
    return redirect('/vacatures_student')


@app.route('/jobs/<int:job_id>/dislike', methods=['POST'])
@login_required
def dislike_job(job_id):
    if current_user.role != 'student':
        abort(403)
    job = JobListing.query.get(job_id)
    if not job or not getattr(job, 'is_active', True):
        abort(404)
    # Check if already disliked
    existing_dislike = Dislike.query.filter_by(user_id=current_user.id, job_id=job_id).first()
    if not existing_dislike:
        dislike = Dislike(user_id=current_user.id, job_id=job_id)
        db.session.add(dislike)
        db.session.commit()
    return redirect('/vacatures_student')


@app.route('/jobs/<int:job_id>/delete', methods=['POST'])
@login_required
def delete_job(job_id):
    # Only recruiters that own the job's employer may delete the job
    if getattr(current_user, 'role', None) != 'recruiter':
        return jsonify({'error': 'Toegang geweigerd'}), 403

    rec = RecruiterUser.query.filter_by(user_id=current_user.id).first()
    job = JobListing.query.get(job_id)
    if not job:
        return jsonify({'error': 'Vacature niet gevonden'}), 404

    if not rec or not rec.employer or rec.employer.id != job.employer_id:
        return jsonify({'error': 'Toegang geweigerd'}), 403

    try:
        # permanent deletion endpoint (called after undo window)
        # remove dependent rows first to avoid orphans
        Match.query.filter_by(job_id=job.id).delete()
        Dislike.query.filter_by(job_id=job.id).delete()
        JobListingSector.query.filter_by(job_id=job.id).delete()
        db.session.delete(job)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.exception('Fout bij verwijderen vacature')
        return jsonify({'error': 'Verwijderen mislukt'}), 500


@app.route('/jobs/<int:job_id>/deactivate', methods=['POST'])
@login_required
def deactivate_job(job_id):
    # Mark job as inactive immediately so students don't see it
    if getattr(current_user, 'role', None) != 'recruiter':
        return jsonify({'error': 'Toegang geweigerd'}), 403

    rec = RecruiterUser.query.filter_by(user_id=current_user.id).first()
    job = JobListing.query.get(job_id)
    if not job:
        return jsonify({'error': 'Vacature niet gevonden'}), 404

    if not rec or not rec.employer or rec.employer.id != job.employer_id:
        return jsonify({'error': 'Toegang geweigerd'}), 403

    try:
        job.is_active = False
        db.session.add(job)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Deactiveren mislukt'}), 500


@app.route('/jobs/<int:job_id>/restore', methods=['POST'])
@login_required
def restore_job(job_id):
    # Restore a deactivated job (used by undo)
    if getattr(current_user, 'role', None) != 'recruiter':
        return jsonify({'error': 'Toegang geweigerd'}), 403

    rec = RecruiterUser.query.filter_by(user_id=current_user.id).first()
    job = JobListing.query.get(job_id)
    if not job:
        return jsonify({'error': 'Vacature niet gevonden'}), 404

    if not rec or not rec.employer or rec.employer.id != job.employer_id:
        return jsonify({'error': 'Toegang geweigerd'}), 403

    try:
        job.is_active = True
        db.session.add(job)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Herstel mislukt'}), 500


# Matches overzicht
@app.route('/match_page')
@login_required
def match_page():
    if current_user.role == 'recruiter':
        rec = current_user.recruiter
        formatted = []
        if rec and rec.employer:
            for job in rec.employer.job_listings:
                for m in job.matches:
                    # ensure company name available on job for template
                    j = m.job
                    try:
                        j.company_name = j.posted_company_name or (j.employer.name if j.employer else 'Onbekend')
                    except Exception:
                        j.company_name = getattr(j, 'posted_company_name', None) or 'Onbekend'
                    formatted.append({'match': m, 'job': j})
        return render_template('match_page.html', matches=formatted)
    else:
        # For students, get their matches and format them for the template
        matches = current_user.matches
        formatted_matches = []
        for match in matches:
            j = match.job
            # attach a company_name attribute for template convenience
            try:
                j.company_name = j.posted_company_name or (j.employer.name if j.employer else 'Onbekend')
            except Exception:
                j.company_name = getattr(j, 'posted_company_name', None) or 'Onbekend'
            formatted_matches.append({
                'match': match,
                'user': current_user,
                'job': j
            })
        return render_template('match_page.html', matches=formatted_matches)


# Employer profile
@app.route('/employer/<int:employer_id>')
@login_required
def employer_profile(employer_id):
    emp = Employer.query.get_or_404(employer_id)
    return render_template('employer_profile.html', employer=emp)


@app.route("/student/vacature/<int:job_id>")
def student_vacature(job_id):
    job = JobListing.query.get_or_404(job_id)
    # Provide company_name and liked flag for the student vacancy view
    job.company_name = job.employer.name if job.employer else "Onbekend"
    liked = False
    if current_user.is_authenticated and hasattr(current_user, 'id'):
        liked = Match.query.filter_by(user_id=current_user.id, job_id=job.id).first() is not None
    return render_template("vacature_student.html", job=job, liked=liked)


@app.route("/test/vacature")
def test_vacature():
    class FakeJob:
        title = "Student Marketeer"
        company_name = "Cool Company"
        location = "Gent"
        description = "Je promoot ons merk op campussen."
    job = FakeJob()
    return render_template("vacature_student.html", job=job)


@app.route('/_init_demo')
def init_demo():
    if Sector.query.first():
        return "Demo al geïnitialiseerd."
    s1 = Sector(name='Horeca')
    s2 = Sector(name='Retail')
    db.session.add_all([s1, s2])
    db.session.commit()
    return "Demo sectors aangemaakt."


@app.route("/test-supabase")
def test_supabase():
    if not supabase:
        return "Supabase niet geconfigureerd."
    try:
        response = supabase.table("app_user").select("*").limit(1).execute()
        return f"Connected to Supabase! Sample data: {response.data}"
    except Exception as e:
        return f"Supabase connection failed: {str(e)}"




# ------------------ UTILITIES ------------------
def load_stopwords():
    return {
        "de","het","een","en","van","met","je","jij","u","ik","hij","zij","we","wij","ze",
        "die","dat","dit","daar","hier","als","maar","om","te","is","in","op","voor","naar",
        "door","aan","tot","uit","bij","ook","wat","hoe","waar","wanneer","wel","niet","geen",
        "zijn","was","wordt","heb","heeft","hebben","kan","kunnen","moet","moeten","zal","zullen"
    }

STOPWORDS = load_stopwords()



# eenvoudige vacatures pagina voor studenten
@app.route('/vacatures_student')
@login_required
def vacatures_student():
    if current_user.role != 'student':
        flash('Alleen studenten kunnen deze pagina bekijken.', 'danger')
        return redirect(url_for('index'))

    # Import stopwords loader
    from utils.stopwords import load_stopwords_from_db

    # Get stopwords from DB if possible, else fallback
    try:
        stopwords = load_stopwords_from_db()
        if not stopwords:
            stopwords = STOPWORDS
    except Exception:
        stopwords = STOPWORDS

    # Get all jobs not liked or disliked by the student
    jobs = JobListing.query.all()
    liked_matches = Match.query.filter_by(user_id=current_user.id).all()
    liked_job_ids = [m.job_id for m in liked_matches]
    disliked_job_ids = [d.job_id for d in Dislike.query.filter_by(user_id=current_user.id).all()]

    # Collect words from liked jobs (title, description, location)
    liked_words = []
    for m in liked_matches:
        job = JobListing.query.get(m.job_id)
        if job:
            fields = f"{job.title} {job.description or ''} {job.location or ''}"
            liked_words.extend(fields.lower().split())
    # Remove stopwords
    liked_words = [w for w in liked_words if w not in stopwords]
    liked_word_set = set(liked_words)

    def job_fit_score_and_pct(job):
        # Score = overlap of job words with liked_word_set
        fields = f"{job.title} {job.description or ''} {job.location or ''}"
        job_words = [w for w in fields.lower().split() if w not in stopwords]
        overlap = len(set(job_words) & liked_word_set)
        total = len(set(job_words))
        pct = int((overlap / total) * 100) if total > 0 else 0
        return overlap, pct

    jobs_to_show = []
    for job in jobs:
        if job.id in liked_job_ids or job.id in disliked_job_ids:
            continue
        job.company_name = job.employer.name if job.employer else "Onbekend"
        overlap, pct = job_fit_score_and_pct(job)
        jobs_to_show.append({'job': job, 'liked': False, 'fit_pct': pct, 'overlap': overlap})

    # Sort jobs by fit percentage (descending), then by overlap score (descending)
    # This ensures highest matching jobs appear first
    jobs_sorted = sorted(jobs_to_show, key=lambda x: (x['fit_pct'], x['overlap']), reverse=True)

    return render_template('vacatures_list.html', jobs=jobs_sorted)


# -----------------------
# SEED DATA
# -----------------------
def seed_database():
    """Create sample data if database is empty"""
    with app.app_context():
        db.create_all()
        
        # Check if database already has data
        if JobListing.query.first():
            return  # Data already exists
        
        # Create sample employers
        employers = [
            Employer(name='ACME BV', location='Amsterdam', description='A leading tech company'),
            Employer(name='TechCorp', location='Utrecht', description='Innovation in software'),
            Employer(name='WebDesign Inc', location='Rotterdam', description='Digital solutions'),
            Employer(name='DataSystems', location='Groningen', description='Big data & analytics'),
        ]
        
        for emp in employers:
            db.session.add(emp)
        db.session.commit()
        
        # Create sample job listings
        jobs_data = [
            {
                'employer_id': employers[0].id,
                'title': 'Python Developer',
                'description': 'We are looking for an experienced Python developer to join our growing team. Experience with Django and FastAPI required.',
                'location': 'Amsterdam',
                'salary': 3500,
                'periode': '6 months'
            },
            {
                'employer_id': employers[1].id,
                'title': 'Frontend Developer',
                'description': 'Looking for a skilled React/Vue developer. Must have experience with modern JavaScript frameworks and responsive design.',
                'location': 'Utrecht',
                'salary': 3200,
                'periode': '4 months'
            },
            {
                'employer_id': employers[2].id,
                'title': 'Full Stack Developer',
                'description': 'Develop both backend and frontend solutions. Tech stack includes Node.js, React, and PostgreSQL.',
                'location': 'Rotterdam',
                'salary': 3800,
                'periode': '6 months'
            },
            {
                'employer_id': employers[3].id,
                'title': 'Data Analyst',
                'description': 'Analyze large datasets and create insights. Experience with Python, SQL, and visualization tools required.',
                'location': 'Groningen',
                'salary': 2800,
                'periode': '3 months'
            },
            {
                'employer_id': employers[0].id,
                'title': 'DevOps Engineer',
                'description': 'Manage cloud infrastructure and CI/CD pipelines. Experience with Docker, Kubernetes, and AWS needed.',
                'location': 'Amsterdam',
                'salary': 4000,
                'periode': '6 months'
            },
            {
                'employer_id': employers[1].id,
                'title': 'UI/UX Designer',
                'description': 'Design user-friendly interfaces for web applications. Portfolio and experience with Figma required.',
                'location': 'Utrecht',
                'salary': 2900,
                'periode': '3 months'
            },
        ]
        
        for job_data in jobs_data:
            job = JobListing(**job_data)
            db.session.add(job)
        db.session.commit()

# -----------------------
# START
# -----------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
# ...existing code...