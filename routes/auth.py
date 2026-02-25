"""
PASS Authentication Routes
============================
Handles user registration, login, logout, and session management.
Protected by Flask-Login with role-based access control.
"""

from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from models import User, Student

auth_bp = Blueprint("auth", __name__, template_folder="../templates")


@auth_bp.route("/")
def index():
    """Landing page — redirect to appropriate dashboard if logged in."""
    if current_user.is_authenticated:
        if current_user.role == "student":
            return redirect(url_for("student.self_view"))
        return redirect(url_for("dashboard.instructor_dashboard"))
    return render_template("auth/landing.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """User login with role-based redirect."""
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=request.form.get("remember"))
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()

            flash(f"Welcome back, {user.full_name}!", "success")

            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)

            if user.role == "student":
                return redirect(url_for("student.self_view"))
            return redirect(url_for("dashboard.instructor_dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration with role selection."""
    if current_user.is_authenticated:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        full_name = request.form.get("full_name", "").strip()
        role = request.form.get("role", "student")
        student_id_input = request.form.get("student_id", "").strip()

        # Validation
        errors = []

        if not all([username, email, password, full_name]):
            errors.append("All fields are required.")

        if password != password_confirm:
            errors.append("Passwords do not match.")

        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")

        if User.query.filter_by(username=username).first():
            errors.append("Username already exists.")

        if User.query.filter_by(email=email).first():
            errors.append("Email already registered.")

        if role not in ("student", "instructor"):
            errors.append("Invalid role selected.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("auth/register.html")

        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # If student, also create student profile
        if role == "student":
            sid = student_id_input or f"STU-{username.upper()[:6]}-{user.id:03d}"
            student = Student(
                student_id=sid,
                name=full_name,
                user_id=user.id,
            )
            db.session.add(student)

        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
