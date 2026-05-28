"""
PASS REST API Routes
======================
Implements the API endpoints defined in PRD Section 8.3.

All responses follow a consistent JSON envelope:
{
    "success": bool,
    "data": {...},
    "message": str (optional)
}
"""

import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app import db
from models import Student, Submission, Alert, PolicyEvent, Course
from engine.ingestion import DataIngestor
from engine.metrics import MetricComputer
from engine.hysteresis import HysteresisFilter
from engine.credibility import CredibilityScorer

api_bp = Blueprint("api", __name__)

# Engine instances
metric_computer = MetricComputer()
hysteresis_filter = HysteresisFilter()
credibility_scorer = CredibilityScorer()


def api_response(data=None, message=None, success=True, status_code=200):
    """Standard API response envelope."""
    body = {"success": success}
    if data is not None:
        body["data"] = data
    if message:
        body["message"] = message
    return jsonify(body), status_code


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/ingest — Upload CSV or trigger LMS poll (PRD 8.3)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/ingest", methods=["POST"])
@login_required
def ingest_data():
    """
    Upload CSV data for ingestion.

    Accepts multipart/form-data with a 'file' field containing the CSV,
    or JSON with a 'csv_data' field containing raw CSV content.

    Returns:
        Ingestion summary with counts and error log.
    """
    ingestor = DataIngestor()

    if "file" in request.files:
        file = request.files["file"]
        if not file.filename.lower().endswith(".csv"):
            return api_response(message="Only CSV files are accepted.", success=False, status_code=400)
        content = file.read().decode("utf-8")
        filename = file.filename
    elif request.is_json and "csv_data" in request.json:
        content = request.json["csv_data"]
        filename = request.json.get("filename", "api_upload.csv")
    else:
        return api_response(
            message="No CSV file or data provided.", success=False, status_code=400
        )

    result = ingestor.ingest_csv(content, filename)

    if not result["success"]:
        return api_response(
            data={"errors": result["errors"]},
            message="Ingestion failed.",
            success=False,
            status_code=400,
        )

    # Save to database
    from routes.dashboard import _save_ingestion_records, _recompute_all_metrics

    saved = _save_ingestion_records(result["records"])
    _recompute_all_metrics()

    return api_response(
        data={
            "filename": filename,
            "total_records": result["total_records"],
            "valid_records": result["valid_records"],
            "invalid_records": result["invalid_records"],
            "saved_records": saved,
            "errors": result["errors"],
        },
        message=f"Successfully ingested {saved} records.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/alerts — Active hysteresis-confirmed alerts (PRD 8.3)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/alerts", methods=["GET"])
