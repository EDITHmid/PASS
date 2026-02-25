"""
PASS — Test Configuration
============================
Pytest fixtures and shared test setup.
"""

import os
import sys
import pytest

# Ensure project root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db as _db
from models import User, Course, Student, Submission


@pytest.fixture(scope="session")
def app():
    """Create application instance for testing."""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SERVER_NAME"] = "localhost"
    return app


@pytest.fixture(scope="function")
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app, db):
    """Test client."""
    return app.test_client()


@pytest.fixture
def instructor_user(db):
    """Create an instructor user."""
    user = User(
        username="test_instructor",
        email="instructor@test.edu",
        full_name="Test Instructor",
        role="instructor",
    )
    user.set_password("testpass123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def student_user(db):
    """Create a student user with linked Student profile."""
    user = User(
        username="test_student",
        email="student@test.edu",
        full_name="Test Student",
        role="student",
    )
    user.set_password("testpass123")
    db.session.add(user)
    db.session.flush()

    student = Student(
        student_id="1RV22CS999",
        name="Test Student",
        user_id=user.id,
        credibility_score=65.0,
    )
    db.session.add(student)
    db.session.commit()
    return user


@pytest.fixture
def sample_student(db):
    """Create a sample student with submissions."""
    from datetime import datetime, timezone, timedelta

    student = Student(
        student_id="1RV22CS001",
        name="Sample Student",
        credibility_score=72.5,
    )
    db.session.add(student)
    db.session.flush()

    base_deadline = datetime(2025, 1, 13, 23, 59, 0, tzinfo=timezone.utc)
    delta_t_values = [12.0, 8.5, 15.2, -2.3, 6.7, -5.1, 10.0, 3.2, -1.5, 7.8]

    for i, dt_hours in enumerate(delta_t_values):
        deadline = base_deadline + timedelta(weeks=i)
        sub = Submission(
            submission_id=f"SUB-TEST-{i:03d}",
            student_id=student.id,
            assignment_id=f"A{i+1:02d}",
            submitted_at=deadline - timedelta(hours=dt_hours),
            deadline=deadline,
            delta_t=dt_hours * 3600,
            delta_t_hours=dt_hours,
            submission_status="on_time" if dt_hours >= 0 else "late",
        )
        db.session.add(sub)

    db.session.commit()
    return student
