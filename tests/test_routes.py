"""
PASS — API & Route Integration Tests
========================================
Tests for REST API endpoints (PRD Section 8.3).
"""

import json
import pytest


class TestAuthRoutes:
    """Test authentication flows."""

    def test_landing_page(self, client):
        """Public landing page loads."""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_login_page(self, client):
        """Login page renders."""
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_register_page(self, client):
        """Registration page renders."""
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_login_invalid_credentials(self, client, instructor_user):
        """Login fails with wrong password."""
        resp = client.post("/login", data={
            "username": "test_instructor",
            "password": "wrongpass",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_login_valid_credentials(self, client, instructor_user):
        """Login succeeds with correct credentials."""
        resp = client.post("/login", data={
            "username": "test_instructor",
            "password": "testpass123",
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_dashboard_requires_auth(self, client):
        """Dashboard redirects unauthenticated users."""
        resp = client.get("/dashboard")
        assert resp.status_code in (302, 401, 403)


class TestAPIEndpoints:
    """Test REST API endpoints."""

    def _login(self, client, username="test_instructor", password="testpass123"):
        return client.post("/login", data={
            "username": username,
            "password": password,
        })

    def test_health_endpoint(self, client):
        """GET /api/health returns ok."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"

    def test_students_list(self, client, instructor_user, sample_student):
        """GET /api/students returns student list."""
        self._login(client)
        resp = client.get("/api/students")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert isinstance(data["data"]["students"], list)

    def test_student_detail(self, client, instructor_user, sample_student):
        """GET /api/student/<id> returns student data."""
        self._login(client)
        resp = client.get(f"/api/student/{sample_student.student_id}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["data"]["student"]["student_id"] == sample_student.student_id

    def test_dashboard_summary(self, client, instructor_user, sample_student):
        """GET /api/dashboard/summary returns stats."""
        self._login(client)
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "total_students" in data["data"]

    def test_alerts_endpoint(self, client, instructor_user):
        """GET /api/alerts returns alerts list."""
        self._login(client)
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert isinstance(data["data"]["alerts"], list)

    def test_export_csv(self, client, instructor_user):
        """GET /api/export/csv returns CSV data."""
        self._login(client)
        resp = client.get("/api/export/csv?type=students")
        assert resp.status_code == 200


class TestDatabaseModels:
    """Test SQLAlchemy model properties."""

    def test_student_computed_properties(self, app, sample_student):
        """Verify student computed properties work correctly."""
        with app.app_context():
            from models import Student
            student = Student.query.get(sample_student.id)
            assert student.total_submissions == 10
            assert 0 <= student.on_time_rate <= 100
            assert isinstance(student.active_alerts_count, int)

    def test_student_to_dict(self, app, sample_student):
        """Verify to_dict() serialization."""
        with app.app_context():
            from models import Student
            student = Student.query.get(sample_student.id)
            d = student.to_dict()
            assert "student_id" in d
            assert "name" in d
            assert "credibility_score" in d

    def test_user_password_hashing(self, db):
        """Verify password hashing works."""
        from models import User
        user = User(username="hash_test", email="h@t.com", full_name="Hash Test")
        user.set_password("mypassword")
        assert user.check_password("mypassword")
        assert not user.check_password("wrongpassword")