@login_required
def get_alerts():
    """
    Returns active hysteresis-confirmed alerts with full context.

    Query params:
        resolved: 'true'|'false' (filter by resolution status)
        severity: 'info'|'warning'|'critical' (filter by severity)
        limit: int (max results, default 50)
    """
    query = Alert.query

    resolved = request.args.get("resolved")
    if resolved is not None:
        query = query.filter_by(resolved=(resolved.lower() == "true"))

    severity = request.args.get("severity")
    if severity in ("info", "warning", "critical"):
        query = query.filter_by(severity=severity)

    limit = request.args.get("limit", 50, type=int)
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()

    return api_response(
        data={
            "alerts": [a.to_dict() for a in alerts],
            "total": len(alerts),
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/student/<id> — Student detail with metrics (PRD 8.3)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/student/<student_id>", methods=["GET"])
@login_required
def get_student(student_id):
    """
    Returns Δt history, variance data, and credibility score for one student.
    """
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return api_response(message="Student not found.", success=False, status_code=404)

    submissions = Submission.query.filter_by(student_id=student.id).order_by(
        Submission.submitted_at.asc()
    ).all()

    delta_t_values = [s.delta_t for s in submissions]
    summary = metric_computer.compute_student_summary(delta_t_values)
    variance_series = metric_computer.compute_rolling_variance_series(delta_t_values)

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

    alerts = Alert.query.filter_by(student_id=student.id).order_by(
        Alert.created_at.desc()
    ).all()

    policy_events = PolicyEvent.query.filter_by(student_id=student.id).all()

    return api_response(
        data={
            "student": student.to_dict(),
            "metrics": summary,
            "credibility": cred_result,
            "submissions": [s.to_dict() for s in submissions],
            "delta_t_series": [
                {"assignment": s.assignment_id, "delta_t_hours": round(s.delta_t_hours, 2)}
                for s in submissions
            ],
            "variance_series": [
                round(v, 2) if v is not None else None for v in variance_series
            ],
            "alerts": [a.to_dict() for a in alerts],
            "policy_events": [p.to_dict() for p in policy_events],
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/dashboard/summary — Class-wide aggregates (PRD 8.3)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/dashboard/summary", methods=["GET"])
@login_required
def get_dashboard_summary():
    """Returns class-wide aggregates for the instructor dashboard."""
    students = Student.query.filter_by(status="active").all()
    total = len(students)

    if total == 0:
        return api_response(
            data={
                "total_students": 0,
                "avg_credibility": 0,
                "distribution": {"excellent": 0, "good": 0, "warning": 0, "critical": 0},
                "total_active_alerts": 0,
                "total_submissions": 0,
            }
        )

    scores = [s.credibility_score for s in students]
    distribution = {
        "excellent": sum(1 for s in scores if s >= 85),
        "good": sum(1 for s in scores if 50 <= s < 85),
        "warning": sum(1 for s in scores if 30 <= s < 50),
        "critical": sum(1 for s in scores if s < 30),
    }

    # Class-wide Δt trend data
    all_submissions = Submission.query.order_by(Submission.submitted_at.asc()).all()

    # Aggregate by assignment
    assignment_averages = {}
    for sub in all_submissions:
        if sub.assignment_id not in assignment_averages:
            assignment_averages[sub.assignment_id] = []
        assignment_averages[sub.assignment_id].append(sub.delta_t_hours)

    class_trend = [
        {
            "assignment": aid,
            "avg_delta_t_hours": round(sum(vals) / len(vals), 2),
            "submission_count": len(vals),
        }
        for aid, vals in assignment_averages.items()
    ]

    return api_response(
        data={
            "total_students": total,
            "avg_credibility": round(sum(scores) / total, 2),
            "distribution": distribution,
            "total_active_alerts": Alert.query.filter_by(resolved=False).count(),
            "total_submissions": len(all_submissions),
            "class_trend": class_trend,
            "at_risk_students": [
                s.to_dict() for s in sorted(students, key=lambda x: x.credibility_score)[:10]
            ],
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/policy/trigger — Manual policy event (PRD 8.3)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/policy/trigger", methods=["POST"])
@login_required
def trigger_policy():
    """Manually trigger or override a policy event."""
    data = request.get_json()
    if not data:
        return api_response(message="JSON body required.", success=False, status_code=400)

    student_id = data.get("student_id")
    policy_type = data.get("policy_type")
    description = data.get("description", "Manually triggered policy event.")

    if not student_id or not policy_type:
        return api_response(
            message="student_id and policy_type are required.",
            success=False,
            status_code=400,
        )

    student = db.session.get(Student, student_id)
    if not student:
        return api_response(message="Student not found.", success=False, status_code=404)

    event = PolicyEvent(
        event_id=f"POL-{uuid.uuid4().hex[:8].upper()}",
        student_id=student.id,
        policy_type=policy_type,
        description=description,
        triggered_by="manual",
    )
    db.session.add(event)
    db.session.commit()

    return api_response(
        data=event.to_dict(),
        message=f"Policy event '{policy_type}' created for {student.name}.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/export/csv — Export current view data as CSV (PRD 8.3)
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/export/csv", methods=["GET"])
@login_required
def export_csv_api():
    """Export data as CSV via API."""
    from routes.dashboard import export_csv
    return export_csv()


# ─────────────────────────────────────────────────────────────────────────────
# Additional utility endpoints
# ─────────────────────────────────────────────────────────────────────────────

@api_bp.route("/students", methods=["GET"])
@login_required
def get_all_students():
    """Get all students with basic metrics."""
    students = Student.query.filter_by(status="active").order_by(
        Student.credibility_score.asc()
    ).all()
    return api_response(
        data={
            "students": [s.to_dict() for s in students],
            "total": len(students),
        }
    )


@api_bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint."""
    return api_response(
        data={
            "status": "healthy",
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
