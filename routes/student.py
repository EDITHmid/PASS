"""
PASS Student Self-View Routes
================================
Implements FR-15 from the PRD.

Provides students with:
  - Personal Δt time-series chart
  - Credibility Score gauge
  - Active perks and waivers
"""

import json
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app import db
from models import Student, Submission, Alert, PolicyEvent
from engine.metrics import MetricComputer
from engine.credibility import CredibilityScorer

student_bp = Blueprint("student", __name__, template_folder="../templates")

metric_computer = MetricComputer()
credibility_scorer = CredibilityScorer()


@student_bp.route("/view")
@login_required
def self_view():
    """
    Student Self-View panel (FR-15).
    Shows personal behavioral trends, credibility score, and active perks.
    """
    # Find the student profile for the logged-in user
    if current_user.role == "student":
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student:
            # Try to find by name match as fallback
            student = Student.query.filter_by(
                name=current_user.full_name
            ).first()
    else:
        # Instructors/admins can view any student
        abort(403)

    if not student:
        return render_template("student/no_profile.html")

    # Retrieve submissions
    submissions = Submission.query.filter_by(student_id=student.id).order_by(
        Submission.submitted_at.asc()
    ).all()

    # Compute metrics
    delta_t_values = [s.delta_t for s in submissions]
    delta_t_hours = [round(s.delta_t_hours, 2) for s in submissions]
    assignment_labels = [s.assignment_id for s in submissions]

    summary = metric_computer.compute_student_summary(delta_t_values)
    variance_series = metric_computer.compute_rolling_variance_series(delta_t_values)

    # Credibility score with breakdown
    total_assignments = max(len(submissions), 1)
    cred_result = credibility_scorer.compute_credibility_score(
        delta_t_values=delta_t_values,
        variance_value=summary["current_variance"],
        submitted_count=len(submissions),
        total_assignments=total_assignments,
        attendance_pct=student.attendance_pct or 0.0,
        mid1=student.mid1_score,
        mid2=student.mid2_score,
        mid3=student.mid3_score,
    )

    # Active alerts for this student
    alerts = Alert.query.filter_by(
        student_id=student.id
    ).order_by(Alert.created_at.desc()).all()

    # Active perks/waivers
    active_perks = PolicyEvent.query.filter_by(
        student_id=student.id, is_active=True
    ).order_by(PolicyEvent.triggered_at.desc()).all()

    # Prepare JSON for charts
    submissions_json = json.dumps([
        {
            "assignment_id": s.assignment_id,
            "delta_t_hours": round(s.delta_t_hours, 2),
        }
        for s in submissions
    ])

    breakdown = {
        "delta_t_score": cred_result["components"]["delta_t_consistency"]["score"],
        "variance_score": cred_result["components"]["variance_stability"]["score"],
        "completion_score": cred_result["components"]["completion_rate"]["score"],
        "attendance_score": cred_result["components"]["attendance"]["score"],
        "exam_score": cred_result["components"]["exam_performance"]["score"],
    }

    # Determine trend
    trend_data = summary.get("trend", {})
    trend_direction = trend_data.get("direction", "stable") if isinstance(trend_data, dict) else "stable"
    metrics = {"trend": trend_direction}

    return render_template(
        "student/self_view.html",
        student=student,
        submissions=submissions,
        submissions_json=submissions_json,
        breakdown=breakdown,
        metrics=metrics,
        alerts=alerts,
        active_perks=active_perks,
    )
