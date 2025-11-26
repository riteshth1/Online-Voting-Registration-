from app import app

from authentication import auth_bp
from logout import logout_bp
from admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(logout_bp)
app.register_blueprint(admin_bp)

if __name__ == "__main__":
    app.run(debug=True)

