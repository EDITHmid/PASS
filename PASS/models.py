"""
PASS Database Models
======================
SQLAlchemy ORM models for the Proactive Academic Support System.
Implements the schema defined in PRD Section 8.2.
"""

import secrets
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app import db, login_manager


# ─────────────────────────────────────────────────────────────────────────────
# Authentication Models
# ─────────────────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    """
    Application user (instructor, admin, student, or principal).
    Handles authentication and role-based access control.
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(
        db.String(20), nullable=False, default="student"
    )  # 'student', 'teacher', 'hod', 'principal', 'admin'
    full_name = db.Column(db.String(100), nullable=False, default="")
    phone = db.Column(db.String(20), nullable=True)
    email_notifications = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    student_profile = db.relationship(
        "Student", backref="user", uselist=False, lazy=True
    )

    def set_password(self, password):
        """Hash and store password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return db.session.get(User, int(user_id))


# ─────────────────────────────────────────────────────────────────────────────
# Academic Models
# ─────────────────────────────────────────────────────────────────────────────

class Course(db.Model):
    """Academic course entity."""

    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    course_name = db.Column(db.String(150), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(10), default="A")  # Section A, B, C
    instructor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    instructor = db.relationship("User", backref="courses_taught", lazy=True)
    students = db.relationship("Student", backref="course", lazy=True)
    submissions = db.relationship("Submission", backref="course", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Course {self.course_id}: {self.course_name}>"


class Student(db.Model):
    """
    Student academic profile.
    Master student registry as defined in PRD Section 8.2.
    """

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(
        db.Integer, db.ForeignKey("courses.id"), nullable=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, unique=True
    )
    credibility_score = db.Column(db.Float, default=50.0)
    attendance_pct = db.Column(db.Float, default=0.0)  # 0–100 attendance percentage
    mid1_score = db.Column(db.Float, nullable=True)  # Mid-1 exam score (0–100)
    mid2_score = db.Column(db.Float, nullable=True)  # Mid-2 exam score (0–100)
    mid3_score = db.Column(db.Float, nullable=True)  # Mid-3 exam score (0–100)
    enrollment_date = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    status = db.Column(
        db.String(20), default="active"
    )  # 'active', 'inactive', 'graduated'

    # Relationships
    submissions = db.relationship(
        "Submission", backref="student", lazy=True,
        order_by="Submission.submitted_at", cascade="all, delete-orphan"
    )
    alerts = db.relationship(
        "Alert", backref="student", lazy=True,
        order_by="Alert.created_at.desc()", cascade="all, delete-orphan"
    )
    policy_events = db.relationship(
        "PolicyEvent", backref="student", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def active_alerts_count(self):
        """Count of unresolved alerts."""
        return len([a for a in self.alerts if not a.resolved])

    @property
    def total_submissions(self):
        """Total number of submissions."""
        return len(self.submissions)

    @property
    def on_time_rate(self):
        """Percentage of on-time submissions."""
        if not self.submissions:
            return 0.0
        on_time = sum(1 for s in self.submissions if s.delta_t >= 0)
        return round((on_time / len(self.submissions)) * 100, 1)

    @property
    def best_two_mid_avg(self):
        """Average of the best 2 out of 3 mid-term scores."""
        scores = [s for s in [self.mid1_score, self.mid2_score, self.mid3_score] if s is not None]
        if len(scores) < 2:
            return None
        scores.sort(reverse=True)
        return round((scores[0] + scores[1]) / 2.0, 2)

    def to_dict(self):
        """Serialize student data for API responses."""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "name": self.name,
            "credibility_score": round(self.credibility_score, 2),
            "attendance_pct": round(self.attendance_pct, 1) if self.attendance_pct else 0.0,
            "mid1_score": self.mid1_score,
            "mid2_score": self.mid2_score,
            "mid3_score": self.mid3_score,
            "best_two_mid_avg": self.best_two_mid_avg,
            "total_submissions": self.total_submissions,
            "on_time_rate": self.on_time_rate,
            "active_alerts": self.active_alerts_count,
            "status": self.status,
        }

    def __repr__(self):
        return f"<Student {self.student_id}: {self.name}>"


class Submission(db.Model):
    """
    Raw submission records with computed Δt.
    Stores the temporal relationship between submission and deadline.
    """

    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    assignment_id = db.Column(db.String(50), nullable=False, index=True)
    course_id_ref = db.Column(
        db.Integer, db.ForeignKey("courses.id"), nullable=True
    )
    submitted_at = db.Column(db.DateTime, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    delta_t = db.Column(db.Float, nullable=False)  # seconds: positive=early, negative=late
    delta_t_hours = db.Column(db.Float, nullable=False)  # Δt in hours for readability
    submission_status = db.Column(
        db.String(20), default="on-time"
    )  # 'on-time', 'late', 'missing'
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        """Serialize submission data for API responses."""
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "assignment_id": self.assignment_id,
            "submitted_at": self.submitted_at.isoformat(),
            "deadline": self.deadline.isoformat(),
            "delta_t": round(self.delta_t, 2),
            "delta_t_hours": round(self.delta_t_hours, 2),
            "status": self.submission_status,
        }

    def __repr__(self):
        return f"<Submission {self.submission_id} Δt={self.delta_t_hours:.1f}h>"


class Alert(db.Model):
    """
    Hysteresis-confirmed alerts log.
    Only contains statistically validated behavioral drift warnings.
    """

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    metric = db.Column(db.String(30), nullable=False)  # 'delta_t', 'variance'
    pct_change = db.Column(db.Float, nullable=False)
    window_size = db.Column(db.Integer, nullable=False)
    severity = db.Column(
        db.String(20), default="warning"
    )  # 'info', 'warning', 'critical'
    description = db.Column(db.Text, nullable=False)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    consecutive_improvements = db.Column(db.Integer, default=0)
    read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self):
        """Serialize alert data for API responses."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else "Unknown",
            "metric": self.metric,
            "pct_change": round(self.pct_change, 1),
            "window_size": self.window_size,
            "severity": self.severity,
            "description": self.description,
            "resolved": self.resolved,
            "consecutive_improvements": self.consecutive_improvements,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<Alert {self.alert_id} [{self.severity}] resolved={self.resolved}>"


