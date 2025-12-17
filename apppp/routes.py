from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta

from app import app, supabase
from apppp.models import (db, AppUser, Student, RecruiterUser, Employer, JobListing, Match, Dislike, 
                          get_employer_for_current_user, get_current_recruiter, recruiter_owns_job, populate_jobs_display_fields, 
                          get_unseen_jobs_for_user
)
from apppp.models import STOPWORDS

from utils.stopwords import load_stopwords_from_db


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
        return redirect(url_for('recruiter_dashboard_view'))
    return render_template('login_bedrijf.html')


@app.route('/login_student', methods=['GET', 'POST'])
def login_student():
    if request.method == 'POST':
        agree = request.form.get('agree_terms')
        if agree != 'on':
            flash("Je moet de algemene voorwaarden accepteren.", "danger")
            return redirect(url_for('login_student'))

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
        return redirect(url_for('vacatures_student'))
    return render_template('login_student.html')


@app.route('/student_dashboard')
@login_required
def student_dashboard_view():
    jobs = get_unseen_jobs_for_user(current_user)
    student = getattr(current_user, 'student', None)
    return render_template('student_dashboard.html', jobs=jobs, student=student, user=current_user)


@app.route('/recruiter_dashboard')
@login_required
def recruiter_dashboard_view():
    employer = get_employer_for_current_user()
    jobs = []
    if employer:
        jobs = JobListing.query.filter_by(employer_id=employer.id, is_active=True).all()

    populate_jobs_display_fields(jobs)
    jobs = sorted(jobs, key=lambda j: getattr(j, 'match_count', 0), reverse=True)

    active_job_count = len(jobs)
    total_matches = sum(len(getattr(j, 'matches', []) or []) for j in jobs)
    cutoff = datetime.utcnow() - timedelta(days=7)
    matches_last_7_days = sum(
        1 for j in jobs for m in (j.matches or []) if getattr(m, 'matched_at', None) and m.matched_at >= cutoff
    )
    avg_matches_per_job = (total_matches / active_job_count) if active_job_count > 0 else 0

    stats = {
        'active_job_count': active_job_count,
        'total_matches': total_matches,
        'matches_last_7_days': matches_last_7_days,
        'avg_matches_per_job': avg_matches_per_job,
    }

    return render_template('recruiter_dashboard.html', stats=stats, jobs=jobs)


@app.route('/recruiter/job_counts')
@login_required
def recruiter_job_counts():
    if getattr(current_user, 'role', None) != 'recruiter':
        return jsonify({'error': 'Toegang geweigerd'}), 403

    employer = get_employer_for_current_user()
    if not employer:
        return jsonify({'error': 'Geen werkgever gevonden'}), 404

    jobs = JobListing.query.filter_by(employer_id=employer.id, is_active=True).all()
    counts = {j.id: Match.query.filter_by(job_id=j.id).count() for j in jobs}
    total_matches = sum(counts.values())
    return jsonify({'counts': counts, 'total_matches': total_matches})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/registratie_bedrijf', methods=['GET', 'POST'])
def registratie_bedrijf():
    if request.method == 'POST':
        company_name = request.form.get('companyName')
        email = request.form.get('email')
        password = request.form.get('password')
        if AppUser.query.filter_by(email=email).first():
            flash("Email is al in gebruik.", "danger")
            return redirect(url_for('registratie_bedrijf'))

        try:
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

            flash("Account aangemaakt.", "success")
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
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')

        if AppUser.query.filter_by(email=email).first():
            flash("Email is al in gebruik.", "danger")
            return redirect(url_for('registratie_student'))

        try:
            user = AppUser(email=email, role='student')
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            student = Student(user_id=user.id, first_name=first_name, last_name=last_name)
            db.session.add(student)
            db.session.commit()

            flash("Account aangemaakt.", "success")
            return redirect(url_for('login_student'))
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Fout bij registratie student: %s', e)
            flash("Kon student niet registreren. Probeer opnieuw.", "danger")
            return redirect(url_for('registratie_student'))
    return render_template('registratie_student.html')


