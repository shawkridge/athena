"""Run tests on dream procedures and track results for learning."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..consolidation.dream_store import DreamStore
from ..consolidation.dream_models import DreamStatus, DreamTier, DreamProcedure
from ..core.database import Database
from .dream_sandbox import DreamSandbox, DreamTestResult, TestOutcome
from .synthetic_test_generator import SyntheticTestGenerator

logger = logging.getLogger(__name__)


class DreamTestRunner:
    """Run comprehensive tests on dream procedures."""

    def __init__(
        self,
        db: Optional[Database] = None,
        sandbox_timeout_seconds: int = 30,
        tests_per_dream: int = 5,
    ):
        """Initialize dream test runner.

        Args:
            db: Database instance (creates new if None)
            sandbox_timeout_seconds: Timeout per test execution
            tests_per_dream: Number of test variants per dream
        """
        self.db = db or Database()
        self.store = DreamStore(self.db)
        self.sandbox = DreamSandbox(timeout_seconds=sandbox_timeout_seconds)
        self.test_generator = SyntheticTestGenerator(seed=42)
        self.tests_per_dream = tests_per_dream

        self.test_results: List[DreamTestResult] = []
        self.dreams_tested = 0
        self.dreams_passed = 0

    async def test_tier1_dreams(self) -> Dict[str, Any]:
        """Test all Tier 1 (viable) dreams.

        Returns:
            Dictionary with testing results and statistics
        """
        # Get all Tier 1 dreams
        try:
            tier1_dreams = await self.store.get_by_tier(DreamTier.VIABLE)
        except Exception as e:
            logger.error(f"Could not retrieve Tier 1 dreams: {e}")
            return {"error": str(e), "success": False}

        logger.info(f"Testing {len(tier1_dreams)} Tier 1 dreams")

        tested_dreams = []
        for dream in tier1_dreams:
            if dream.status == DreamStatus.PENDING_TEST:
                result = await self.test_dream(dream)
                tested_dreams.append(result)

        # Calculate statistics
        stats = self._calculate_statistics()

        return {
            "success": True,
            "total_tier1_dreams": len(tier1_dreams),
            "tested_dreams": len(tested_dreams),
            "dreams_passed": self.dreams_passed,
            "dreams_failed": len(tested_dreams) - self.dreams_passed,
            "pass_rate": (
                self.dreams_passed / len(tested_dreams)
                if tested_dreams
                else 0.0
            ),
            "statistics": stats,
            "tested_dreams_details": tested_dreams,
        }

    async def test_dream(
        self,
        dream: DreamProcedure,
        variant_indices: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Test a single dream procedure.

        Args:
            dream: Dream procedure to test
            variant_indices: Specific test variants to run (None = all)

        Returns:
            Dictionary with test results
        """
        logger.info(f"Testing dream {dream.id} ({dream.dream_type})")
        self.dreams_tested += 1

        # Generate test inputs
        test_inputs = self.test_generator.generate_test_inputs(
            dream.code,
            num_variants=self.tests_per_dream,
        )

        if not test_inputs:
            logger.warning(f"Could not generate test inputs for dream {dream.id}")
            test_inputs = [{}]  # Empty input as fallback

        # Get expected output type
        expected_output_type = self.test_generator.get_expected_output_type(
            dream.code
        )

        # Run tests
        test_results = []
        all_passed = True

        for i, inputs in enumerate(test_inputs):
            if variant_indices and i not in variant_indices:
                continue

            result = await self.sandbox.execute_dream(
                dream_id=dream.id,
                code=dream.code,
                input_params=inputs,
                expected_output_type=expected_output_type,
            )

            test_results.append(result.to_dict())
            self.test_results.append(result)

            if not result.success:
                all_passed = False

        # Update dream in database
        if all_passed:
            self.dreams_passed += 1
            await self._update_dream_status(
                dream.id,
                DreamStatus.TESTED,
                "success",
                None,
            )
        else:
            failed_count = sum(
                1 for r in test_results
                if not self._parse_result_dict(r)["success"]
            )
            await self._update_dream_status(
                dream.id,
                DreamStatus.TESTED,
                "failure",
                f"{failed_count}/{len(test_results)} tests failed",
            )

        return {
            "dream_id": dream.id,
            "dream_type": dream.dream_type,
            "total_tests": len(test_results),
            "passed": all_passed,
            "test_results": test_results,
            "failure_patterns": (
                {k: v.__dict__ for k, v in self.sandbox.failure_patterns.items()}
                if not all_passed
                else {}
            ),
        }

    async def test_with_edge_cases(
        self,
        dream: DreamProcedure,
    ) -> Dict[str, Any]:
        """Test dream with edge case inputs.

        Args:
            dream: Dream procedure to test

        Returns:
            Dictionary with edge case test results
        """
        logger.info(f"Testing dream {dream.id} with edge cases")

        # Generate edge case inputs
        edge_cases = self.test_generator.generate_edge_case_inputs(dream.code)
        expected_output_type = self.test_generator.get_expected_output_type(
            dream.code
        )

        # Run edge case tests
        results = []
        for edge_case_inputs in edge_cases:
            result = await self.sandbox.execute_dream(
                dream_id=dream.id,
                code=dream.code,
                input_params=edge_case_inputs,
                expected_output_type=expected_output_type,
            )
            results.append(result.to_dict())
            self.test_results.append(result)

        return {
            "dream_id": dream.id,
            "edge_case_count": len(edge_cases),
            "results": results,
        }

    async def _update_dream_status(
        self,
        dream_id: int,
        status: DreamStatus,
        test_outcome: str,
        test_error: Optional[str],
    ) -> None:
        """Update dream status in database after testing.

        Args:
            dream_id: Dream ID
            status: New status
            test_outcome: Test outcome ("success" or "failure")
            test_error: Error message if failed
        """
        try:
            dream = await self.store.get_dream(dream_id)
            if dream:
                dream.status = status
                dream.test_outcome = test_outcome
                dream.test_error = test_error
                dream.test_timestamp = datetime.now()
                await self.store.update_dream(dream)
        except Exception as e:
            logger.error(f"Could not update dream status: {e}")

    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from all test results.

        Returns:
            Dictionary with test statistics
        """
        if not self.test_results:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "success_rate": 0.0,
                "average_execution_time_ms": 0.0,
            }

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.success)
        failed = total - passed
        avg_time = sum(r.execution_time_ms for r in self.test_results) / total

        # Outcomes breakdown
        outcomes = {}
        for result in self.test_results:
            outcome = result.test_outcome.value
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        # Error categories
        error_categories = {}
        for result in self.test_results:
            if result.error_category:
                cat = result.error_category.value
                error_categories[cat] = error_categories.get(cat, 0) + 1

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total if total > 0 else 0.0,
            "average_execution_time_ms": avg_time,
            "outcomes": outcomes,
            "error_categories": error_categories,
            "failure_patterns": self.sandbox.get_failure_patterns(),
        }

    @staticmethod
    def _parse_result_dict(result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Parse result dictionary for analysis.

        Args:
            result_dict: Result dictionary

        Returns:
            Parsed result data
        """
        return {
            "success": result_dict.get("success", False),
            "outcome": result_dict.get("test_outcome", "unknown"),
            "error_category": result_dict.get("error_category"),
        }

    async def generate_learning_report(self) -> Dict[str, Any]:
        """Generate learning report from test results.

        Returns:
            Dictionary with learning insights
        """
        if not self.test_results:
            return {"message": "No test results to analyze"}

        # Failure pattern analysis
        failure_patterns = self.sandbox.get_failure_patterns()

        # Most common failures
        top_failures = sorted(
            failure_patterns.items(),
            key=lambda x: x[1].frequency,
            reverse=True,
        )[:5]

        # Suggested improvements for generation
        improvements = []

        for pattern_key, pattern in top_failures:
            if "syntax" in pattern.error_category.value:
                improvements.append({
                    "category": "Syntax",
                    "issue": pattern.error_message,
                    "frequency": pattern.frequency,
                    "suggestion": "Add Python syntax validation before code generation",
                })
            elif "type" in pattern.error_category.value:
                improvements.append({
                    "category": "Type",
                    "issue": pattern.error_message,
                    "frequency": pattern.frequency,
                    "suggestion": "Enforce type hints and add type checking",
                })
            elif "dependency" in pattern.error_category.value:
                improvements.append({
                    "category": "Dependency",
                    "issue": pattern.error_message,
                    "frequency": pattern.frequency,
                    "suggestion": "Check available imports and dependencies",
                })
            elif "resource" in pattern.error_category.value:
                improvements.append({
                    "category": "Resource",
                    "issue": pattern.error_message,
                    "frequency": pattern.frequency,
                    "suggestion": "Add resource limits and optimize for memory",
                })

        stats = self._calculate_statistics()

        return {
            "total_dreams_tested": self.dreams_tested,
            "dreams_passed": self.dreams_passed,
            "test_statistics": stats,
            "top_failure_patterns": [
                {
                    "pattern": k,
                    "frequency": v.frequency,
                    "category": v.error_category.value,
                    "last_seen": v.last_seen.isoformat(),
                }
                for k, v in top_failures
            ],
            "suggested_improvements": improvements,
        }

    async def run_continuous_testing(
        self,
        interval_seconds: int = 300,
        max_iterations: int = None,
    ) -> None:
        """Run testing in a loop at regular intervals.

        Args:
            interval_seconds: Seconds between test runs
            max_iterations: Maximum iterations (None = infinite)
        """
        iteration = 0
        while max_iterations is None or iteration < max_iterations:
            logger.info(f"Starting test iteration {iteration + 1}")

            try:
                result = await self.test_tier1_dreams()
                logger.info(f"Test iteration {iteration + 1} complete: {result}")
            except Exception as e:
                logger.error(f"Test iteration {iteration + 1} failed: {e}")

            iteration += 1
            if max_iterations is None or iteration < max_iterations:
                await asyncio.sleep(interval_seconds)

        logger.info("Continuous testing completed")
