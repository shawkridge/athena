"""Self-reflection system for metacognitive monitoring and calibration."""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from statistics import mean, stdev

from .models import ConfidenceCalibration


class SelfReflectionSystem:
    """
    Tracks confidence calibration, error attribution, and performance trends.

    Capabilities:
    - Compare reported confidence vs actual accuracy
    - Identify overconfidence and underconfidence patterns
    - Track and analyze errors
    - Measure reasoning quality
    - Detect systematic biases
    - Generate self-assessment reports
    """

    def __init__(self, db_path: str):
        """Initialize reflection system."""
        self.db_path = db_path

    def record_confidence(
        self,
        project_id: int,
        memory_id: int,
        confidence_reported: float,
        confidence_actual: float,
        memory_type: str,
    ) -> bool:
        """
        Record confidence calibration data.

        Args:
            project_id: Project ID
            memory_id: Memory ID
            confidence_reported: User-reported or inferred confidence (0-1)
            confidence_actual: Actual accuracy/correctness (0-1)
            memory_type: Type of memory ('semantic', 'episodic', 'procedural', etc)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            calibration_error = abs(confidence_reported - confidence_actual)

            cursor.execute(
                """
                INSERT INTO metacognition_confidence
                (project_id, memory_id, confidence_reported, confidence_actual, memory_type, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    memory_id,
                    confidence_reported,
                    confidence_actual,
                    memory_type,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return True

    def calibrate_confidence(self, project_id: int) -> Dict:
        """
        Calculate overall confidence calibration metrics.

        Returns:
            Dictionary with:
            - mean_reported: Average reported confidence
            - mean_actual: Average actual accuracy
            - calibration_error: Mean absolute error
            - is_overconfident: True if reported > actual
            - is_underconfident: True if actual > reported
            - calibration_status: 'well_calibrated', 'overconfident', 'underconfident'
            - adjustment_factor: Scale factor to improve calibration
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT confidence_reported, confidence_actual
                FROM metacognition_confidence
                WHERE project_id = ?
                """,
                (project_id,),
            )
            rows = cursor.fetchall()

        if not rows:
            return {
                "mean_reported": 0.0,
                "mean_actual": 0.0,
                "calibration_error": 0.0,
                "is_overconfident": False,
                "is_underconfident": False,
                "calibration_status": "no_data",
                "adjustment_factor": 1.0,
            }

        reported = [r[0] for r in rows]
        actual = [r[1] for r in rows]

        mean_reported = mean(reported)
        mean_actual = mean(actual)
        calibration_error = mean(
            [abs(r - a) for r, a in zip(reported, actual)]
        )

        # Determine calibration status
        diff = mean_reported - mean_actual
        if abs(diff) < 0.05:
            calibration_status = "well_calibrated"
            adjustment_factor = 1.0
        elif diff > 0.05:
            calibration_status = "overconfident"
            adjustment_factor = mean_actual / mean_reported if mean_reported > 0 else 1.0
        else:
            calibration_status = "underconfident"
            adjustment_factor = mean_actual / mean_reported if mean_reported > 0 else 1.0

        return {
            "mean_reported": mean_reported,
            "mean_actual": mean_actual,
            "calibration_error": calibration_error,
            "is_overconfident": diff > 0.05,
            "is_underconfident": diff < -0.05,
            "calibration_status": calibration_status,
            "adjustment_factor": adjustment_factor,
        }

    def track_error(
        self,
        project_id: int,
        error_type: str,
        description: str,
        memory_id: Optional[int] = None,
        recovery_action: Optional[str] = None,
    ) -> bool:
        """
        Track an error for analysis.

        Args:
            project_id: Project ID
            error_type: Type of error ('retrieval', 'consolidation', 'reasoning', 'bias')
            description: Description of the error
            memory_id: Related memory ID (optional)
            recovery_action: How the error was recovered (optional)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Create a record in the confidence table with error context
            cursor.execute(
                """
                INSERT INTO metacognition_confidence
                (project_id, memory_id, memory_type, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (project_id, memory_id, f"error:{error_type}", datetime.now().isoformat()),
            )
            conn.commit()
            return True

    def get_success_rates_by_type(self, project_id: int) -> Dict[str, float]:
        """
        Calculate success rates broken down by memory type.

        Returns:
            Dictionary mapping memory type to success rate (0-1)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT memory_type, confidence_actual
                FROM metacognition_confidence
                WHERE project_id = ? AND memory_type NOT LIKE 'error:%'
                """,
                (project_id,),
            )
            rows = cursor.fetchall()

        if not rows:
            return {}

        # Group by memory type
        types_data = {}
        for mem_type, actual_confidence in rows:
            if mem_type not in types_data:
                types_data[mem_type] = []
            types_data[mem_type].append(actual_confidence)

        # Calculate success rate (mean actual confidence) for each type
        success_rates = {}
        for mem_type, confidences in types_data.items():
            success_rates[mem_type] = mean(confidences) if confidences else 0.0

        return success_rates

    def analyze_reasoning_quality(self, project_id: int) -> Dict:
        """
        Assess overall reasoning quality.

        Returns:
            Dictionary with:
            - accuracy: Overall accuracy (mean actual confidence)
            - consistency: Standard deviation of accuracy (lower is more consistent)
            - reliability: How reliable predictions are
            - quality_score: Composite quality score (0-1)
            - assessment: 'excellent', 'good', 'fair', 'poor'
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT confidence_actual
                FROM metacognition_confidence
                WHERE project_id = ? AND memory_type NOT LIKE 'error:%'
                """,
                (project_id,),
            )
            rows = cursor.fetchall()

        if not rows:
            return {
                "accuracy": 0.0,
                "consistency": 0.0,
                "reliability": 0.0,
                "quality_score": 0.0,
                "assessment": "no_data",
            }

        actual_confidences = [r[0] for r in rows]
        accuracy = mean(actual_confidences)

        # Consistency: lower stdev = higher consistency
        if len(actual_confidences) > 1:
            consistency = stdev(actual_confidences)
        else:
            consistency = 0.0

        # Reliability: accuracy * (1 - normalized_stdev)
        reliability = accuracy * (1.0 - min(consistency, 1.0))

        # Quality score: balance of accuracy and consistency
        quality_score = (accuracy * 0.7) + ((1.0 - consistency) * 0.3)

        # Assessment
        if quality_score >= 0.85:
            assessment = "excellent"
        elif quality_score >= 0.7:
            assessment = "good"
        elif quality_score >= 0.5:
            assessment = "fair"
        else:
            assessment = "poor"

        return {
            "accuracy": accuracy,
            "consistency": consistency,
            "reliability": reliability,
            "quality_score": quality_score,
            "assessment": assessment,
        }

    def detect_systematic_bias(self, project_id: int) -> Dict:
        """
        Identify systematic biases in decision-making.

        Returns:
            Dictionary with detected biases:
            - overconfidence_bias: Tendency to be overconfident
            - underconfidence_bias: Tendency to be underconfident
            - type_bias: Biases specific to memory types
            - severity: 'none', 'mild', 'moderate', 'severe'
            - recommendations: Suggested corrective actions
        """
        calibration = self.calibrate_confidence(project_id)
        success_by_type = self.get_success_rates_by_type(project_id)

        biases = {
            "overconfidence_bias": calibration["is_overconfident"],
            "underconfidence_bias": calibration["is_underconfident"],
            "type_bias": {},
            "severity": "none",
            "recommendations": [],
        }

        # Analyze per-type biases
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT memory_type, confidence_reported, confidence_actual
                FROM metacognition_confidence
                WHERE project_id = ? AND memory_type NOT LIKE 'error:%'
                """,
                (project_id,),
            )
            rows = cursor.fetchall()

        for mem_type, reported, actual in rows:
            if mem_type not in biases["type_bias"]:
                biases["type_bias"][mem_type] = {
                    "mean_diff": 0.0,
                    "bias_direction": "neutral",
                }

        # Calculate mean difference per type
        type_diffs = {}
        for mem_type, reported, actual in rows:
            if mem_type not in type_diffs:
                type_diffs[mem_type] = []
            type_diffs[mem_type].append(reported - actual)

        for mem_type, diffs in type_diffs.items():
            mean_diff = mean(diffs) if diffs else 0.0
            if mean_diff > 0.1:
                bias_direction = "overconfident"
            elif mean_diff < -0.1:
                bias_direction = "underconfident"
            else:
                bias_direction = "neutral"

            biases["type_bias"][mem_type] = {
                "mean_diff": mean_diff,
                "bias_direction": bias_direction,
            }

        # Determine overall severity
        calibration_error = calibration["calibration_error"]
        if calibration_error > 0.3:
            biases["severity"] = "severe"
            biases["recommendations"].append(
                "Recalibrate confidence estimates; current error is very high"
            )
        elif calibration_error > 0.2:
            biases["severity"] = "moderate"
            biases["recommendations"].append(
                "Review confidence calibration; noticeable systematic bias"
            )
        elif calibration_error > 0.1:
            biases["severity"] = "mild"

        # Add specific recommendations
        if calibration["is_overconfident"]:
            biases["recommendations"].append(
                "Be more conservative with confidence estimates"
            )
        if calibration["is_underconfident"]:
            biases["recommendations"].append("Build more confidence in correct judgments")

        return biases

    def get_performance_trends(
        self, project_id: int, hours: int = 24
    ) -> Dict:
        """
        Analyze performance trends over time.

        Returns:
            Dictionary with trend analysis:
            - trend: 'improving', 'declining', 'stable'
            - accuracy_trend: Change in accuracy
            - consistency_trend: Change in consistency
            - recent_performance: Last N results
            - historical_avg: Average performance
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cutoff_time = (
                (datetime.now() - timedelta(hours=hours)).isoformat()
            )

            cursor.execute(
                """
                SELECT confidence_actual, updated_at
                FROM metacognition_confidence
                WHERE project_id = ? AND updated_at >= ? AND memory_type NOT LIKE 'error:%'
                ORDER BY updated_at DESC
                LIMIT 20
                """,
                (project_id, cutoff_time),
            )
            recent = cursor.fetchall()

            # Get all historical data
            cursor.execute(
                """
                SELECT confidence_actual
                FROM metacognition_confidence
                WHERE project_id = ? AND memory_type NOT LIKE 'error:%'
                """,
                (project_id,),
            )
            all_data = cursor.fetchall()

        if not recent:
            return {
                "trend": "no_data",
                "accuracy_trend": 0.0,
                "consistency_trend": 0.0,
                "recent_performance": [],
                "historical_avg": 0.0,
            }

        recent_accuracies = [r[0] for r in recent]
        recent_avg = mean(recent_accuracies)

        historical_accuracies = [r[0] for r in all_data]
        historical_avg = mean(historical_accuracies) if historical_accuracies else 0.0

        accuracy_trend = recent_avg - historical_avg

        # Determine trend direction
        if accuracy_trend > 0.05:
            trend = "improving"
        elif accuracy_trend < -0.05:
            trend = "declining"
        else:
            trend = "stable"

        # Consistency trend
        if len(recent_accuracies) > 1:
            recent_consistency = stdev(recent_accuracies)
        else:
            recent_consistency = 0.0

        if len(historical_accuracies) > 1:
            historical_consistency = stdev(historical_accuracies)
        else:
            historical_consistency = 0.0

        consistency_trend = recent_consistency - historical_consistency

        return {
            "trend": trend,
            "accuracy_trend": accuracy_trend,
            "consistency_trend": consistency_trend,
            "recent_performance": recent_accuracies,
            "historical_avg": historical_avg,
            "recent_avg": recent_avg,
        }

    def generate_self_report(self, project_id: int) -> Dict:
        """
        Generate comprehensive self-assessment report.

        Returns:
            Dictionary with complete self-reflection analysis
        """
        calibration = self.calibrate_confidence(project_id)
        reasoning_quality = self.analyze_reasoning_quality(project_id)
        bias_analysis = self.detect_systematic_bias(project_id)
        performance_trends = self.get_performance_trends(project_id)
        success_by_type = self.get_success_rates_by_type(project_id)

        summary = (
            f"Self-Assessment Report - Project {project_id}\n"
            f"Overall Assessment: {reasoning_quality['assessment'].upper()}\n"
            f"Calibration Status: {calibration['calibration_status'].upper()}\n"
            f"Performance Trend: {performance_trends['trend'].upper()}\n"
            f"Bias Severity: {bias_analysis['severity'].upper()}"
        )

        return {
            "summary": summary,
            "calibration": calibration,
            "reasoning_quality": reasoning_quality,
            "bias_analysis": bias_analysis,
            "performance_trends": performance_trends,
            "success_by_type": success_by_type,
            "timestamp": datetime.now().isoformat(),
        }