@app.route('/match_page')
@login_required
def match_page():
    # Show matches: recruiters see matches for their employer's jobs, students see their own matches
    if getattr(current_user, 'role', None) == 'recruiter':
        rec = get_employer_for_current_user()  # returns Employer via recruiter
        matches = []
        if rec:
            for job in rec.job_listings:
                for m in job.matches:
                    matches.append(m)
        return render_template('match_page.html', matches=matches)
    else:
        matches = current_user.matches or []
        formatted = [{'match': match, 'user': current_user, 'job': match.job} for match in matches]
        return render_template('match_page.html', matches=formatted)


@app.route('/vacatures_student')
@login_required
def vacatures_student():
    # List active jobs for students with a simple fit scoring based on previously liked jobs
    if getattr(current_user, 'role', None) != 'student':
        flash('Alleen studenten kunnen deze pagina bekijken.', 'danger')
        return redirect(url_for('index'))

    try:
        stopwords = load_stopwords_from_db()
        if not stopwords:
            stopwords = STOPWORDS
    except Exception:
        stopwords = STOPWORDS

    jobs = JobListing.query.filter_by(is_active=True).all()
    liked_matches = Match.query.filter_by(user_id=current_user.id).all()
    liked_job_ids = [m.job_id for m in liked_matches]
    disliked_job_ids = [d.job_id for d in Dislike.query.filter_by(user_id=current_user.id).all()]

    liked_words = []
    for m in liked_matches:
        job = JobListing.query.get(m.job_id)
        if job:
            fields = f"{job.title} {job.description or ''} {job.location or ''}"
            liked_words.extend(fields.lower().split())

    liked_words = [w for w in liked_words if w not in stopwords]
    liked_word_set = set(liked_words)

    def job_fit_score_and_pct(job):
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
        job.company_name = job.employer.name if job.employer else 'Onbekend'
        overlap, pct = job_fit_score_and_pct(job)
        jobs_to_show.append({'job': job, 'liked': False, 'fit_pct': pct, 'overlap': overlap})

    jobs_sorted = sorted(jobs_to_show, key=lambda x: (x['fit_pct'], x['overlap']), reverse=True)
    return render_template('vacatures_list.html', jobs=jobs_sorted)


@app.route('/recruiter_profiel', methods=['GET', 'POST'])
@login_required
def recruiter_profiel():
    # Only recruiters should access this page
    if getattr(current_user, 'role', None) != 'recruiter':
        flash('Alleen recruiters kunnen deze pagina bekijken.', 'danger')
        return redirect(url_for('index'))

    rec = get_current_recruiter()
    employer = rec.employer if rec and getattr(rec, 'employer', None) else None

    if request.method == 'POST':
        company_name = request.form.get('company_name')
        contact_person = request.form.get('contact_person')
        contact_email = request.form.get('contact_email')
        btw_number = request.form.get('btw_number')
        password = request.form.get('password')

        try:
            # update or create employer
            if not employer:
                employer = Employer(name=company_name or 'Onbekend', contact_email=contact_email, btw_number=btw_number)
                db.session.add(employer)
                db.session.flush()
                if rec:
                    rec.employer_id = employer.id
                    db.session.add(rec)
            else:
                employer.name = company_name or employer.name
                employer.contact_person = contact_person or employer.contact_person
                employer.contact_email = contact_email or employer.contact_email
                employer.btw_number = btw_number or employer.btw_number
                db.session.add(employer)

            # update user email/password
            if current_user and request.form.get('email'):
                new_email = request.form.get('email')
                if new_email and new_email != current_user.email:
                    if AppUser.query.filter_by(email=new_email).first():
                        flash('Email is al in gebruik.', 'danger')
                        return redirect(url_for('recruiter_profiel'))
                    current_user.email = new_email
                    db.session.add(current_user)

            if password:
                current_user.set_password(password)
                db.session.add(current_user)

            db.session.commit()
            flash('Profiel bijgewerkt.', 'success')
            return redirect(url_for('recruiter_profiel'))
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Fout bij bijwerken recruiter profiel: %s', e)
            flash('Kon profiel niet opslaan. Probeer opnieuw.', 'danger')
            return redirect(url_for('recruiter_profiel'))

    return render_template('recruiter_profiel.html', user=current_user, employer=employer)


