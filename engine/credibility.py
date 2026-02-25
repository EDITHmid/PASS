"""
PASS Credibility Scoring Engine
=================================
Implements FR-11, FR-12, FR-13 from the PRD.

Credibility Score (0–100) is computed from:
  - Δt Consistency (50%): Measures how consistently early submissions are.
  - Variance Stability (30%): Lower variance = more consistent = higher score.
  - Assignment Completion Rate (20%): Percentage of assignments submitted.

Scores crossing configurable thresholds trigger automated policy events.
"""

import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone


class CredibilityScorer:
    """
    Computes and manages student Credibility Scores.

    The score functions as both a reliability index and a policy engine —
    rewarding consistent students with automated perks (attendance flexibility, etc.).
    """

    def __init__(
        self,
        weight_delta_t: float = 0.50,
        weight_variance: float = 0.30,
        weight_completion: float = 0.20,
        threshold_high: float = 85.0,
        threshold_warning: float = 50.0,
        threshold_critical: float = 30.0,
    ):
        """
        Initialize the credibility scorer.

        Args:
            weight_delta_t: Weight for Δt consistency component (FR-12: 50%).
            weight_variance: Weight for variance stability component (FR-12: 30%).
            weight_completion: Weight for completion rate component (FR-12: 20%).
            threshold_high: Score threshold for automated perks (FR-13: ≥85).
            threshold_warning: Score threshold for warning state.
            threshold_critical: Score threshold for critical alerts.
        """
        assert abs(weight_delta_t + weight_variance + weight_completion - 1.0) < 1e-6, \
            "Weights must sum to 1.0"

        self.weight_delta_t = weight_delta_t
        self.weight_variance = weight_variance
        self.weight_completion = weight_completion
        self.threshold_high = threshold_high
        self.threshold_warning = threshold_warning
        self.threshold_critical = threshold_critical

    def compute_delta_t_score(self, delta_t_values: List[float]) -> float:
        """
        Compute the Δt consistency sub-score (0–100).

        Higher scores for students who consistently submit early.
        Uses the mean Δt normalized against a reference window.

        Args:
            delta_t_values: List of Δt values in seconds.

        Returns:
            Score from 0 to 100.
        """
        if not delta_t_values:
            return 50.0  # Neutral default for no data

        # Convert to hours for more intuitive thresholds
        hours = [dt / 3600.0 for dt in delta_t_values]
        mean_hours = float(np.mean(hours))

        # Scoring logic:
        # ≥24h early → 100 points
        # 0h (exactly on time) → 60 points
        # ≤-24h late → 0 points
        # Linear interpolation between these anchors
        if mean_hours >= 24:
            score = 100.0
        elif mean_hours >= 0:
            # 0h → 60, 24h → 100
            score = 60.0 + (mean_hours / 24.0) * 40.0
        elif mean_hours >= -24:
            # -24h → 0, 0h → 60
            score = max(0.0, 60.0 + (mean_hours / 24.0) * 60.0)
        else:
            score = 0.0

        # Penalty for recent decline: compare last 3 to overall
        if len(hours) >= 3:
            recent_mean = float(np.mean(hours[-3:]))
            if recent_mean < mean_hours * 0.7:  # >30% decline recently
                score *= 0.85  # 15% penalty

        return round(min(100.0, max(0.0, score)), 2)

    def compute_variance_score(
        self, variance_value: float, historical_variances: Optional[List[float]] = None
    ) -> float:
        """
        Compute the variance stability sub-score (0–100).

        Lower variance = more consistent = higher score.
        Normalized against historical variance distribution.

        Args:
            variance_value: Current variance stability value.
            historical_variances: List of past variance values for context.

        Returns:
            Score from 0 to 100.
        """
        if variance_value == 0:
            return 100.0  # Perfect consistency

        # Convert variance from seconds to hours for scoring
        var_hours = variance_value / 3600.0

        # Scoring: variance in hours
        # 0h → 100, 6h → 70, 12h → 40, 24h → 10, >48h → 0
        if var_hours <= 1:
            score = 100.0
        elif var_hours <= 6:
            score = 100.0 - (var_hours - 1) * 6.0  # 100 → 70
        elif var_hours <= 12:
            score = 70.0 - (var_hours - 6) * 5.0  # 70 → 40
        elif var_hours <= 24:
            score = 40.0 - (var_hours - 12) * 2.5  # 40 → 10
        else:
            score = max(0.0, 10.0 - (var_hours - 24) * 0.42)

        # Contextual adjustment: if variance is improving relative to history
        if historical_variances and len(historical_variances) >= 3:
            hist_mean = float(np.mean(historical_variances[-3:]))
            if hist_mean > 0 and variance_value < hist_mean * 0.8:
                score = min(100.0, score * 1.1)  # 10% bonus for improvement

        return round(min(100.0, max(0.0, score)), 2)

    def compute_completion_score(
        self, submitted_count: int, total_assignments: int
    ) -> float:
        """
        Compute the completion rate sub-score (0–100).

        Simple percentage of assignments submitted out of total assigned.

        Args:
            submitted_count: Number of assignments submitted.
            total_assignments: Total number of assignments in the course.

        Returns:
            Score from 0 to 100.
        """
        if total_assignments == 0:
            return 50.0  # Neutral default

        rate = submitted_count / total_assignments
        # Non-linear: penalize missing assignments more heavily
        # 100% → 100, 90% → 85, 80% → 70, 70% → 50, <60% → linear to 0
        if rate >= 1.0:
            return 100.0
        elif rate >= 0.9:
            return 85.0 + (rate - 0.9) * 150  # 85 → 100
        elif rate >= 0.8:
            return 70.0 + (rate - 0.8) * 150  # 70 → 85
        elif rate >= 0.7:
            return 50.0 + (rate - 0.7) * 200  # 50 → 70
        else:
            return max(0.0, rate / 0.7 * 50.0)

    def compute_credibility_score(
        self,
        delta_t_values: List[float],
        variance_value: float,
        submitted_count: int,
        total_assignments: int,
        historical_variances: Optional[List[float]] = None,
    ) -> Dict:
        """
        Compute the composite Credibility Score (FR-11, FR-12).

        Args:
            delta_t_values: All Δt values for the student.
            variance_value: Current variance stability value.
            submitted_count: Number of assignments submitted.
            total_assignments: Total number of assignments.
            historical_variances: Past variance values for contextual scoring.

        Returns:
            Dictionary with overall score and component breakdown.
        """
        dt_score = self.compute_delta_t_score(delta_t_values)
        var_score = self.compute_variance_score(variance_value, historical_variances)
        comp_score = self.compute_completion_score(submitted_count, total_assignments)

        # Weighted composite
        overall = (
            dt_score * self.weight_delta_t
            + var_score * self.weight_variance
            + comp_score * self.weight_completion
        )
        overall = round(min(100.0, max(0.0, overall)), 2)

        # Determine tier
        if overall >= self.threshold_high:
            tier = "excellent"
            tier_label = "High Credibility"
        elif overall >= self.threshold_warning:
            tier = "good"
            tier_label = "Satisfactory"
        elif overall >= self.threshold_critical:
            tier = "warning"
            tier_label = "Needs Attention"
        else:
            tier = "critical"
            tier_label = "At Risk"

        return {
            "overall_score": overall,
            "tier": tier,
            "tier_label": tier_label,
            "components": {
                "delta_t_consistency": {
                    "score": dt_score,
                    "weight": self.weight_delta_t,
                    "weighted": round(dt_score * self.weight_delta_t, 2),
                },
                "variance_stability": {
                    "score": var_score,
                    "weight": self.weight_variance,
                    "weighted": round(var_score * self.weight_variance, 2),
                },
                "completion_rate": {
                    "score": comp_score,
                    "weight": self.weight_completion,
                    "weighted": round(comp_score * self.weight_completion, 2),
                },
            },
        }

    def check_policy_triggers(
        self, current_score: float, previous_score: float
    ) -> List[Dict]:
        """
        Check if score changes should trigger automated policy events (FR-13).

        Args:
            current_score: The newly computed credibility score.
            previous_score: The previous credibility score.

        Returns:
            List of policy event dictionaries to create.
        """
        events = []
        now = datetime.now(timezone.utc)

        # Crossed above high threshold → attendance waiver
        if current_score >= self.threshold_high and previous_score < self.threshold_high:
            events.append({
                "policy_type": "attendance_waiver",
                "description": (
                    f"Credibility Score has reached {current_score:.1f}, exceeding the "
                    f"{self.threshold_high} threshold. Automatic attendance flexibility "
                    f"waiver has been granted for this semester."
                ),
                "triggered_at": now,
                "expires_at": now + timedelta(days=90),
            })

        # Score improved significantly (>15 points) → recognition
        if current_score - previous_score > 15:
            events.append({
                "policy_type": "recognition",
                "description": (
                    f"Credibility Score improved significantly from {previous_score:.1f} "
                    f"to {current_score:.1f}. This student demonstrates notable "
                    f"improvement in academic engagement."
                ),
                "triggered_at": now,
                "expires_at": None,
            })

        # Dropped below critical → requires attention
        if current_score < self.threshold_critical and previous_score >= self.threshold_critical:
            events.append({
                "policy_type": "intervention_required",
                "description": (
                    f"Credibility Score has dropped to {current_score:.1f}, below the "
                    f"critical threshold of {self.threshold_critical}. Immediate "
                    f"instructor intervention is recommended."
                ),
                "triggered_at": now,
                "expires_at": None,
            })

        return events
