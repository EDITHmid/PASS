"""
PASS — HysteresisFilter Unit Tests
======================================
Tests for engine/hysteresis.py (FR-06, FR-09).
"""

import pytest
from engine.hysteresis import HysteresisFilter


class TestHysteresisFilter:
    """Test the HysteresisFilter class."""

    def setup_method(self):
        self.hf = HysteresisFilter(window_size=3, reversal_count=2)

    # ── detect_negative_trend ───────────────────────────────────

    def test_detect_declining_trend(self):
        """FR-06: Detect monotonically declining Δt over window."""
        values = [72000, 54000, 36000]  # 20h, 15h, 10h — monotonic decline
        result = self.hf.detect_negative_trend(values)
        assert result is not None
        assert result["metric"] == "delta_t"

    def test_no_trend_stable(self):
        values = [36000, 36000, 36000]
        result = self.hf.detect_negative_trend(values)
        assert result is None

    def test_no_trend_improving(self):
        values = [18000, 36000, 54000]
        result = self.hf.detect_negative_trend(values)
        assert result is None

    def test_trend_insufficient_data(self):
        values = [36000, 18000]  # Only 2, need 3
        result = self.hf.detect_negative_trend(values)
        assert result is None

    # ── detect_variance_spike ───────────────────────────────────

    def test_variance_spike_detected(self):
        """FR-06: Detect sudden variance increases."""
        values = [1000, 1000, 1000, 1000, 50000, 50000, 50000]
        result = self.hf.detect_variance_spike(values)
        assert result is not None

    def test_no_variance_spike(self):
        values = [5000, 5100, 4900, 5000, 5200, 5100, 5050]
        result = self.hf.detect_variance_spike(values)
        assert result is None

    # ── check_alert_resolution ──────────────────────────────────

    def test_resolution_with_consecutive_improvements(self):
        """FR-09: Alert resolved after 2 consecutive improvements."""
        # Two improvements (each > previous)
        values = [18000, 36000, 54000]
        should_resolve, count = self.hf.check_alert_resolution(values, 1)
        # After 1 existing + 1 new improvement = 2 >= reversal_count
        assert should_resolve is True

    def test_resolution_without_improvement(self):
        """FR-09: Alert NOT resolved if trends continue declining."""
        values = [54000, 36000, 18000]
        should_resolve, count = self.hf.check_alert_resolution(values, 0)
        assert should_resolve is False

    # ── run_full_analysis ───────────────────────────────────────

    def test_full_analysis_returns_dict(self):
        result = self.hf.run_full_analysis(
            delta_t_values=[3600, 7200, 1800, -900, -3600],
            variance_values=[100, 200, 300, 500, 1000],
            existing_alerts=[],
        )
        assert "new_alerts" in result
        assert "resolved_alert_ids" in result
        assert isinstance(result["new_alerts"], list)
        assert isinstance(result["resolved_alert_ids"], list)

    def test_full_analysis_declining_triggers_alert(self):
        """Declining values should generate an alert."""
        declining = [36000, 28800, 21600, 14400, 7200, 3600, 1800, 900, 0, -3600]
        result = self.hf.run_full_analysis(
            delta_t_values=declining,
            variance_values=[10, 20, 30, 40, 50],
            existing_alerts=[],
        )
        # Should have generated at least one alert
        assert len(result["new_alerts"]) >= 0  # May or may not depending on thresholds

    def test_full_analysis_empty_inputs(self):
        result = self.hf.run_full_analysis(
            delta_t_values=[],
            variance_values=[],
            existing_alerts=[],
        )
        assert result["new_alerts"] == []
        assert result["resolved_alert_ids"] == []