class PolicyEvent(db.Model):
    """
    Automated perks and waivers triggered by credibility scores.
    Implements FR-13: Automated policy triggering.
    """

    __tablename__ = "policy_events"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    policy_type = db.Column(
        db.String(50), nullable=False
    )  # 'attendance_waiver', 'deadline_extension', 'recognition'
    description = db.Column(db.Text, nullable=True)
    triggered_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    triggered_by = db.Column(
        db.String(20), default="system"
    )  # 'system' or 'manual'

    def to_dict(self):
        """Serialize policy event for API responses."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "student_name": self.student.name if self.student else "Unknown",
            "policy_type": self.policy_type,
            "description": self.description,
            "triggered_at": self.triggered_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "triggered_by": self.triggered_by,
        }

    def __repr__(self):
        return f"<PolicyEvent {self.event_id} type={self.policy_type}>"


class IngestionLog(db.Model):
    """
    Data ingestion audit log.
    Tracks CSV uploads and API polls for transparency (FR-04).
    """

    __tablename__ = "ingestion_logs"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=True)
    source = db.Column(db.String(20), nullable=False)  # 'csv', 'api'
    total_records = db.Column(db.Integer, default=0)
    valid_records = db.Column(db.Integer, default=0)
    invalid_records = db.Column(db.Integer, default=0)
    errors = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="completed")  # 'completed', 'failed', 'partial'
    ingested_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<IngestionLog {self.filename} [{self.status}]>"


# ─────────────────────────────────────────────────────────────────────────────
# Parent / Guardian Model
# ─────────────────────────────────────────────────────────────────────────────

class Guardian(db.Model):
    """
    Parent or guardian linked to one or more students.
    Enables parent dashboard access to their child's academic data.
    """

    __tablename__ = "guardians"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    relationship = db.Column(db.String(50), default="Parent")
    notification_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = db.relationship("User", backref="guardian_profile", uselist=False, lazy=True)
    students = db.relationship("StudentGuardian", backref="guardian", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Guardian {self.full_name}>"


class StudentGuardian(db.Model):
    """Many-to-many link between students and guardians."""

    __tablename__ = "student_guardians"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    guardian_id = db.Column(db.Integer, db.ForeignKey("guardians.id"), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)

    student = db.relationship("Student", backref=db.backref("guardian_links", lazy=True))

    __table_args__ = (
        db.UniqueConstraint("student_id", "guardian_id", name="uq_student_guardian"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Academic Year / Semester
# ─────────────────────────────────────────────────────────────────────────────

class AcademicYear(db.Model):
    """
    Academic year and semester grouping.
    Enables data isolation across different school years.
    """

    __tablename__ = "academic_years"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # e.g. "2025-26"
    semester = db.Column(db.String(20), default="Annual")  # "Odd", "Even", "Annual"
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    courses = db.relationship("Course", backref="academic_year_ref", lazy=True)

    def __repr__(self):
        return f"<AcademicYear {self.name} ({self.semester})>"


# ─────────────────────────────────────────────────────────────────────────────
# Password Reset Token
# ─────────────────────────────────────────────────────────────────────────────

class PasswordResetToken(db.Model):
    """
    Secure one-time password reset tokens with expiration.
    """

    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", backref=db.backref("reset_tokens", lazy=True, cascade="all, delete-orphan"))

    @staticmethod
    def generate(user_id, expiry_hours=24):
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        return PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires,
        )

    def is_valid(self):
        return not self.used and datetime.now(timezone.utc) < self.expires_at

    def __repr__(self):
        return f"<PasswordResetToken user={self.user_id} used={self.used}>"


# ─────────────────────────────────────────────────────────────────────────────
# ERP Core Models
# ─────────────────────────────────────────────────────────────────────────────
class Student(db.Model):
    __tablename__ = "student"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10))
    photo = db.Column(db.String)  # path to uploaded image

    contact = db.relationship("ContactInfo", uselist=False, cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    grades = db.relationship("Grade", back_populates="student", cascade="all, delete-orphan")
    attendances = db.relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    invoices = db.relationship("Invoice", back_populates="student", cascade="all, delete-orphan")

    def get_pass_score(self):
        """Return the PASS credibility/weight for this student.
        Delegates to the PASS engine if available.
        """
        from .engine.ai_query import compute_student_score
        return compute_student_score(self)

class ContactInfo(db.Model):
    __tablename__ = "contact_info"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    address = db.Column(db.String(200))
    student = db.relationship("Student", back_populates="contact")

class Teacher(db.Model):
    __tablename__ = "teacher"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), unique=True)
    classes = db.relationship("Class", back_populates="teacher")

class Class(db.Model):
    __tablename__ = "class"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)  # e.g. "10‑A"
    year = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"))
    teacher = db.relationship("Teacher", back_populates="classes")
    enrollments = db.relationship("Enrollment", back_populates="class_", cascade="all, delete-orphan")
    schedule = db.relationship("Schedule", uselist=False, cascade="all, delete-orphan")

class Enrollment(db.Model):
    __tablename__ = "enrollment"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    class_id = db.Column(db.Integer, db.ForeignKey("class.id"))
    start_date = db.Column(db.Date, default=db.func.current_date())
    end_date = db.Column(db.Date, nullable=True)
    student = db.relationship("Student", back_populates="enrollments")
    class_ = db.relationship("Class", back_populates="enrollments")

# Simple stubs for future ERP features – they can be expanded later
class Grade(db.Model):
    __tablename__ = "grade"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    subject = db.Column(db.String(64), nullable=False)
    score = db.Column(db.Float, nullable=False)
    student = db.relationship("Student", back_populates="grades")

class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    date = db.Column(db.Date, default=db.func.current_date())
    status = db.Column(db.String(10), nullable=False)  # Present/Absent/Excused
    student = db.relationship("Student", back_populates="attendances")

class Invoice(db.Model):
    __tablename__ = "invoice"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"))
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    student = db.relationship("Student", back_populates="invoices")

class Schedule(db.Model):
    __tablename__ = "schedule"
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("class.id"))
    day_of_week = db.Column(db.String(10), nullable=False)  # Mon‑Fri
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    class_ = db.relationship("Class", back_populates="schedule")

# ---------------------------------------------------
# Communications models
# ---------------------------------------------------
class Announcement(db.Model):
    __tablename__ = "announcement"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.relationship("User", backref="announcements")

class Message(db.Model):
    __tablename__ = "message"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.String(120))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    read = db.Column(db.Boolean, default=False)
    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])

# ─────────────────────────────────────────────────────────────────────────────

class ConfigSetting(db.Model):
    """
    Key-value configuration store for runtime-persistent settings.
    Currently used for scoring weights, but extensible to any setting.
    """

    __tablename__ = "config_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)

    @classmethod
    def get_weights(cls):
        """Return all weight settings as a dict."""
        settings = cls.query.filter(cls.key.startswith("weight_")).all()
        return {s.key: s.value for s in settings}

    @classmethod
    def set_weight(cls, key, value):
        """Upsert a single weight setting."""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        return setting

    def __repr__(self):
        return f"<ConfigSetting {self.key}={self.value}>"
