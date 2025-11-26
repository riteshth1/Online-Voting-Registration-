from flask import render_template, redirect, url_for, session, flash, request, current_app
from werkzeug.routing import BuildError
from sqlalchemy.exc import SQLAlchemyError
from app import app, db, User, Candidate, Vote

def _login_url():
    try:
        return url_for('auth.login')
    except BuildError:
        try:
            return url_for('login')
        except BuildError:
            return '/login'


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(_login_url())

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        flash("User not found. Please log in again.", "warning")
        return redirect(_login_url())

    candidates = Candidate.query.order_by(Candidate.id).all()

    if getattr(user, "has_voted", False):
        return render_template('voted.html', user=user)

    return render_template('dashboard.html', user=user, candidates=candidates)


@app.route('/vote/<int:candidate_id>', methods=['POST'])
def vote(candidate_id):
    if 'user_id' not in session:
        return redirect(_login_url())

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        flash("User session invalid. Please log in again.", "warning")
        return redirect(_login_url())

    candidate = Candidate.query.get(candidate_id)
    if not candidate:
        flash("Candidate not found.", "danger")
        return redirect(url_for('dashboard'))

    if getattr(user, "has_voted", False):
        flash("You have already voted.", "info")
        return redirect(url_for('dashboard'))

    # Record the vote safely and update candidate tally
    new_vote = Vote(voter_id=user.id, candidate_id=candidate.id)
    try:
        db.session.add(new_vote)
        # ensure votes is integer
        candidate.votes = (candidate.votes or 0) + 1
        user.has_voted = True
        db.session.commit()
        flash(f"Your vote for {candidate.name} has been recorded!", "success")
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to record vote")
        flash("An error occurred while recording your vote. Please try again.", "danger")

    return redirect(url_for('dashboard'))
