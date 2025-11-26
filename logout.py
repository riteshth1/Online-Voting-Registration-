from flask import Blueprint, session, redirect, url_for, flash

logout_bp = Blueprint("logout", __name__)


@logout_bp.route("/logout")
def logout():
    """
    Clear the session and redirect to the login page.
    Register this blueprint in app.py with:
      from logout import logout_bp
      app.register_blueprint(logout_bp)
    """
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))