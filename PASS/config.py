"""
PASS Application Configuration
================================
Centralized configuration for Flask application, database, and security settings.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class."""

    # Flask Core
    SECRET_KEY = os.environ.get("SECRET_KEY", "pass-secret-key-change-in-production")
    DEBUG = False
    TESTING = False

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'pass.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # File Upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload

    # Email Configuration (optional — for password reset & notifications)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", None)
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", None)
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", None)
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "noreply@pass.edu")

    # PASS-Specific Configuration
    HYSTERESIS_WINDOW_SIZE = 3  # Consecutive assignments for trend confirmation
    HYSTERESIS_REVERSAL_COUNT = 2  # Consecutive improvements to resolve alert
    VARIANCE_ROLLING_WINDOW = 5  # Rolling window for variance stability
    CREDIBILITY_THRESHOLD_HIGH = 85  # Score for automated perks
    CREDIBILITY_THRESHOLD_WARNING = 50  # Score for warning state
    CREDIBILITY_THRESHOLD_CRITICAL = 30  # Score for critical alerts
    EXAM_ELIGIBILITY_THRESHOLD = 50  # Minimum credibility to sit for final exams

    # Credibility Score Weights (must sum to 1.0)
    WEIGHT_DELTA_T_CONSISTENCY = 0.25
    WEIGHT_VARIANCE_STABILITY = 0.10
    WEIGHT_COMPLETION_RATE = 0.10
    WEIGHT_ATTENDANCE = 0.25
    WEIGHT_EXAM_PERFORMANCE = 0.30

    # Institution Info (customize per school)
    SCHOOL_NAME = os.environ.get("SCHOOL_NAME", "My School")
    SCHOOL_ADDRESS = os.environ.get("SCHOOL_ADDRESS", "")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SERVER_NAME = "localhost"


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    SESSION_COOKIE_SECURE = False  # Set True if using HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PREFERRED_URL_SCHEME = "https"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
