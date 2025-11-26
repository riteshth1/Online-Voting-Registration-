import secrets
import time
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, current_app
from flask_mail import Message
from app import app, db, bcrypt, User, Candidate, mail

# OTP storage: voter_id -> {"otp": str, "expiry": timestamp}
otp_storage = {}
OTP_TTL_SECONDS = 300  # 5 minutes

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        voter_id = request.form.get('voter_id', '').strip()
        password = request.form.get('password', '').strip()

        if not (name and email and voter_id and password):
            flash("All fields are required.", 'warning')
            return redirect(url_for('register'))

        existing_user = User.query.filter((User.email == email) | (User.voter_id == voter_id)).first()
        if existing_user:
            flash("User already exists. Please login.", 'warning')
            return redirect(url_for('login'))

        # Prefer model helper if available
        new_user = User(name=name, email=email, voter_id=voter_id)
        if hasattr(new_user, "set_password"):
            new_user.set_password(password)
        else:
            hashed_pass = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user.password = hashed_pass

        db.session.add(new_user)
        db.session.commit()

        flash("Registered successfully!", 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/', methods=['GET'])
@app.route('/login', methods=['GET'])
def login():
    # login page shows form that posts to /get_otp or /verify_otp depending on your UI
    return render_template('login.html')


@app.route('/get_otp', methods=['POST'])
def get_otp():
    voter_id = request.form.get('voter_id', '').strip()
    if not voter_id:
        flash("Please provide your Voter ID.", "warning")
        return redirect(url_for('login'))

    user = User.query.filter_by(voter_id=voter_id).first()
    if not user:
        flash("Voter ID not found. Please register first.", "danger")
        return redirect(url_for('register'))

    # Generate 6-digit OTP
    otp = f"{secrets.randbelow(900000) + 100000}"
    expiry = time.time() + OTP_TTL_SECONDS
    otp_storage[voter_id] = {"otp": otp, "expiry": expiry}

    # Send email using Flask-Mail (uses app.config MAIL_* settings)
    sender = app.config.get("MAIL_USERNAME") or app.config.get("MAIL_DEFAULT_SENDER") or "noreply@example.com"
    msg = Message(
        subject="Your Voting System OTP",
        sender=sender,
        recipients=[user.email],
        body=f"Dear {user.name},\n\nYour OTP for login is: {otp}\nThis code is valid for {OTP_TTL_SECONDS//60} minutes.\n\nDo not share it with anyone."
    )

    try:
        mail.send(msg)
        flash("OTP has been sent to your registered email.", "success")
    except Exception:
        # Do not leak exception detail to users
        current_app.logger.exception("Failed sending OTP email")
        flash("Error sending OTP email. Contact administrator.", "danger")

    return redirect(url_for('login', otp_sent='true'))


@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    otp_entered = request.form.get('otp', '').strip()
    if not otp_entered:
        flash("Please enter the OTP.", "warning")
        return redirect(url_for('login'))

    # Clean expired otps and find match
    now = time.time()
    matched_voter_id = None
    expired_keys = []
    for v_id, data in list(otp_storage.items()):
        if data.get("expiry", 0) < now:
            expired_keys.append(v_id)
            continue
        if data.get("otp") == otp_entered:
            matched_voter_id = v_id
            break

    for k in expired_keys:
        otp_storage.pop(k, None)

    if not matched_voter_id:
        flash("Invalid or expired OTP. Please try again.", "danger")
        return redirect(url_for('login'))

    user = User.query.filter_by(voter_id=matched_voter_id).first()
    if not user:
        flash("User not found. Please register.", "danger")
        return redirect(url_for('register'))

    # Successful login
    session['user_id'] = user.id
    session['user_name'] = user.name
    otp_storage.pop(matched_voter_id, None)
    flash("Logged in successfully!", "success")
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        flash("User not found. Please log in again.", "warning")
        return redirect(url_for('login'))

    candidates = Candidate.query.order_by(Candidate.id).all()

    if getattr(user, "has_voted", False):
        flash("You have already voted. Thank you for participating!", "info")
        return render_template('voted.html', user=user)

    return render_template('dashboard.html', user=user, candidates=candidates)


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))
