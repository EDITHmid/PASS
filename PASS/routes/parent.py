"""
PASS Parent/Guardian Dashboard Routes
=======================================
Provides parents with a view of their child's academic progress,
credibility score, submission patterns, and active alerts.
"""

import json
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from app import db
from models import Guardian, Student, Submission, Alert, PolicyEvent
from engine.metrics import MetricComputer
from engine.credibility import CredibilityScorer

parent_bp = Blueprint("parent", __name__, template_folder="../templates")

metric_computer = MetricComputer()
credibility_scorer = CredibilityScorer()


@parent_bp.route("/dashboard")
@login_required
def dashboard():
    """Parent dashboard showing all linked children."""
    if current_user.role != "parent":
        abort(403)

    guardian = Guardian.query.filter_by(user_id=current_user.id).first()
    if not guardian:
        return render_template("parent/no_children.html")

    children_data = []
    for link in guardian.students:
        student = link.student
        if not student:
            continue

        submissions = Submission.query.filter_by(student_id=student.id).order_by(
            Submission.submitted_at.asc()
        ).all()

        delta_t_values = [s.delta_t for s in submissions]
        summary = metric_computer.compute_student_summary(delta_t_values)

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

        active_alerts = Alert.query.filter_by(
            student_id=student.id, resolved=False
        ).count()

        children_data.append({
            "student": student,
            "credibility": cred_result,
            "summary": summary,
            "active_alerts": active_alerts,
            "submissions_json": json.dumps([
                {"assignment_id": s.assignment_id, "delta_t_hours": round(s.delta_t_hours, 2)}
                for s in submissions[-10:]
            ]),
        })

    return render_template(
        "parent/dashboard.html",
        guardian=guardian,
        children=children_data,
    )
