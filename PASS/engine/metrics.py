"""
PASS Metric Computation Engine
================================
Implements FR-05, FR-06, FR-07 from the PRD.

Computes:
  - Δt (Submission Velocity): deadline_timestamp − submission_timestamp
  - Variance Stability: Rolling population std deviation of Δt values
"""

import numpy as np
from typing import List, Dict, Optional, Tuple


class MetricComputer:
    """
    Core metric computation engine for PASS.

    Computes the two foundational metrics that drive the entire system:
    1. Submission Velocity (Δt) — temporal distance between submission and deadline
    2. Variance Stability — rolling std deviation measuring consistency
    """

    def __init__(self, rolling_window: int = 5):
        """
        Initialize the metric computer.

        Args:
            rolling_window: Number of recent assignments for variance computation.
                            Default N=5 as specified in FR-06.
        """
        self.rolling_window = rolling_window

    @staticmethod
    def compute_delta_t(submission_timestamp: float, deadline_timestamp: float) -> float:
        """
        Compute Submission Velocity (Δt) as per FR-05.

        Δt = deadline_timestamp − submission_timestamp

        Positive values indicate early submissions.
        Negative values indicate late submissions.

        Args:
            submission_timestamp: UNIX timestamp of submission.
            deadline_timestamp: UNIX timestamp of deadline.

        Returns:
            Δt in seconds (positive = early, negative = late).
        """
        return deadline_timestamp - submission_timestamp

    @staticmethod
    def delta_t_to_hours(delta_t_seconds: float) -> float:
        """Convert Δt from seconds to hours for readability."""
        return delta_t_seconds / 3600.0

    @staticmethod
    def classify_submission(delta_t_seconds: float) -> str:
        """
        Classify a submission based on Δt value.

        Args:
            delta_t_seconds: Δt in seconds.

        Returns:
            'on-time' if early/on time, 'late' if after deadline.
        """
        if delta_t_seconds >= 0:
            return "on-time"
        return "late"

    def compute_variance_stability(self, delta_t_values: List[float]) -> float:
        """
        Compute Variance Stability index as per FR-06.

        Uses population standard deviation of the last N Δt values.
        High variance = erratic submission behavior (potential burnout precursor).

        Args:
            delta_t_values: Ordered list of Δt values (most recent last).

        Returns:
            Population standard deviation of the rolling window.
            Returns 0.0 if insufficient data.
        """
        if len(delta_t_values) < 2:
            return 0.0

        # Use only the last N values (rolling window)
        window = delta_t_values[-self.rolling_window:]
        return float(np.std(window, ddof=0))  # Population std deviation

    def compute_rolling_variance_series(
        self, delta_t_values: List[float]
    ) -> List[Optional[float]]:
        """
        Compute a time-series of rolling variance stability values.

        Useful for charting variance trends over time.

        Args:
            delta_t_values: Full ordered list of Δt values.

        Returns:
            List of variance values (None where insufficient data exists).
        """
        result = []
        for i in range(len(delta_t_values)):
            if i < 1:
                result.append(None)
            else:
                start = max(0, i + 1 - self.rolling_window)
                window = delta_t_values[start:i + 1]
                result.append(float(np.std(window, ddof=0)))
        return result

    def compute_trend_direction(
        self, delta_t_values: List[float], window: int = 3
    ) -> Dict:
        """
        Analyze the direction and magnitude of Δt trend.

        Args:
            delta_t_values: Ordered list of Δt values.
            window: Number of recent values to analyze.

        Returns:
            Dictionary with trend analysis:
            {
                'direction': 'improving' | 'worsening' | 'stable',
                'pct_change': float,
                'is_monotonic_decline': bool,
                'values': list
            }
        """
        if len(delta_t_values) < window:
            return {
                "direction": "stable",
                "pct_change": 0.0,
                "is_monotonic_decline": False,
                "values": delta_t_values,
            }

        recent = delta_t_values[-window:]

        # Compute percentage change from first to last in window
        if abs(recent[0]) < 1e-10:
            pct_change = 0.0 if abs(recent[-1]) < 1e-10 else -100.0
        else:
            pct_change = ((recent[-1] - recent[0]) / abs(recent[0])) * 100

        # Check for monotonic decline (each value worse than previous)
        is_monotonic_decline = all(
            recent[i] < recent[i - 1] for i in range(1, len(recent))
        )

        # Determine direction
        if pct_change < -10:
            direction = "worsening"
        elif pct_change > 10:
            direction = "improving"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "pct_change": round(pct_change, 2),
            "is_monotonic_decline": is_monotonic_decline,
            "values": recent,
        }

    def compute_student_summary(
        self, delta_t_values: List[float]
    ) -> Dict:
        """
        Compute a comprehensive summary of a student's metrics.

        Args:
            delta_t_values: All Δt values in chronological order.

        Returns:
            Complete metric summary dictionary.
        """
        if not delta_t_values:
            return {
                "total_submissions": 0,
                "mean_delta_t": 0.0,
                "median_delta_t": 0.0,
                "current_variance": 0.0,
                "on_time_rate": 0.0,
                "trend": self.compute_trend_direction([]),
                "latest_delta_t": 0.0,
            }

        dt_hours = [self.delta_t_to_hours(dt) for dt in delta_t_values]
        on_time = sum(1 for dt in delta_t_values if dt >= 0)

        return {
            "total_submissions": len(delta_t_values),
            "mean_delta_t": round(float(np.mean(dt_hours)), 2),
            "median_delta_t": round(float(np.median(dt_hours)), 2),
            "current_variance": round(self.compute_variance_stability(delta_t_values), 2),
            "on_time_rate": round((on_time / len(delta_t_values)) * 100, 1),
            "trend": self.compute_trend_direction(delta_t_values),
            "latest_delta_t": round(self.delta_t_to_hours(delta_t_values[-1]), 2),
        }