@app.route('/vacature/nieuw', methods=['GET', 'POST'])
@login_required
def vacature_nieuw():

    if getattr(current_user, 'role', None) != 'recruiter':
        flash('Alleen recruiters kunnen vacatures aanmaken.', 'danger')
        return redirect(url_for('index'))

    rec = get_current_recruiter()
    if not rec or not getattr(rec, 'employer', None):
        flash('Geen werkgever gekoppeld. Neem contact op met de beheerder.', 'danger')
        return redirect(url_for('recruiter_dashboard_view'))

    employer = rec.employer

    if request.method == 'POST':
        title = request.form.get('title') or request.form.get('jobTitle')
        client = request.form.get('client')
        location = request.form.get('location')
        description = request.form.get('description')

        if not title:
            flash('Titel is verplicht.', 'danger')
            return redirect(url_for('vacature_nieuw'))

        try:
            job = JobListing(
                employer_id=employer.id,
                client=client,
                title=title,
                location=location,
                description=description,
                is_active=True,
            )
            db.session.add(job)
            db.session.commit()
            flash('Vacature succesvol geplaatst ✅', 'success')
            return redirect(url_for('recruiter_dashboard_view'))
        except Exception as e:
            db.session.rollback()
            app.logger.exception('Fout bij aanmaken vacature: %s', e)
            flash('Kon vacature niet aanmaken. Probeer opnieuw.', 'danger')
            return redirect(url_for('vacature_nieuw'))

    try:
        return render_template('vacature_nieuw.html', employer=employer)
    except Exception:
        # Fallback: render the company vacancies page if the specific template doesn't exist
        return render_template('vacatures_bedrijf.html', employer=employer)



@app.route('/vacature/opslaan', methods=['POST'])
@login_required
def vacature_opslaan():

    # Only recruiters may create jobs
    if getattr(current_user, 'role', None) != 'recruiter':
        flash('Alleen recruiters kunnen vacatures aanmaken.', 'danger')
        return redirect(url_for('index'))

    # Prefer the employer linked to the logged-in recruiter
    rec = get_current_recruiter()
    employer = rec.employer if rec and getattr(rec, 'employer', None) else None

    # If the template provided an employer_id, try to use it (but ensure the logged-in recruiter can create for it)
    form_employer_id = request.form.get('employer_id') or request.form.get('employerId')
    form_company = request.form.get('companyName') or request.form.get('company')

    if not employer and form_employer_id:
        try:
            employer = Employer.query.get(int(form_employer_id))
        except Exception:
            employer = None

    # If still no employer, but a company name was provided, create or find a matching employer
    if not employer and form_company:
        employer = Employer.query.filter_by(name=form_company).first()
        if not employer:
            employer = Employer(name=form_company, contact_email=None)
            db.session.add(employer)
            db.session.flush()

    if not employer:
        flash('Geen werkgever gekoppeld of opgegeven. Neem contact op met de beheerder.', 'danger')
        return redirect(url_for('recruiter_dashboard_view'))

    # Extract job fields from the form (support both current and legacy field names)
    title = request.form.get('jobTitle') or request.form.get('title') or request.form.get('position')
    client = request.form.get('client')
    location = request.form.get('location')
    description = request.form.get('description')

    if not title:
        flash('Titel is verplicht.', 'danger')
        return redirect(url_for('vacature_nieuw'))

    try:
        job = JobListing(
            employer_id=employer.id,
            client=client,
            title=title,
            location=location,
            description=description,
            is_active=True,
        )
        db.session.add(job)
        db.session.commit()
        flash('Vacature succesvol geplaatst ✅', 'success')
        return redirect(url_for('recruiter_dashboard_view'))
    except Exception as e:
        db.session.rollback()
        app.logger.exception('Fout bij opslaan vacature (opslaan endpoint): %s', e)
        flash('Kon vacature niet opslaan. Probeer opnieuw.', 'danger')
        return redirect(url_for('vacature_nieuw'))

