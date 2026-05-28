"""
PASS Admin & Principal Dashboard Routes
==========================================
Provides school-wide overview, user management, and configuration.
"""

import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user

from app import db
from models import User, Student, Course, Submission, Alert, PolicyEvent, AcademicYear
from engine.metrics import MetricComputer
from engine.credibility import CredibilityScorer

admin_bp = Blueprint("admin", __name__, template_folder="../templates")

metric_computer = MetricComputer()
credibility_scorer = CredibilityScorer()


def admin_required(f):
    """Decorator to restrict access to principal/admin."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role not in ("principal", "admin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/dashboard")
@login_required
@admin_required
def principal_dashboard():
    """School-wide overview for principal."""
    total_students = Student.query.filter_by(status="active").count()
    total_courses = Course.query.count()
    total_teachers = User.query.filter(
        User.role.in_(["teacher", "instructor"])
    ).count()
    total_alerts = Alert.query.filter_by(resolved=False).count()

    all_students = Student.query.filter_by(status="active").all()
    scores = [s.credibility_score for s in all_students if s.credibility_score]

    avg_credibility = round(sum(scores) / len(scores), 2) if scores else 0

    distribution = {
        "high": sum(1 for s in scores if s >= 85),
        "medium": sum(1 for s in scores if 50 <= s < 85),
        "low": sum(1 for s in scores if 30 <= s < 50),
        "critical": sum(1 for s in scores if s < 30),
    }

    students = Student.query.filter_by(status="active").order_by(
        Student.credibility_score.asc()
    ).limit(10).all()

    return render_template(
        "admin/principal_dashboard.html",
        total_students=total_students,
        total_courses=total_courses,
        total_teachers=total_teachers,
        total_alerts=total_alerts,
        avg_credibility=avg_credibility,
        distribution=json.dumps(distribution),
        at_risk_students=students,
    )


@admin_bp.route("/users")
@login_required
@admin_required
def manage_users():
    """Manage all users (principal/admin only)."""
    users = User.query.order_by(User.role, User.username).all()
    return render_template("admin/manage_users.html", users=users)


@admin_bp.route("/users/toggle/<int:user_id>")
@login_required
@admin_required
def toggle_user(user_id):
    """Enable or disable a user account."""
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"User '{user.username}' {'activated' if user.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/weights", methods=["GET", "POST"])
@login_required
@admin_required
def configure_weights():
    """Configure credibility scoring weights per school."""
    if request.method == "POST":
        try:
            weights = {
                "WEIGHT_DELTA_T_CONSISTENCY": float(request.form.get("weight_delta_t", 0.25)),
                "WEIGHT_VARIANCE_STABILITY": float(request.form.get("weight_variance", 0.10)),
                "WEIGHT_COMPLETION_RATE": float(request.form.get("weight_completion", 0.10)),
                "WEIGHT_ATTENDANCE": float(request.form.get("weight_attendance", 0.25)),
                "WEIGHT_EXAM_PERFORMANCE": float(request.form.get("weight_exam", 0.30)),
            }
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                flash(f"Weights must sum to 1.0 (currently {total:.2f}).", "danger")
                return redirect(url_for("admin.configure_weights"))

            from flask import current_app
            for key, val in weights.items():
                current_app.config[key] = val

            flash("Scoring weights updated successfully!", "success")
        except (ValueError, TypeError):
            flash("Invalid weight values provided.", "danger")
        return redirect(url_for("admin.configure_weights"))

    from flask import current_app
    current_weights = {
        "delta_t": current_app.config.get("WEIGHT_DELTA_T_CONSISTENCY", 0.25),
        "variance": current_app.config.get("WEIGHT_VARIANCE_STABILITY", 0.10),
        "completion": current_app.config.get("WEIGHT_COMPLETION_RATE", 0.10),
        "attendance": current_app.config.get("WEIGHT_ATTENDANCE", 0.25),
        "exam": current_app.config.get("WEIGHT_EXAM_PERFORMANCE", 0.30),
    }
    return render_template("admin/weight_config.html", weights=current_weights)
