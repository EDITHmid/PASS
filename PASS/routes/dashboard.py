"""
PASS Instructor Dashboard Routes
===================================
Implements FR-14 through FR-17 from the PRD.

Provides the instructor-facing dashboard with:
  - Active alerts feed
  - Top at-risk students list
  - Class-wide Δt trend charts
  - Student drill-down views
  - CSV data export
"""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, Response, abort,
)
from flask_login import login_required, current_user
from flask import current_app

from app import db, csrf
from models import Student, Submission, Alert, PolicyEvent, Course, IngestionLog
from engine.ingestion import DataIngestor
from engine.metrics import MetricComputer
from engine.hysteresis import HysteresisFilter
from engine.credibility import CredibilityScorer
from engine.ai_query import AIQueryEngine

dashboard_bp = Blueprint("dashboard", __name__, template_folder="../templates")

# Initialize engine components
metric_computer = MetricComputer()
hysteresis_filter = HysteresisFilter()
credibility_scorer = CredibilityScorer()


def instructor_required(f):
    """Decorator to restrict access to instructors and admins."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role not in ("instructor", "admin", "principal"):
            abort(403)
        return f(*args, **kwargs)

    return decorated


@dashboard_bp.route("/dashboard")
@login_required
@instructor_required
def instructor_dashboard():
    """
    Main instructor dashboard (FR-14).
    Displays: active alerts, at-risk students, class-wide trends.
    """
    # Get active alerts
    active_alerts = Alert.query.filter_by(resolved=False).order_by(
        Alert.created_at.desc()
    ).limit(20).all()

    # Get at-risk students (credibility < 50, sorted by lowest first)
    at_risk_students = Student.query.filter(
        Student.status == "active",
        Student.credibility_score < 50
    ).order_by(
        Student.credibility_score.asc()
    ).all()

    # Get all students for overview
    all_students = Student.query.filter_by(status="active").all()

    # Compute class-wide stats
    total_students = len(all_students)
    if total_students > 0:
        avg_credibility = sum(s.credibility_score for s in all_students) / total_students
        students_above_85 = sum(1 for s in all_students if s.credibility_score >= 85)
        students_below_30 = sum(1 for s in all_students if s.credibility_score < 30)
    else:
        avg_credibility = 0
        students_above_85 = 0
        students_below_30 = 0

    total_alerts = Alert.query.filter_by(resolved=False).count()
    total_submissions = Submission.query.count()

    # Credibility distribution for doughnut chart
    cred_distribution = {
        "high": sum(1 for s in all_students if s.credibility_score >= 85),
        "medium": sum(1 for s in all_students if 50 <= s.credibility_score < 85),
        "low": sum(1 for s in all_students if 30 <= s.credibility_score < 50),
        "critical": sum(1 for s in all_students if s.credibility_score < 30),
    }

    # Submissions JSON for Δt trend chart
    recent_submissions = Submission.query.order_by(
        Submission.submitted_at.asc()
    ).all()
    submissions_json = json.dumps([
        {
            "assignment_id": s.assignment_id,
            "delta_t_hours": round(s.delta_t_hours, 2),
            "student_id": s.student.student_id if s.student else "unknown",
        }
        for s in recent_submissions
    ])

    # Stats dict for template
    stats = {
        "total_students": total_students,
        "active_alerts": total_alerts,
        "at_risk_count": sum(1 for s in all_students if (s.credibility_score or 0) < 50),
        "avg_credibility": avg_credibility,
    }

    return render_template(
        "dashboard/instructor.html",
        stats=stats,
        alerts=active_alerts,
        at_risk=at_risk_students,
        all_students=all_students,
        submissions_json=submissions_json,
        cred_distribution=json.dumps(cred_distribution),
    )


@dashboard_bp.route("/dashboard/student/<student_id>")
@login_required
@instructor_required
def student_detail(student_id):
    """
    Student drill-down view for instructors.
    Shows Δt time-series, variance trends, credibility breakdown.
    """
    student = Student.query.filter_by(student_id=student_id).first_or_404()

    submissions = Submission.query.filter_by(student_id=student.id).order_by(
        Submission.submitted_at.asc()
    ).all()

    alerts = Alert.query.filter_by(student_id=student.id).order_by(
        Alert.created_at.desc()
    ).all()

    policy_events = PolicyEvent.query.filter_by(student_id=student.id).order_by(
        PolicyEvent.triggered_at.desc()
    ).all()

    # Compute detailed metrics
    delta_t_values = [s.delta_t for s in submissions]
    delta_t_hours = [s.delta_t_hours for s in submissions]
    assignment_labels = [s.assignment_id for s in submissions]

    summary = metric_computer.compute_student_summary(delta_t_values)
    variance_series = metric_computer.compute_rolling_variance_series(delta_t_values)

    # Credibility breakdown
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

    return render_template(
        "dashboard/student_detail.html",
        student=student,
        submissions=submissions,
        submissions_json=submissions_json,
        alerts=alerts,
        policy_events=policy_events,
        breakdown=breakdown,
    )


@dashboard_bp.route("/dashboard/upload", methods=["GET", "POST"])
@login_required
@instructor_required
def upload_csv():
    """CSV upload page for data ingestion (FR-01)."""
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected.", "danger")
            return redirect(url_for("dashboard.upload_csv"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(url_for("dashboard.upload_csv"))

        if not file.filename.lower().endswith(".csv"):
            flash("Only CSV files are accepted.", "danger")
            return redirect(url_for("dashboard.upload_csv"))

        try:
            content = file.read().decode("utf-8")
        except UnicodeDecodeError:
            content = file.read().decode("latin-1")

        # Ingest data
        ingestor = DataIngestor()
        result = ingestor.ingest_csv(content, file.filename)

        if not result["success"]:
            for error in result["errors"]:
                flash(error, "danger")
            return redirect(url_for("dashboard.upload_csv"))

        # Save records to database
        saved = _save_ingestion_records(result["records"])

        # Log ingestion
        log = IngestionLog(
            filename=file.filename,
            source="csv",
            total_records=result["total_records"],
            valid_records=result["valid_records"],
            invalid_records=result["invalid_records"],
            errors="\n".join(result["errors"]) if result["errors"] else None,
            status="completed",
            ingested_by=current_user.id,
        )
        db.session.add(log)
        db.session.commit()

        # Recompute all metrics
        _recompute_all_metrics()

        flash(
            f"Successfully ingested {saved} records from {file.filename}. "
            f"({result['invalid_records']} records skipped.)",
            "success",
        )
        return redirect(url_for("dashboard.instructor_dashboard"))

    # GET: show recent ingestion logs
    logs = IngestionLog.query.order_by(IngestionLog.created_at.desc()).limit(10).all()
    return render_template("dashboard/upload.html", logs=logs)


@dashboard_bp.route("/dashboard/import-students", methods=["GET", "POST"])
@login_required
@instructor_required
def import_students():
    """Bulk import student roster from CSV."""
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected.", "danger")
            return redirect(url_for("dashboard.import_students"))

        file = request.files["file"]
        if not file.filename.lower().endswith(".csv"):
            flash("Only CSV files are accepted.", "danger")
            return redirect(url_for("dashboard.import_students"))

        try:
            import pandas as pd
            import io

            content = file.read().decode("utf-8")
            df = pd.read_csv(io.StringIO(content))
            df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

            required = {"student_id", "name"}
            missing = required - set(df.columns)
            if missing:
                flash(f"Missing required columns: {', '.join(missing)}", "danger")
                return redirect(url_for("dashboard.import_students"))

            created = 0
            skipped = 0
            for _, row in df.iterrows():
                sid = str(row["student_id"]).strip()
                name = str(row.get("name", sid)).strip()
                if Student.query.filter_by(student_id=sid).first():
                    skipped += 1
                    continue

                student = Student(
                    student_id=sid,
                    name=name,
                    attendance_pct=_safe_float(row.get("attendance_pct")),
                    mid1_score=_safe_float(row.get("mid1_score")),
                    mid2_score=_safe_float(row.get("mid2_score")),
                    mid3_score=_safe_float(row.get("mid3_score")),
                )
                # Link to course if course_id or course column provided
                course_col = row.get("course_id") or row.get("course")
                if course_col and pd.notna(course_col):
                    course = Course.query.filter_by(course_id=str(course_col).strip()).first()
                    if course:
                        student.course_id = course.id

                db.session.add(student)
                created += 1

            db.session.commit()
            flash(f"Imported {created} students. {skipped} skipped (already exist).", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error importing students: {str(e)}", "danger")

        return redirect(url_for("dashboard.instructor_dashboard"))

    return render_template("dashboard/import_students.html")


def _safe_float(value):
    """Safely convert a value to float, returning None on failure."""
    import numpy as np
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        v = float(value)
        return v if not np.isnan(v) else None
    except (ValueError, TypeError):
        return None


@dashboard_bp.route("/dashboard/report/<student_id>")
@login_required
def student_report(student_id):
    """Generate a printable PDF-friendly credibility report."""
    if current_user.role not in ("instructor", "admin", "principal"):
        abort(403)
    from flask import current_app
    student = Student.query.filter_by(student_id=student_id).first_or_404()

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

    alerts = Alert.query.filter_by(student_id=student.id).order_by(
        Alert.created_at.desc()
    ).all()

    components = [
        {"label": "Δt Consistency", "weight": 25, "score": cred_result["components"]["delta_t_consistency"]["score"]},
        {"label": "Variance Stability", "weight": 10, "score": cred_result["components"]["variance_stability"]["score"]},
        {"label": "Completion", "weight": 10, "score": cred_result["components"]["completion_rate"]["score"]},
        {"label": "Attendance", "weight": 25, "score": cred_result["components"]["attendance"]["score"]},
        {"label": "Exam Performance", "weight": 30, "score": cred_result["components"]["exam_performance"]["score"]},
    ]

    from datetime import datetime
    return render_template(
        "reports/student_report.html",
        student=student,
        score=cred_result["overall_score"],
        tier_label=cred_result["tier_label"],
        components=components,
        submissions=submissions,
        alerts=alerts,
        school_name=current_app.config.get("SCHOOL_NAME", "PASS"),
        generated_at=datetime.now().strftime("%B %d, %Y"),
    )


@dashboard_bp.route("/dashboard/export/csv")
@login_required
@instructor_required
def export_csv():
    """Export current data as CSV (FR-17)."""
    export_type = request.args.get("type", "students")

    output = io.StringIO()
    writer = csv.writer(output)

    if export_type == "students":
        writer.writerow([
            "Roll No", "Name", "Credibility Score", "Total Submissions",
            "On-Time Rate (%)", "Active Alerts", "Status",
        ])
        for s in Student.query.filter_by(status="active").all():
            writer.writerow([
                s.student_id, s.name, round(s.credibility_score, 2),
                s.total_submissions, s.on_time_rate,
                s.active_alerts_count, s.status,
            ])
    elif export_type == "alerts":
        writer.writerow([
            "Alert ID", "Student", "Metric", "% Change", "Window Size",
            "Severity", "Description", "Resolved", "Created At",
        ])
        for a in Alert.query.order_by(Alert.created_at.desc()).all():
            writer.writerow([
                a.alert_id, a.student.name, a.metric, round(a.pct_change, 1),
                a.window_size, a.severity, a.description, a.resolved,
                a.created_at.strftime("%Y-%m-%d %H:%M"),
            ])
    elif export_type == "submissions":
        writer.writerow([
            "Submission ID", "Student", "Assignment", "Submitted At",
            "Deadline", "Δt (hours)", "Status",
        ])
        for s in Submission.query.order_by(Submission.submitted_at.desc()).all():
            writer.writerow([
                s.submission_id, s.student.name, s.assignment_id,
                s.submitted_at.strftime("%Y-%m-%d %H:%M"),
                s.deadline.strftime("%Y-%m-%d %H:%M"),
                round(s.delta_t_hours, 2), s.submission_status,
            ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=pass_export_{export_type}_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )


@dashboard_bp.route("/dashboard/recompute", methods=["POST"])
@login_required
@instructor_required
def trigger_recompute():
    """Recompute all credibility scores and alerts."""
    _recompute_all_metrics()
    flash("All scores and alerts have been recalculated.", "success")
    return redirect(url_for("dashboard.instructor_dashboard"))


@dashboard_bp.route("/dashboard/notifications")
@login_required
@instructor_required
def notifications():
    """Notification center — view and filter all alerts."""
    page = request.args.get("page", 1, type=int)
    severity = request.args.get("severity", "")
    status_filter = request.args.get("status", "")

    query = Alert.query.join(Student).order_by(Alert.created_at.desc())

    if severity in ("critical", "warning", "info"):
        query = query.filter(Alert.severity == severity)
    if status_filter == "unread":
        query = query.filter(Alert.read == False)
    elif status_filter == "resolved":
        query = query.filter(Alert.resolved == True)
    elif status_filter == "active":
        query = query.filter(Alert.resolved == False)

    pagination = query.paginate(page=page, per_page=25, error_out=False)
    alerts = pagination.items

    unread_count = Alert.query.filter_by(read=False, resolved=False).count()

    return render_template(
        "dashboard/notifications.html",
        alerts=alerts,
        pagination=pagination,
        unread_count=unread_count,
        active_severity=severity,
        active_status=status_filter,
    )


@dashboard_bp.route("/dashboard/notifications/mark-read", methods=["POST"])
@login_required
@instructor_required
def mark_notification_read():
    """Mark a single alert as read."""
    data = request.get_json(silent=True)
    if not data or "alert_id" not in data:
        return jsonify({"success": False, "error": "Missing alert_id"}), 400

    alert = Alert.query.filter_by(alert_id=data["alert_id"]).first()
    if not alert:
        return jsonify({"success": False, "error": "Alert not found"}), 404

    alert.read = True
    alert.read_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route("/dashboard/notifications/mark-all-read", methods=["POST"])
@login_required
@instructor_required
def mark_all_notifications_read():
    """Mark all unread, unresolved alerts as read."""
    now = datetime.now(timezone.utc)
    Alert.query.filter_by(read=False, resolved=False).update(
        {"read": True, "read_at": now}
    )
    db.session.commit()
    return jsonify({"success": True})


@dashboard_bp.route("/dashboard/notifications/unread-count")
@login_required
def unread_notification_count():
    """Return unread alert count for navbar badge."""
    count = Alert.query.filter_by(read=False, resolved=False).count()
    return jsonify({"count": count})


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def _save_ingestion_records(records):
    """Save validated ingestion records to the database."""
    saved_count = 0

    for rec in records:
        # Find or create student
        student = Student.query.filter_by(student_id=rec["student_id"]).first()
        if not student:
            student = Student(
                student_id=rec["student_id"],
                name=rec.get("student_name") or rec["student_id"],
            )
            db.session.add(student)
            db.session.flush()

        # Update attendance & exam scores if provided in CSV
        if rec.get("attendance_pct") is not None:
            student.attendance_pct = rec["attendance_pct"]
        if rec.get("mid1_score") is not None:
            student.mid1_score = rec["mid1_score"]
        if rec.get("mid2_score") is not None:
            student.mid2_score = rec["mid2_score"]
        if rec.get("mid3_score") is not None:
            student.mid3_score = rec["mid3_score"]

        # Find or create course
        course = None
        if rec.get("course_id"):
            course = Course.query.filter_by(course_id=rec["course_id"]).first()
            if not course:
                course = Course(
                    course_id=rec["course_id"],
                    course_name=rec["course_id"],
                    semester="Current",
                )
                db.session.add(course)
                db.session.flush()

            if not student.course_id:
                student.course_id = course.id

        # Check for duplicate submissions
        existing = Submission.query.filter_by(
            submission_id=rec["submission_id"]
        ).first()
        if existing:
            continue

        # Create submission record
        submission = Submission(
            submission_id=rec["submission_id"],
            student_id=student.id,
            assignment_id=rec["assignment_id"],
            course_id_ref=course.id if course else None,
            submitted_at=rec["submitted_at"],
            deadline=rec["deadline"],
            delta_t=rec["delta_t"],
            delta_t_hours=rec["delta_t_hours"],
            submission_status=rec["submission_status"],
        )
        db.session.add(submission)
        saved_count += 1

    db.session.commit()
    return saved_count


def _recompute_all_metrics():
    """
    Recompute all metrics after new data ingestion (FR-07).
    Updates credibility scores and generates any new alerts.
    """
    students = Student.query.filter_by(status="active").all()

    for student in students:
        submissions = Submission.query.filter_by(
            student_id=student.id
        ).order_by(Submission.submitted_at.asc()).all()

        if not submissions:
            continue

        delta_t_values = [s.delta_t for s in submissions]

        # Compute metrics
        summary = metric_computer.compute_student_summary(delta_t_values)
        variance_series = metric_computer.compute_rolling_variance_series(delta_t_values)

        # Compute credibility score
        total_assignments = max(len(submissions), 1)
        prev_score = student.credibility_score
        cred_result = credibility_scorer.compute_credibility_score(
            delta_t_values=delta_t_values,
            variance_value=summary["current_variance"],
            submitted_count=len(submissions),
            total_assignments=total_assignments,
            attendance_pct=student.attendance_pct or 0.0,
            mid1=student.mid1_score,
            mid2=student.mid2_score,
            mid3=student.mid3_score,
            historical_variances=[v for v in variance_series if v is not None],
        )
        student.credibility_score = cred_result["overall_score"]

        # Run hysteresis analysis
        existing_alerts = [
            a.to_dict() for a in Alert.query.filter_by(
                student_id=student.id, resolved=False
            ).all()
        ]
        valid_variances = [v for v in variance_series if v is not None]

        analysis = hysteresis_filter.run_full_analysis(
            delta_t_values=delta_t_values,
            variance_values=valid_variances,
            existing_alerts=existing_alerts,
        )

        # Persist consecutive_improvements back to DB before creating new alerts
        for alert_dict in existing_alerts:
            if "consecutive_improvements" in alert_dict and alert_dict.get("alert_id"):
                db_alert = Alert.query.filter_by(alert_id=alert_dict["alert_id"]).first()
                if db_alert:
                    db_alert.consecutive_improvements = alert_dict["consecutive_improvements"]

        # Create new alerts
        for alert_data in analysis["new_alerts"]:
            alert = Alert(
                alert_id=alert_data["alert_id"],
                student_id=student.id,
                metric=alert_data["metric"],
                pct_change=alert_data["pct_change"],
                window_size=alert_data["window_size"],
                severity=alert_data["severity"],
                description=alert_data["description"],
            )
            db.session.add(alert)

        # Resolve alerts
        for alert_id in analysis["resolved_alert_ids"]:
            alert = Alert.query.filter_by(alert_id=alert_id).first()
            if alert:
                alert.resolved = True
                alert.resolved_at = datetime.now(timezone.utc)

        # Check for policy triggers
        policy_events = credibility_scorer.check_policy_triggers(
            cred_result["overall_score"], prev_score
        )
        for event_data in policy_events:
            event = PolicyEvent(
                event_id=f"POL-{uuid.uuid4().hex[:8].upper()}",
                student_id=student.id,
                policy_type=event_data["policy_type"],
                description=event_data["description"],
                triggered_at=event_data["triggered_at"],
                expires_at=event_data.get("expires_at"),
            )
            db.session.add(event)

    db.session.commit()


@dashboard_bp.route("/ai-query", methods=["POST"])
@csrf.exempt
@login_required
def ai_query():
    """Process a natural-language query and return AI-style response."""
    if current_user.role not in ("instructor", "admin", "principal"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True)
    if not data or "query" not in data:
        return jsonify({"error": "Missing query"}), 400

    try:
        engine = AIQueryEngine(db)
        result = engine.process(data["query"])
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"AI query error: %s", e)
        return jsonify({"response": "Sorry, something went wrong processing that. Please try a different question.", "data": None})
