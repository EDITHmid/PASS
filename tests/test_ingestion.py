"""
PASS — DataIngestor Unit Tests
=================================
Tests for engine/ingestion.py (FR-01).
"""

import pytest
from engine.ingestion import DataIngestor


class TestDataIngestor:
    """Test the DataIngestor class."""

    def setup_method(self):
        self.ingestor = DataIngestor()

    # ── validate_csv_structure ──────────────────────────────────

    def test_valid_csv_structure(self):
        """FR-01: Valid CSV with all required columns passes."""
        csv_content = (
            "student_id,student_name,assignment_id,submission_timestamp,deadline_timestamp,course_id\n"
            "1RV22CS001,Arjun Mehta,A01,2025-01-15 14:30:00,2025-01-15 23:59:00,CS501\n"
        )
        result = self.ingestor.validate_csv_structure(csv_content)
        assert result["valid"] is True

    def test_missing_columns(self):
        """FR-01: CSV missing required columns should fail."""
        csv_content = "student_id,assignment_id\n1RV22CS001,A01\n"
        result = self.ingestor.validate_csv_structure(csv_content)
        assert result["valid"] is False

    def test_empty_csv(self):
        result = self.ingestor.validate_csv_structure("")
        assert result["valid"] is False

    # ── ingest_csv ──────────────────────────────────────────────

    def test_ingest_valid_csv(self):
        """FR-01: Full pipeline ingestion of valid data."""
        csv_content = (
            "student_id,student_name,assignment_id,submission_timestamp,deadline_timestamp,course_id\n"
            "1RV22CS001,Arjun Mehta,A01,2025-01-15 14:30:00,2025-01-15 23:59:00,CS501\n"
            "1RV22CS002,Priya Reddy,A01,2025-01-14 10:00:00,2025-01-15 23:59:00,CS501\n"
        )
        result = self.ingestor.ingest_csv(csv_content, "test.csv")
        assert result["success"] is True
        assert result["valid_records"] == 2
        assert result["invalid_records"] == 0
        assert len(result["records"]) == 2

    def test_ingest_computes_delta_t(self):
        """FR-02: Verify Δt is computed correctly during ingestion."""
        csv_content = (
            "student_id,student_name,assignment_id,submission_timestamp,deadline_timestamp,course_id\n"
            "1RV22CS001,Arjun,A01,2025-01-15 12:00:00,2025-01-15 23:59:00,CS501\n"
        )
        result = self.ingestor.ingest_csv(csv_content, "test.csv")
        assert result["success"] is True
        record = result["records"][0]
        # Submitted ~12h before deadline, Δt should be positive
        assert record["delta_t"] > 0
        assert record["delta_t_hours"] > 0

    def test_ingest_late_submission(self):
        """FR-02: Late submission has negative Δt."""
        csv_content = (
            "student_id,student_name,assignment_id,submission_timestamp,deadline_timestamp,course_id\n"
            "1RV22CS001,Arjun,A01,2025-01-16 12:00:00,2025-01-15 23:59:00,CS501\n"
        )
        result = self.ingestor.ingest_csv(csv_content, "test.csv")
        record = result["records"][0]
        assert record["delta_t"] < 0
        assert record["submission_status"] == "late"

    def test_ingest_invalid_row(self):
        """FR-01: Invalid rows should be skipped with error count."""
        csv_content = (
            "student_id,student_name,assignment_id,submission_timestamp,deadline_timestamp,course_id\n"
            "1RV22CS001,Arjun,A01,2025-01-15 14:30:00,2025-01-15 23:59:00,CS501\n"
            ",,,,,\n"  # Invalid row — all fields empty (NaN)
        )
        result = self.ingestor.ingest_csv(csv_content, "test.csv")
        assert result["success"] is True
        assert result["valid_records"] >= 1
        assert result["invalid_records"] >= 1

    def test_ingest_multiple_date_formats(self):
        """FR-01: Support multiple datetime formats."""
        csv_content = (
            "student_id,student_name,assignment_id,submission_timestamp,deadline_timestamp,course_id\n"
            "1RV22CS001,Arjun,A01,2025-01-15 14:30:00,2025-01-15 23:59:00,CS501\n"
        )
        result = self.ingestor.ingest_csv(csv_content, "test.csv")
        assert result["success"] is True

    # ── _parse_timestamp ────────────────────────────────────────

    def test_parse_standard_format(self):
        ts = self.ingestor._parse_timestamp("2025-01-15 14:30:00")
        assert ts is not None
        assert ts.year == 2025
        assert ts.month == 1
        assert ts.day == 15

    def test_parse_invalid_timestamp(self):
        with pytest.raises(ValueError):
            self.ingestor._parse_timestamp("not-a-date")

    def test_parse_empty_timestamp(self):
        """Empty string raises ValueError."""
        import pytest
        with pytest.raises(ValueError):
            self.ingestor._parse_timestamp("")
