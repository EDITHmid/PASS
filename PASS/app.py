"""
PASS Application Factory
==========================
Creates and configures the Flask application instance with all extensions,
blueprints, and middleware.
"""

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS

try:
    from flask_mail import Mail
    _mail_available = True
except ImportError:
    Mail = None
    _mail_available = False

from config import config_by_name

# Initialize extensions (created here, bound to app in create_app)
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail() if Mail is not None else None


def create_app(config_name=None):
    """
    Application factory pattern.

    Args:
        config_name: Configuration profile ('development', 'testing', 'production')

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_by_name[config_name])

    # Ensure required directories exist
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    if mail is not None:
        mail.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.api import api_bp
    from routes.parent import parent_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(parent_bp, url_prefix="/parent")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Exempt API routes from CSRF for REST clients
    csrf.exempt(api_bp)

    # Create database tables
    with app.app_context():
        from models import User, Student, Submission, Alert, PolicyEvent, Course, Guardian, StudentGuardian, AcademicYear, PasswordResetToken, ConfigSetting
        db.create_all()
        _load_persisted_weights(app)

    # Register error handlers
    register_error_handlers(app)

    # Register template context processors
    register_context_processors(app)

    return app


def register_error_handlers(app):
    """Register custom error pages."""

    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        from flask import render_template
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(error):
        from flask import render_template
        return render_template("errors/403.html"), 403


def _load_persisted_weights(app):
    """Load scoring weights from DB into app.config so they survive restarts."""
    try:
        from models import ConfigSetting
        db_weights = ConfigSetting.get_weights()
        for db_key, val in db_weights.items():
            config_key = f"WEIGHT_{db_key.upper()}"
            app.config[config_key] = val
    except Exception:
        pass  # table might not exist yet on first run


def register_context_processors(app):
    """Register Jinja2 context processors for templates."""

    @app.context_processor
    def inject_app_info():
        return {
            "app_name": "PASS",
            "app_version": "1.0",
            "app_full_name": "Proactive Academic Support System",
        }
