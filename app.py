# Standard library
from datetime import timedelta
import os

# Third-party
from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager

# Local
from models import db, User
from auth import auth_bp, init_oauth
from blueprints.main import main_bp
from blueprints.transactions import transactions_bp
from blueprints.plaid import plaid_bp

load_dotenv()

login_manager = LoginManager()


def create_app(config_override: dict | None = None) -> Flask:
    app = Flask(__name__)

    # Apply overrides first so tests can inject DB URL + SECRET_KEY before checks
    if config_override:
        app.config.update(config_override)

    # Resolve secrets from config (tests inject directly) or env
    secret_key = app.config.get('SECRET_KEY') or os.getenv("SECRET_KEY")
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI') or os.getenv("DATABASE_URL")

    if not app.config.get('TESTING'):
        if not secret_key:
            raise RuntimeError("SECRET_KEY is not set in the environment (.env)")
        if not db_url:
            raise RuntimeError("DATABASE_URL is not set in the environment (.env)")

    app.secret_key = secret_key or "test-secret"
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url or "sqlite:///:memory:"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Connection pool — skip for SQLite (used in tests)
    if not app.config.get('TESTING'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 20,
            'max_overflow': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'pool_timeout': 30,
        }

    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') != 'development'

    # Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.landing'
    login_manager.login_message = 'Please log in to access this page'

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    init_oauth(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(plaid_bp)

    with app.app_context():
        db.create_all()
        if not app.config.get('TESTING'):
            try:
                with db.engine.connect() as connection:
                    connection.execute(db.text("SELECT 1"))
                print("✅ Database connection: SUCCESS!")
            except Exception as e:
                print(f"❌ Database connection: FAILED - {e}")
                exit(1)

    return app


# ========================================
# START THE APP
# ========================================
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
