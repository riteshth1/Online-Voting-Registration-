from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.exceptions import abort
from flask import jsonify

# from models import db, User, Candidate

from app import db, User, Candidate

admin_bp = Blueprint('admin', __name__)


def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.query.get(user_id)


# Admin Dashboard
@admin_bp.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        flash('Please log in to access the dashboard.')
        return redirect(url_for('auth.login'))  # change 'auth.login' to your login endpoint
    candidates = Candidate.query.order_by(Candidate.id).all()
    return render_template('admin_dashboard.html', user=user, candidates=candidates)


@admin_bp.route('/vote/<int:cand_id>', methods=['POST'])
def vote(cand_id):
    user = get_current_user()
    if not user:
        flash('Please log in to vote.')
        return redirect(url_for('auth.login'))  # change to your login endpoint

    # Prevent double voting - assumes User model has boolean 'has_voted' field
    if getattr(user, 'has_voted', False):
        flash('You have already voted.')
        return redirect(url_for('admin.dashboard'))

    candidate = Candidate.query.get(cand_id)
    if not candidate:
        abort(404)

    # Increment candidate votes (assumes integer 'votes' column)
    candidate.votes = (candidate.votes or 0) + 1
    # Mark user as voted (adjust field name if different)
    setattr(user, 'has_voted', True)

    try:
        db.session.commit()
        flash('Your vote has been recorded. Thank you.')
    except Exception as e:
        db.session.rollback()
        # Log the exception in real app
        flash('An error occurred while recording your vote. Please try again.')

    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    # add any other session cleanup as needed
    flash('You have been logged out.')
    return redirect(url_for('auth.login'))  # change to your login endpoint


# Only admin can access these routes
def admin_required():
    if 'user_id' not in session or session.get('user_name') != 'admin':
        flash("Unauthorized access. Admin only!", "danger")
        return False
    return True


# Admin Dashboard
@app.route('/admin/dashboard')
def admin_dashboard():
    if not admin_required():
        return redirect(url_for('login'))

    candidates = Candidate.query.all()
    total_voters = User.query.count()
    voted_users = User.query.filter_by(has_voted=True).count()

    # Fetch vote counts for each candidate
    vote_data = (
        db.session.query(Candidate.name, db.func.count(Vote.id))
        .outerjoin(Vote)
        .group_by(Candidate.id)
        .all()
    )

    vote_labels = [v[0] for v in vote_data]
    vote_values = [v[1] for v in vote_data]

    return render_template(
        'admin_dashboard.html',
        candidates=candidates,
        total_voters=total_voters,
        voted_users=voted_users,
        vote_counts=vote_data,
        vote_labels=vote_labels,
        vote_values=vote_values,
    )


# Add candidate
@app.route('/admin/add_candidate', methods=['POST'])
def add_candidate():
    if not admin_required():
        return redirect(url_for('login'))

    name = request.form['name']
    party = request.form['party']
    position = request.form['position']

    new_cand = Candidate(name=name, party=party, position=position)
    db.session.add(new_cand)
    db.session.commit()

    flash('Candidate added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


# Delete candidate
@app.route('/admin/delete_candidate/<int:id>')
def delete_candidate(id):
    if not admin_required():
        return redirect(url_for('login'))

    candidate = Candidate.query.get(id)
    if candidate:
        db.session.delete(candidate)
        db.session.commit()
        flash('Candidate deleted successfully!', 'info')
    else:
        flash('Candidate not found.', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/live_votes')
def live_votes():
    vote_data = (
        db.session.query(Candidate.name, db.func.count(Vote.id))
        .outerjoin(Vote)
        .group_by(Candidate.id)
        .all()
    )

    labels = [v[0] for v in vote_data]
    values = [v[1] for v in vote_data]

    return jsonify({'labels': labels, 'values': values})