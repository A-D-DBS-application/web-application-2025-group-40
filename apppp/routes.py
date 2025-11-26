from flask import Flask, render_template, session, redirect, url_for
from models import (
    db,
    Match,
    AppUser,
    JobListing,
    Employer,
    RecruiterUser,
    Student,
)
from datetime import datetime, timedelta
from sqlalchemy import func
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)


@app.route('/choose_role')
def choose_role():
    return render_template('choose_role.html')


@app.route('/login')
def login():
    # let op: nu alleen GET, iemand anders uit je groep
    # moet hier nog POST + session['user_id'] zetten
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/match_page')
def match_page():
    return render_template('match_page.html')


# --------- DASHBOARD BEDRIJF / RECRUITER ---------
@app.route('/bedrijf/dashboard')
def company_dashboard():
    # 1. check of iemand is ingelogd
    if 'user_id' not in session:
        # als nog geen login-systeem met session is,
        # kom je hier altijd terecht
        return redirect(url_for('login'))

    user = AppUser.query.get(session['user_id'])

    # 2. alleen recruiters mogen dit zien
    if not user or user.role != 'recruiter':
        return "Geen toegang tot bedrijfsdashboard", 403

    # 3. recruiter koppelen aan employer via RecruiterUser
    recruiter_link = RecruiterUser.query.filter_by(user_id=user.id).first()
    if recruiter_link is None:
        return "Geen bedrijf gekoppeld aan deze recruiter", 404

    employer = Employer.query.get(recruiter_link.employer_id)

    # 4. alle vacatures van dit bedrijf
    jobs = JobListing.query.filter_by(employer_id=employer.id).all()
    active_job_count = len(jobs)

    # 5. totaal aantal matches op alle vacatures van dit bedrijf
    total_matches = (
        db.session.query(func.count(Match.id))
        .join(JobListing, Match.job_id == JobListing.id)
        .filter(JobListing.employer_id == employer.id)
        .scalar()
    ) or 0

    # 6. matches in de laatste 7 dagen
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    matches_last_7_days = (
        db.session.query(func.count(Match.id))
        .join(JobListing, Match.job_id == JobListing.id)
        .filter(
            JobListing.employer_id == employer.id,
            Match.matched_at >= seven_days_ago,
        )
        .scalar()
    ) or 0

    # 7. gemiddelde matches per vacature
    avg_matches_per_job = (
        round(total_matches / active_job_count, 1)
        if active_job_count > 0
        else 0
    )

    # 8. per vacature het aantal matches
    job_data = []
    for job in jobs:
        match_count = Match.query.filter_by(job_id=job.id).count()
        job_data.append(
            {
                "id": job.id,
                "title": job.title,
                "location": job.location,
                # periode is een DATERANGE, we tonen gewoon de string
                "periode": str(job.periode) if job.periode is not None else "",
                "match_count": match_count,
            }
        )

    # 9. recente matches + student info
    recent_rows = (
        db.session.query(Match, JobListing, Student)
        .join(JobListing, Match.job_id == JobListing.id)
        .join(Student, Match.user_id == Student.user_id)
        .filter(JobListing.employer_id == employer.id)
        .order_by(Match.matched_at.desc())
        .limit(10)
        .all()
    )

    recent_matches = []
    for m, job, student in recent_rows:
        recent_matches.append(
            {
                "student_name": f"{student.first_name} {student.last_name}",
                "job_title": job.title,
                "matched_at": m.matched_at.strftime("%d/%m/%Y %H:%M")
                if m.matched_at
                else "",
                "notification_sent": m.notification_sent,
            }
        )

    # 10. team (alle recruiters bij dit bedrijf)
    team_rows = (
        db.session.query(RecruiterUser, AppUser)
        .join(AppUser, RecruiterUser.user_id == AppUser.id)
        .filter(RecruiterUser.employer_id == employer.id)
        .all()
    )

    team = []
    for r, u in team_rows:
        team.append(
            {
                "name": u.email,  # geen username in model, dus email tonen
                "email": u.email,
                "is_admin": r.is_admin,
            }
        )

    # 11. statistieken bundelen
    stats = {
        "active_job_count": active_job_count,
        "total_matches": total_matches,
        "matches_last_7_days": matches_last_7_days,
        "avg_matches_per_job": avg_matches_per_job,
    }

    # 12. recruiter-dashboard template renderen
    return render_template(
        'recruiter_dashboard.html',
        employer=employer,
        stats=stats,
        jobs=job_data,
        recent_matches=recent_matches,
        team=team,
    )


if __name__ == "__main__":
    app.run(debug=True)


if __name__ == "__main__":
    app.run(debug=True)


