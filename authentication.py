# import random
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, flash, redirect, url_for, session, render_template
from flask_mail import Message
# from flask_sqlalchemy import SQLAlchemy

from app import app, db, mail, User, Candidate

auth_bp = Blueprint("auth", __name__)

OTP_TTL_SECONDS = 300

# app = Flask(__name__)
app.secret_key = 'logh ptjv yzyp iovf'

# Configuring database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voters.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'riteshbill14@gmail.com'
app.config['MAIL_PASSWORD'] = 'logh ptjv yzyp iovf'

# mail = Mail(app)
# db = SQLAlchemy(app)

@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        voter_id = request.form.get("voter_id", "").strip()
        if not voter_id:
            flash("Please provide your Voter ID.", "warning")
            return redirect(url_for("auth.login"))

        user = User.query.filter_by(voter_id=voter_id).first()
        if not user:
            flash("Voter ID not found. Please register first.", "danger")
            return redirect(url_for("auth.register"))

        # generate OTP and temporary session values (do not set persistent user_id until verified)
        otp = f"{secrets.randbelow(900000) + 100000}"  # 6-digit
        session["auth_otp"] = otp
        session["auth_otp_expiry"] = (datetime.utcnow() + timedelta(seconds=OTP_TTL_SECONDS)).timestamp()
        session["auth_user_id_tmp"] = user.id
        session["auth_user_name_tmp"] = user.name
        session["auth_user_email_tmp"] = user.email

        # prepare email sender/recipient using app config
        sender = app.config.get("MAIL_USERNAME") or app.config.get("MAIL_DEFAULT_SENDER") or "noreply@example.com"
        try:
            msg = Message(
                subject="Your OTP for Online Voting Login",
                sender=sender,
                recipients=[user.email],
            )
            msg.body = f"Hello {user.name},\n\nYour OTP for login is: {otp}\n\nThis code is valid for 5 minutes."
            mail.send(msg)
            flash("OTP sent to your email. Please check and verify.", "info")
        except Exception:

            flash("Unable to send OTP email. Contact administrator.", "danger")

        return redirect(url_for("auth.verify_otp"))

    return render_template("login.html")


@auth_bp.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()
        stored_otp = session.get("auth_otp")
        expiry_ts = session.get("auth_otp_expiry")

        if not stored_otp or not expiry_ts:
            flash("No OTP request found. Please request a new OTP.", "warning")
            return redirect(url_for("auth.login"))

        if datetime.utcnow().timestamp() > expiry_ts:
            session.pop("auth_otp", None)
            session.pop("auth_otp_expiry", None)
            session.pop("auth_user_id_tmp", None)
            session.pop("auth_user_name_tmp", None)
            session.pop("auth_user_email_tmp", None)
            flash("OTP expired. Please request a new one.", "warning")
            return redirect(url_for("auth.login"))

        if entered_otp == stored_otp:

            session.pop("auth_otp", None)
            session.pop("auth_otp_expiry", None)
            session["user_id"] = session.pop("auth_user_id_tmp", None)
            session["user_name"] = session.pop("auth_user_name_tmp", None)
            session["user_email"] = session.pop("auth_user_email_tmp", None)
            flash("Login successful!", "success")
            return redirect(url_for("auth.dashboard"))
        else:
            flash("Invalid OTP. Try again.", "danger")
            return redirect(url_for("auth.verify_otp"))

    return render_template("verify_otp.html")


@auth_bp.route("/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.get(user_id)
    if not user:
        session.clear()
        flash("User not found. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    candidates = Candidate.query.order_by(Candidate.id).all()
    return render_template("dashboard.html", user=user, candidates=candidates)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        voter_id = request.form.get("voter_id", "").strip()

        if not (name and email and voter_id):
            flash("All fields are required.", "warning")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(voter_id=voter_id).first():
            flash("Voter ID already registered.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("auth.register"))

        new_user = User(name=name, email=email, voter_id=voter_id)
        random_pw = secrets.token_urlsafe(16)
        if hasattr(new_user, "set_password"):
            new_user.set_password(random_pw)
        else:
            new_user.password = random_pw

        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! You can now log in using your Voter ID.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
