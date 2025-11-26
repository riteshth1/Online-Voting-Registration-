from app import app
from authentication import auth_bp
from voting_routes import voting_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(voting_bp)

if __name__ == "__main__":
    app.run(debug=True)