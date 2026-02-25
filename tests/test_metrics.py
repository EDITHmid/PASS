"""
PASS — MetricComputer Unit Tests
====================================
Tests for engine/metrics.py (FR-02, FR-03, FR-04).
"""

import pytest
from engine.metrics import MetricComputer


class TestMetricComputer:
    """Test the MetricComputer class."""

    def setup_method(self):
        self.mc = MetricComputer()

    # ── compute_delta_t ─────────────────────────────────────────

    def test_delta_t_early_submission(self):
        """FR-02: Δt > 0 when submitted before deadline."""
        from datetime import datetime, timezone
        deadline = datetime(2025, 1, 15, 23, 59, 0, tzinfo=timezone.utc)
        submitted = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        dt = self.mc.compute_delta_t(submitted.timestamp(), deadline.timestamp())
        assert dt > 0, "Δt should be positive for early submissions"

    def test_delta_t_late_submission(self):
        """FR-02: Δt < 0 when submitted after deadline."""
        from datetime import datetime, timezone
        deadline = datetime(2025, 1, 15, 23, 59, 0, tzinfo=timezone.utc)
        submitted = datetime(2025, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
        dt = self.mc.compute_delta_t(submitted.timestamp(), deadline.timestamp())
        assert dt < 0, "Δt should be negative for late submissions"

    def test_delta_t_exact_deadline(self):
        """FR-02: Δt = 0 at exact deadline."""
        from datetime import datetime, timezone
        deadline = datetime(2025, 1, 15, 23, 59, 0, tzinfo=timezone.utc)
        dt = self.mc.compute_delta_t(deadline.timestamp(), deadline.timestamp())
        assert dt == 0

    # ── delta_t_to_hours ────────────────────────────────────────

    def test_delta_t_to_hours_positive(self):
        dt_seconds = 7200  # 2 hours
        result = self.mc.delta_t_to_hours(dt_seconds)
        assert abs(result - 2.0) < 0.001

    def test_delta_t_to_hours_negative(self):
        dt_seconds = -3600  # -1 hour
        result = self.mc.delta_t_to_hours(dt_seconds)
        assert abs(result - (-1.0)) < 0.001

    # ── classify_submission ─────────────────────────────────────

    def test_classify_on_time(self):
        assert self.mc.classify_submission(3600) == "on-time"

    def test_classify_late(self):
        assert self.mc.classify_submission(-7200) == "late"

    def test_classify_edge_zero(self):
        assert self.mc.classify_submission(0) == "on-time"

    # ── compute_variance_stability ──────────────────────────────

    def test_variance_stability_uniform(self):
        """FR-03: Uniform submissions should have low variance."""
        values = [10.0, 10.0, 10.0, 10.0, 10.0]
        result = self.mc.compute_variance_stability(values)
        assert result == 0.0

    def test_variance_stability_varied(self):
        """FR-03: Varied submissions should have higher variance."""
        values = [10.0, -5.0, 20.0, -10.0, 15.0]
        result = self.mc.compute_variance_stability(values)
        assert result > 0

    def test_variance_stability_empty(self):
        result = self.mc.compute_variance_stability([])
        assert result == 0.0

    def test_variance_stability_single(self):
        result = self.mc.compute_variance_stability([5.0])
        assert result == 0.0

    # ── compute_rolling_variance_series ─────────────────────────

    def test_rolling_variance_series_length(self):
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = self.mc.compute_rolling_variance_series(values)
        assert len(result) == len(values)

    def test_rolling_variance_first_elements_none(self):
        values = [1, 2, 3, 4, 5]
        result = self.mc.compute_rolling_variance_series(values)
        assert result[0] is None  # First element always None
        assert result[-1] is not None  # Last element has enough data

    # ── compute_trend_direction ─────────────────────────────────

    def test_trend_declining(self):
        values = [20.0, 15.0, 10.0, 5.0, 0.0]
        result = self.mc.compute_trend_direction(values)
        assert result["direction"] == "worsening"

    def test_trend_improving(self):
        values = [0.0, 5.0, 10.0, 15.0, 20.0]
        result = self.mc.compute_trend_direction(values)
        assert result["direction"] == "improving"

    def test_trend_stable(self):
        values = [10.0, 10.0, 10.0, 10.0, 10.0]
        result = self.mc.compute_trend_direction(values)
        assert result["direction"] == "stable"

    # ── compute_student_summary ─────────────────────────────────

    def test_student_summary_structure(self):
        values = [3600, 7200, -1800, 5400, 900]
        result = self.mc.compute_student_summary(values)
        assert "mean_delta_t" in result
        assert "current_variance" in result
        assert "trend" in result
        assert "total_submissions" in result

    def test_student_summary_empty(self):
        result = self.mc.compute_student_summary([])
        assert result["total_submissions"] == 0
