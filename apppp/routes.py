# apppp/routes.py
import re
from datetime import datetime, timedelta

from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_user, login_required, logout_user, current_user

from apppp.extensions import db
from apppp.models import AppUser, Student, RecruiterUser, Employer, JobListing, Match, Dislike


def register_routes(app, supabase=None):

    # -----------------------
    # Helpers
    # -----------------------
    def get_current_recruiter():
        if not (current_user.is_authenticated and getattr(current_user, "role", None) == "recruiter"):
            return None
        return RecruiterUser.query.filter_by(user_id=current_user.id).first()

    def get_employer_for_current_user():
        rec = get_current_recruiter()
        return rec.employer if rec and rec.employer else None

    def recruiter_owns_job(job):
        rec = get_current_recruiter()
        return bool(rec and rec.employer and job and rec.employer.id == job.employer_id)

    def populate_jobs_display_fields(jobs):
        for job in jobs:
            job.company_name = job.employer.name if job.employer else "Onbekend"
            job.match_count = len(job.matches or [])

    def tokenize(text: str, stopwords: set[str]) -> list[str]:
        """Split text into words, lowercased, stopwords removed."""
        if not text:
            return []
        words = re.findall(r"\w+", text.lower())
        return [w for w in words if w and w not in stopwords]

    # -----------------------
    # ROUTES
    # -----------------------
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/terms")
    def terms():
        return render_template("terms.html")

    @app.route("/login_bedrijf", methods=["GET", "POST"])
    def login_bedrijf():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            user = AppUser.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                flash("Foute email of wachtwoord!", "danger")
                return redirect(url_for("login_bedrijf"))

            if user.role != "recruiter":
                flash("Dit account is geen bedrijf/recruiter account.", "danger")
                return redirect(url_for("login_bedrijf"))

            login_user(user)
            flash("Inloggen gelukt.", "success")
            return redirect(url_for("recruiter_dashboard_view"))

        return render_template("login_bedrijf.html")

    @app.route("/login_student", methods=["GET", "POST"])
    def login_student():
        if request.method == "POST":
            agree = request.form.get("agree_terms")
            if agree != "on":
                flash("Je moet de algemene voorwaarden accepteren.", "danger")
                return redirect(url_for("login_student"))

            email = request.form.get("email")
            password = request.form.get("password")

            user = AppUser.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                flash("Foute email of wachtwoord!", "danger")
                return redirect(url_for("login_student"))

            if user.role != "student":
                flash("Dit account is geen student account.", "danger")
                return redirect(url_for("login_student"))

            login_user(user)
            return redirect(url_for("vacatures_student"))

        return render_template("login_student.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Uitgelogd.", "info")
        return redirect(url_for("index"))

    @app.route("/registratie_student", methods=["GET", "POST"])
    def registratie_student():
        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            # matcht met jouw template input names:
            first_name = request.form.get("firstName", "")
            last_name = request.form.get("lastName", "")

            if AppUser.query.filter_by(email=email).first():
                flash("Email is al in gebruik.", "danger")
                return redirect(url_for("registratie_student"))

            user = AppUser(email=email, role="student")
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            student = Student(user_id=user.id, first_name=first_name, last_name=last_name)
            db.session.add(student)
            db.session.commit()

            flash("Account aangemaakt. Log in met je gegevens.", "success")
            return redirect(url_for("login_student"))

        return render_template("registratie_student.html")

    @app.route("/registratie_bedrijf", methods=["GET", "POST"])
    def registratie_bedrijf():
        if request.method == "POST":
            company_name = request.form.get("companyName")
            email = request.form.get("email")
            password = request.form.get("password")

            if AppUser.query.filter_by(email=email).first():
                flash("Email is al in gebruik.", "danger")
                return redirect(url_for("registratie_bedrijf"))

            employer = Employer(name=company_name, contact_email=email)
            db.session.add(employer)
            db.session.flush()

            user = AppUser(email=email, role="recruiter")
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            rec = RecruiterUser(employer_id=employer.id, user_id=user.id, is_admin=True)
            db.session.add(rec)
            db.session.commit()

            flash("Account aangemaakt. Log in met je gegevens.", "success")
            return redirect(url_for("login_bedrijf"))

        return render_template("registratie_bedrijf.html")

    @app.route("/recruiter_dashboard")
    @login_required
    def recruiter_dashboard_view():
        if getattr(current_user, "role", None) != "recruiter":
            abort(403)

        employer = get_employer_for_current_user()
        if not employer:
            employer = Employer.query.filter_by(name="ACME BV").first()

        jobs = []
        if employer:
            jobs = JobListing.query.filter_by(employer_id=employer.id, is_active=True).all()

        populate_jobs_display_fields(jobs)
        jobs = sorted(jobs, key=lambda j: getattr(j, "match_count", 0), reverse=True)

        active_job_count = len(jobs)
        total_matches = 0
        matches_last_7_days = 0
        cutoff = datetime.utcnow() - timedelta(days=7)

        for job in jobs:
            jm = job.matches or []
            total_matches += len(jm)
            for m in jm:
                if m.matched_at and m.matched_at >= cutoff:
                    matches_last_7_days += 1

        stats = {
            "active_job_count": active_job_count,
            "total_matches": total_matches,
            "matches_last_7_days": matches_last_7_days,
        }

        return render_template("recruiter_dashboard.html", stats=stats, jobs=jobs)

    @app.route("/recruiter_profiel", methods=["GET", "POST"])
    @login_required
    def recruiter_profiel():
        if getattr(current_user, "role", None) != "recruiter":
            abort(403)

        user = current_user
        rec = RecruiterUser.query.filter_by(user_id=user.id).first()
        employer = rec.employer if rec else None

        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")

            company_name = request.form.get("company_name")
            contact_person = request.form.get("contact_person")
            contact_email = request.form.get("contact_email")
            btw_number = request.form.get("btw_number")
            description = request.form.get("description")

            if email and email != user.email:
                if AppUser.query.filter_by(email=email).first():
                    flash("Email is al in gebruik.", "danger")
                    return redirect(url_for("recruiter_profiel"))
                user.email = email

            if password:
                user.set_password(password)

            if not employer:
                employer = Employer(
                    name=company_name or "Onbekend",
                    contact_person=contact_person,
                    contact_email=contact_email,
                    btw_number=btw_number,
                    description=description,
                )
                db.session.add(employer)
                db.session.flush()

                rec.employer_id = employer.id
                db.session.add(rec)
            else:
                if company_name:
                    employer.name = company_name
                employer.contact_person = contact_person
                employer.contact_email = contact_email
                employer.btw_number = btw_number
                employer.description = description
                db.session.add(employer)

            db.session.add(user)
            db.session.commit()
            flash("Profiel bijgewerkt.", "success")
            return redirect(url_for("recruiter_dashboard_view"))

        return render_template("recruiter_profiel.html", user=user, employer=employer)

    @app.route("/vacature/nieuw")
    @login_required
    def vacature_nieuw():
        if getattr(current_user, "role", None) != "recruiter":
            abort(403)

        employer = get_employer_for_current_user()
        return render_template("vacatures_bedrijf.html", employer=employer)

    @app.route("/vacature/opslaan", methods=["POST"])
    @login_required
    def vacature_opslaan():
        if getattr(current_user, "role", None) != "recruiter":
            abort(403)

        job_title = request.form.get("jobTitle")
        location = request.form.get("location")
        description = request.form.get("description")
        client = request.form.get("client")

        employer = get_employer_for_current_user()
        if not employer:
            flash("Geen werkgever gekoppeld aan dit account.", "danger")
            return redirect(url_for("recruiter_dashboard_view"))

        job = JobListing(
            employer_id=employer.id,
            client=client,
            title=job_title,
            description=description,
            location=location,
            is_active=True,
        )
        db.session.add(job)
        db.session.commit()

        flash("Vacature succesvol geplaatst ✅", "success")
        return redirect(url_for("recruiter_dashboard_view"))

    # =========================================================
    # ✅ STUDENT VACATURES MET MATCH-ALGORITME (fit_pct)
    # =========================================================
    @app.route("/vacatures_student")
    @login_required
    def vacatures_student():
        if getattr(current_user, "role", None) != "student":
            flash("Alleen studenten kunnen deze pagina bekijken.", "danger")
            return redirect(url_for("index"))

        # stopwords laden (als je utils/stopwords.py hebt)
        stopwords = set()
        try:
            from utils.stopwords import load_stopwords_from_db  # project-level utils/
            stopwords = set(load_stopwords_from_db() or [])
        except Exception:
            stopwords = set()

        # alle actieve jobs
        jobs = JobListing.query.filter_by(is_active=True).all()

        # likes/dislikes van student
        liked_matches = Match.query.filter_by(user_id=current_user.id).all()
        liked_job_ids = [m.job_id for m in liked_matches]
        disliked_job_ids = [d.job_id for d in Dislike.query.filter_by(user_id=current_user.id).all()]

        # woorden uit liked jobs verzamelen
        liked_words = []
        for m in liked_matches:
            job = JobListing.query.get(m.job_id)
            if job:
                fields = f"{job.title or ''} {job.description or ''} {job.location or ''}"
                liked_words.extend(tokenize(fields, stopwords))

        liked_word_set = set(liked_words)

        def job_fit_score_and_pct(job: JobListing):
            fields = f"{job.title or ''} {job.description or ''} {job.location or ''}"
            job_words = tokenize(fields, stopwords)
            job_word_set = set(job_words)

            overlap = len(job_word_set & liked_word_set)
            total = len(job_word_set)
            pct = int((overlap / total) * 100) if total > 0 else 0
            return overlap, pct

        jobs_to_show = []
        for job in jobs:
            if job.id in liked_job_ids or job.id in disliked_job_ids:
                continue

            job.company_name = job.employer.name if job.employer else "Onbekend"
            overlap, pct = job_fit_score_and_pct(job)

            jobs_to_show.append(
                {
                    "job": job,
                    "liked": False,
                    "fit_pct": pct,
                    "overlap": overlap,
                }
            )

        # sorteer: hoogste match eerst
        jobs_sorted = sorted(jobs_to_show, key=lambda x: (x["fit_pct"], x["overlap"]), reverse=True)

        return render_template("vacatures_list.html", jobs=jobs_sorted)

    @app.route("/jobs/<int:job_id>/like", methods=["POST"])
    @login_required
    def like_job(job_id):
        if getattr(current_user, "role", None) != "student":
            abort(403)

        existing = Match.query.filter_by(user_id=current_user.id, job_id=job_id).first()
        if not existing:
            db.session.add(Match(user_id=current_user.id, job_id=job_id))
            db.session.commit()

        return redirect(url_for("vacatures_student"))

    @app.route("/jobs/<int:job_id>/dislike", methods=["POST"])
    @login_required
    def dislike_job(job_id):
        if getattr(current_user, "role", None) != "student":
            abort(403)

        existing = Dislike.query.filter_by(user_id=current_user.id, job_id=job_id).first()
        if not existing:
            db.session.add(Dislike(user_id=current_user.id, job_id=job_id))
            db.session.commit()

        return redirect(url_for("vacatures_student"))

    @app.route("/student_dashboard", methods=["GET", "POST"])
    @login_required
    def student_dashboard():
        if getattr(current_user, "role", None) != "student":
            abort(403)

        user = current_user
        student = Student.query.filter_by(user_id=user.id).first()

        if request.method == "POST":
            first_name = (request.form.get("firstName") or "").strip()
            last_name = (request.form.get("lastName") or "").strip()
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "")

            if not first_name or not last_name or not email:
                flash("Vul voornaam, achternaam en e-mail in.", "danger")
                return redirect(url_for("student_dashboard"))

            if email != user.email:
                existing = AppUser.query.filter_by(email=email).first()
                if existing:
                    flash("Dit e-mailadres is al in gebruik.", "danger")
                    return redirect(url_for("student_dashboard"))
                user.email = email

            if not student:
                student = Student(user_id=user.id, first_name=first_name, last_name=last_name)
                db.session.add(student)
            else:
                student.first_name = first_name
                student.last_name = last_name

            if password.strip():
                user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash("Profiel opgeslagen ✅", "success")
            return redirect(url_for("student_dashboard"))

        return render_template("student_dashboard.html", student=student, user=user)

    @app.route("/match_page")
    @login_required
    def match_page():
        if getattr(current_user, "role", None) == "recruiter":
            rec = get_current_recruiter()
            matches = []
            if rec and rec.employer:
                for job in rec.employer.job_listings:
                    for m in job.matches:
                        matches.append(m)
            return render_template("match_page.html", matches=matches)

        formatted = []
        for m in current_user.matches:
            formatted.append({"match": m, "job": m.job, "user": current_user})
        return render_template("match_page.html", matches=formatted)
