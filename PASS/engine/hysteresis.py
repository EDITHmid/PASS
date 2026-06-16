"""
PASS Hysteresis Trend Filter
===============================
Implements FR-08, FR-09, FR-10 from the PRD.

The hysteresis filter is the key innovation that eliminates alert fatigue
by requiring sustained negative trends before generating warnings.

Logic:
  - An alert is generated ONLY when a negative trend persists for N consecutive
    assignments (Confidence Window).
  - A single improvement does NOT cancel an active alert.
  - It requires M consecutive improvements to resolve an alert.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple


class HysteresisFilter:
    """
    Hysteresis-based trend detection filter.

    Suppresses noisy one-off alerts and confirms only statistically sustained
    negative trends, dramatically reducing false positives (target: 60% reduction).
    """

    def __init__(self, window_size: int = 3, reversal_count: int = 2):
        """
        Initialize the hysteresis filter.

        Args:
            window_size: Number of consecutive worsening assignments to confirm
                         a negative trend (Confidence Window). Default: 3 (FR-08).
            reversal_count: Number of consecutive improvements required to resolve
                            an active alert. Default: 2 (FR-09).
        """
        self.window_size = window_size
        self.reversal_count = reversal_count

    def detect_negative_trend(
        self, delta_t_values: List[float]
    ) -> Optional[Dict]:
        """
        Detect if the most recent submissions show a confirmed negative trend.

        A negative trend is confirmed when Δt monotonically worsens over the
        full confidence window.

        Args:
            delta_t_values: Chronologically ordered list of Δt values (seconds).

        Returns:
            Alert dictionary if trend is confirmed, None otherwise.
        """
        if len(delta_t_values) < self.window_size:
            return None

        # Extract the confidence window
        window = delta_t_values[-self.window_size:]

        # Check for monotonic decline (each Δt worse than the previous)
        is_declining = all(
            window[i] < window[i - 1] for i in range(1, len(window))
        )

        if not is_declining:
            return None

        # Compute percentage change across the window
        if abs(window[0]) < 1e-10:
            pct_change = -100.0
        else:
            pct_change = ((window[-1] - window[0]) / abs(window[0])) * 100

        # Determine severity based on magnitude
        severity = self._classify_severity(pct_change)

        # Generate plain-English description (FR-10)
        description = self._generate_description(
            pct_change=pct_change,
            window_size=self.window_size,
            latest_hours=window[-1] / 3600,
            metric="delta_t",
        )

        return {
            "alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}",
            "metric": "delta_t",
            "pct_change": round(pct_change, 2),
            "window_size": self.window_size,
            "severity": severity,
            "description": description,
            "window_values": [round(v / 3600, 2) for v in window],
        }

    def detect_variance_spike(
        self, variance_values: List[float], threshold_multiplier: float = 2.0
    ) -> Optional[Dict]:
        """
        Detect if variance stability has spiked, indicating erratic behavior.

        Args:
            variance_values: Chronologically ordered variance stability values.
            threshold_multiplier: Spike detected when latest > mean * multiplier.

        Returns:
            Alert dictionary if variance spike is confirmed, None otherwise.
        """
        if len(variance_values) < self.window_size + 1:
            return None

        # Compare recent window to historical average
        historical = variance_values[:-self.window_size]
        recent = variance_values[-self.window_size:]

        if not historical:
            return None

        hist_mean = sum(historical) / len(historical)

        if hist_mean < 1e-10:
            return None

        # Check if recent values are consistently elevated
        is_elevated = all(v > hist_mean * threshold_multiplier for v in recent)

        if not is_elevated:
            return None

        recent_mean = sum(recent) / len(recent)
        pct_change = ((recent_mean - hist_mean) / hist_mean) * 100

        severity = self._classify_severity(-abs(pct_change))

        description = self._generate_description(
            pct_change=pct_change,
            window_size=self.window_size,
            latest_hours=None,
            metric="variance",
        )

        return {
            "alert_id": f"ALT-{uuid.uuid4().hex[:8].upper()}",
            "metric": "variance",
            "pct_change": round(pct_change, 2),
            "window_size": self.window_size,
            "severity": severity,
            "description": description,
        }

    def check_alert_resolution(
        self,
        delta_t_values: List[float],
        consecutive_improvements: int,
    ) -> Tuple[bool, int]:
        """
        Check if an active alert should be resolved (FR-09).

        A trend reversal (single improved submission) does NOT immediately cancel
        an alert. It requires `reversal_count` consecutive improvements.

        Args:
            delta_t_values: Recent Δt values (at least 2).
            consecutive_improvements: Current count of consecutive improvements.

        Returns:
            Tuple of (should_resolve: bool, updated_improvement_count: int).
        """
        if len(delta_t_values) < 2:
            return False, consecutive_improvements

        # Check if the latest submission improved over the previous
        if delta_t_values[-1] > delta_t_values[-2]:
            consecutive_improvements += 1
        else:
            consecutive_improvements = 0

        should_resolve = consecutive_improvements >= self.reversal_count

        return should_resolve, consecutive_improvements

    def _classify_severity(self, pct_change: float) -> str:
        """
        Classify alert severity based on percentage change magnitude.

        Args:
            pct_change: Percentage change (negative indicates worsening).

        Returns:
            Severity level: 'info', 'warning', or 'critical'.
        """
        abs_change = abs(pct_change)
        if abs_change >= 50:
            return "critical"
        elif abs_change >= 25:
            return "warning"
        return "info"

    def _generate_description(
        self,
        pct_change: float,
        window_size: int,
        latest_hours: Optional[float],
        metric: str,
    ) -> str:
        """
        Generate a plain-English alert description (FR-10).

        Every alert must include a human-readable rationale — never opaque scores.

        Args:
            pct_change: Percentage change value.
            window_size: Number of assignments in the confidence window.
            latest_hours: Latest Δt value in hours (for delta_t alerts).
            metric: Type of metric ('delta_t' or 'variance').

        Returns:
            Plain-English alert description.
        """
        abs_change = abs(round(pct_change, 1))

        if metric == "delta_t":
            if latest_hours is not None and latest_hours < 0:
                timing = f"The most recent submission was {abs(round(latest_hours, 1))} hours late."
            elif latest_hours is not None:
                timing = f"The most recent submission was {round(latest_hours, 1)} hours before the deadline."
            else:
                timing = ""

            return (
                f"Submission timing has worsened by {abs_change}% over the last "
                f"{window_size} consecutive assignments, indicating a sustained "
                f"decline in engagement. {timing} This pattern may indicate "
                f"increasing academic difficulty or disengagement."
            )
        else:  # variance
            return (
                f"Submission pattern variance has increased by {abs_change}% over the "
                f"last {window_size} assignments compared to the student's historical "
                f"average. Erratic timing patterns often precede sustained performance "
                f"decline and may indicate stress or burnout."
            )

    def run_full_analysis(
        self,
        delta_t_values: List[float],
        variance_values: List[float],
        existing_alerts: List[Dict],
    ) -> Dict:
        """
        Run complete hysteresis analysis for a student.

        Args:
            delta_t_values: All Δt values in chronological order.
            variance_values: All variance stability values in chronological order.
            existing_alerts: List of currently active alert dictionaries.

        Returns:
            Analysis result with new alerts and resolution updates.
        """
        new_alerts = []
        resolved_alerts = []

        # Check for new Δt trend alert
        dt_alert = self.detect_negative_trend(delta_t_values)
        if dt_alert:
            # Only create if no existing unresolved delta_t alert
            has_active_dt = any(
                a.get("metric") == "delta_t" and not a.get("resolved", False)
                for a in existing_alerts
            )
            if not has_active_dt:
                new_alerts.append(dt_alert)

        # Check for variance spike alert
        var_alert = self.detect_variance_spike(variance_values)
        if var_alert:
            has_active_var = any(
                a.get("metric") == "variance" and not a.get("resolved", False)
                for a in existing_alerts
            )
            if not has_active_var:
                new_alerts.append(var_alert)

        # Check for alert resolution
        for alert in existing_alerts:
            if alert.get("resolved", False):
                continue
            improvements = alert.get("consecutive_improvements", 0)
            should_resolve, new_count = self.check_alert_resolution(
                delta_t_values, improvements
            )
            if should_resolve:
                resolved_alerts.append(alert.get("alert_id"))
            else:
                alert["consecutive_improvements"] = new_count

        return {
            "new_alerts": new_alerts,
            "resolved_alert_ids": resolved_alerts,
            "total_active": len(existing_alerts)
            - len(resolved_alerts)
            + len(new_alerts),
        }
