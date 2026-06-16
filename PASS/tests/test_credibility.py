"""
PASS — CredibilityScorer Unit Tests
=======================================
Tests for engine/credibility.py (FR-07, FR-10, FR-11, FR-12).

Five-factor credibility model:
  25% Δt Consistency + 10% Variance Stability + 10% Completion
  + 25% Attendance + 30% Exam Performance (best 2 of 3 mids)
"""

import pytest
from engine.credibility import CredibilityScorer


class TestCredibilityScorer:
    """Test the CredibilityScorer class."""

    def setup_method(self):
        self.cs = CredibilityScorer()

    # ── compute_delta_t_score ───────────────────────────────────

    def test_delta_t_score_all_early(self):
        """FR-07: Consistently early students get high Δt score."""
        values = [86400, 72000, 54000, 43200]  # 24h, 20h, 15h, 12h early
        score = self.cs.compute_delta_t_score(values)
        assert score >= 80

    def test_delta_t_score_all_late(self):
        """FR-07: Consistently late students get low Δt score."""
        values = [-86400, -72000, -54000, -43200]
        score = self.cs.compute_delta_t_score(values)
        assert score <= 30

    def test_delta_t_score_mixed(self):
        values = [43200, -3600, 7200, -7200, 3600]
        score = self.cs.compute_delta_t_score(values)
        assert 20 <= score <= 80

    def test_delta_t_score_empty(self):
        score = self.cs.compute_delta_t_score([])
        assert score == 50.0  # Neutral default for no data

    # ── compute_variance_score ──────────────────────────────────

    def test_variance_score_stable(self):
        """FR-07: Low variance gets high stability score."""
        score = self.cs.compute_variance_score(100)
        assert score >= 80

    def test_variance_score_unstable(self):
        """FR-07: High variance gets low stability score."""
        score = self.cs.compute_variance_score(100000)
        assert score <= 40

    def test_variance_score_zero(self):
        score = self.cs.compute_variance_score(0)
        assert score == 100

    # ── compute_completion_score ────────────────────────────────

    def test_completion_full(self):
        """All assignments submitted."""
        score = self.cs.compute_completion_score(10, 10)
        assert score == 100

    def test_completion_partial(self):
        score = self.cs.compute_completion_score(7, 10)
        assert 50 <= score <= 100

    def test_completion_none(self):
        score = self.cs.compute_completion_score(0, 10)
        assert score == 0

    # ── compute_attendance_score ────────────────────────────────

    def test_attendance_perfect(self):
        """≥95% attendance gets 100."""
        score = self.cs.compute_attendance_score(98.0)
        assert score == 100.0

    def test_attendance_good(self):
        """85-95% attendance gets 80-100."""
        score = self.cs.compute_attendance_score(90.0)
        assert 80 <= score <= 100

    def test_attendance_minimum_eligible(self):
        """75% attendance (minimum exam eligibility) gets ~60."""
        score = self.cs.compute_attendance_score(75.0)
        assert 55 <= score <= 65

    def test_attendance_poor(self):
        """Below 60% gets very low score."""
        score = self.cs.compute_attendance_score(40.0)
        assert score <= 25

    def test_attendance_zero(self):
        score = self.cs.compute_attendance_score(0.0)
        assert score == 0.0

    # ── compute_exam_score ──────────────────────────────────────

    def test_exam_best_two_of_three(self):
        """Best 2 of 3 mid-terms are picked."""
        # mid1=80, mid2=90, mid3=50 → best 2 = (90+80)/2 = 85 → score=100
        score = self.cs.compute_exam_score(mid1=80, mid2=90, mid3=50)
        assert score >= 90

    def test_exam_all_high(self):
        score = self.cs.compute_exam_score(mid1=85, mid2=90, mid3=88)
        assert score == 100.0

    def test_exam_all_low(self):
        score = self.cs.compute_exam_score(mid1=20, mid2=15, mid3=25)
        assert score <= 30

    def test_exam_only_one_score(self):
        """Single score with 10% penalty."""
        score = self.cs.compute_exam_score(mid1=80, mid2=None, mid3=None)
        assert 60 <= score <= 100

    def test_exam_no_scores(self):
        """No exam data returns neutral 50."""
        score = self.cs.compute_exam_score()
        assert score == 50.0

    def test_exam_two_scores(self):
        """When only 2 scores provided, both are used (no best-of-3 needed)."""
        score = self.cs.compute_exam_score(mid1=70, mid2=80, mid3=None)
        assert score >= 70

    # ── compute_credibility_score (overall) ─────────────────────

    def test_credibility_score_structure(self):
        """FR-07: Verify return structure matches 5-factor model."""
        result = self.cs.compute_credibility_score(
            delta_t_values=[3600, 7200, -1800],
            variance_value=5000,
            submitted_count=3,
            total_assignments=5,
            attendance_pct=85.0,
            mid1=70, mid2=65, mid3=80,
        )
        assert "overall_score" in result
        assert "tier" in result
        assert "components" in result
        assert 0 <= result["overall_score"] <= 100
        # Verify all 5 components present
        assert "delta_t_consistency" in result["components"]
        assert "variance_stability" in result["components"]
        assert "completion_rate" in result["components"]
        assert "attendance" in result["components"]
        assert "exam_performance" in result["components"]

    def test_credibility_tier_high(self):
        """FR-10: Score ≥ 85 → excellent tier."""
        result = self.cs.compute_credibility_score(
            delta_t_values=[86400] * 10,  # All 24h early
            variance_value=0,
            submitted_count=10,
            total_assignments=10,
            attendance_pct=98.0,
            mid1=90, mid2=85, mid3=92,
        )
        assert result["tier"] == "excellent"

    def test_credibility_tier_critical(self):
        """FR-10: Score < 30 → critical tier."""
        result = self.cs.compute_credibility_score(
            delta_t_values=[-86400] * 3,  # All 24h late
            variance_value=500000,
            submitted_count=3,
            total_assignments=10,
            attendance_pct=30.0,
            mid1=15, mid2=10, mid3=20,
        )
        assert result["tier"] in ("critical", "warning")

    def test_credibility_weights_sum_to_one(self):
        """FR-07: All 5 weights must sum to 1.0."""
        total_weight = (
            self.cs.weight_delta_t + self.cs.weight_variance
            + self.cs.weight_completion + self.cs.weight_attendance
            + self.cs.weight_exam
        )
        assert abs(total_weight - 1.0) < 0.001

    # ── check_policy_triggers ───────────────────────────────────

    def test_recognition_trigger(self):
        """FR-11: Score improving by >15 should trigger recognition."""
        events = self.cs.check_policy_triggers(current_score=70, previous_score=50)
        types = [e["policy_type"] for e in events]
        assert "recognition" in types

    def test_intervention_trigger(self):
        """FR-12: Score < 30 should trigger intervention."""
        events = self.cs.check_policy_triggers(current_score=25, previous_score=50)
        types = [e["policy_type"] for e in events]
        assert "intervention_required" in types
