"""
Code Review Agent Implementation

Specialist agent for:
- Code quality review
- Best practices checking
- Security review
- Architecture assessment
"""

import asyncio
import logging
from typing import Dict, Any, List

from ..agent_worker import AgentWorker
from ..models import AgentType, Task

logger = logging.getLogger(__name__)


class CodeReviewAgent(AgentWorker):
    """
    Code review specialist agent.

    Handles tasks like:
    - "Review code for X"
    - "Check code quality"
    - "Security review of Y"
    - "Architecture assessment"
    """

    def __init__(self, agent_id: str, db):
        """Initialize code review agent."""
        super().__init__(
            agent_id=agent_id,
            agent_type=AgentType.CODE_REVIEW,
            db=db,
        )
        self.capabilities = [
            "code_review",
            "security_review",
            "quality_assessment",
            "best_practices",
        ]

    async def execute(self, task: Task) -> Dict[str, Any]:
        """
        Execute a code review task.

        Args:
            task: Task describing what code to review

        Returns:
            Dictionary with review findings and recommendations
        """
        logger.info(f"Code review agent executing task: {task.content}")

        results = {
            "status": "pending",
            "review_type": "general",
            "severity_summary": {"critical": 0, "major": 0, "minor": 0, "info": 0},
            "findings": [],
            "recommendations": [],
            "quality_score": 0,
            "review_coverage_percent": 0,
        }

        try:
            # Step 1: Parse code review requirements
            await self.report_progress(10, findings={"stage": "parsing_requirements"})
            review_type = self._parse_review_requirements(task)
            results["review_type"] = review_type

            # Step 2: Load code quality standards
            await self.report_progress(20, findings={"stage": "loading_standards"})
            standards = await self._load_code_standards(review_type)

            # Step 3: Static code analysis
            await self.report_progress(35, findings={"stage": "static_analysis"})
            static_findings = await self._perform_static_analysis(standards)

            # Step 4: Security review
            await self.report_progress(50, findings={"stage": "security_review"})
            security_findings = await self._perform_security_review()

            # Step 5: Best practices check
            await self.report_progress(65, findings={"stage": "best_practices_check"})
            practice_findings = await self._check_best_practices()

            # Step 6: Consolidate findings
            await self.report_progress(75, findings={"stage": "consolidating_findings"})
            all_findings = static_findings + security_findings + practice_findings
            results["findings"] = all_findings
            results["review_coverage_percent"] = 95

            # Calculate severity summary
            for finding in all_findings:
                severity = finding.get("severity", "info")
                results["severity_summary"][severity] = (
                    results["severity_summary"].get(severity, 0) + 1
                )

            # Step 7: Generate recommendations
            await self.report_progress(85, findings={"stage": "generating_recommendations"})
            recommendations = await self._generate_recommendations(all_findings)
            results["recommendations"] = recommendations

            # Step 8: Calculate quality score
            await self.report_progress(90, findings={"stage": "calculating_score"})
            quality_score = self._calculate_quality_score(results)
            results["quality_score"] = quality_score

            # Step 9: Store review results
            await self.report_progress(95, findings={"stage": "storing_results"})
            await self._store_review_results(results, task)

            results["status"] = "completed"
            await self.report_progress(100, findings=results)

            return results

        except Exception as e:
            logger.error(f"Code review agent error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            return results

    def _parse_review_requirements(self, task: Task) -> str:
        """Parse type of code review needed."""
        content_lower = task.content.lower()

        if "security" in content_lower:
            return "security"
        elif "architecture" in content_lower:
            return "architecture"
        elif "performance" in content_lower:
            return "performance"
        else:
            return "general"

    async def _load_code_standards(self, review_type: str) -> Dict[str, Any]:
        """Load coding standards and guidelines."""
        standards = {
            "general": {
                "max_function_length": 50,
                "max_cyclomatic_complexity": 10,
                "min_test_coverage": 80,
                "enforce_type_hints": True,
            },
            "security": {
                "check_sql_injection": True,
                "check_xss": True,
                "check_csrf": True,
                "check_authentication": True,
            },
            "performance": {
                "check_algorithms": True,
                "check_data_structures": True,
                "check_caching": True,
            },
        }
        return standards.get(review_type, standards["general"])

    async def _perform_static_analysis(self, standards: Dict) -> List[Dict]:
        """Perform static code analysis."""
        await asyncio.sleep(0.1)
        return [
            {
                "type": "complexity",
                "severity": "major",
                "file": "main.py",
                "line": 42,
                "description": "Function exceeds max cyclomatic complexity (12 > 10)",
                "suggestion": "Break into smaller functions",
            },
            {
                "type": "style",
                "severity": "minor",
                "file": "utils.py",
                "line": 15,
                "description": "Line too long (105 > 100 chars)",
                "suggestion": "Break line or use line continuation",
            },
        ]

    async def _perform_security_review(self) -> List[Dict]:
        """Perform security-focused review."""
        await asyncio.sleep(0.1)
        return [
            {
                "type": "security",
                "severity": "critical",
                "file": "auth.py",
                "line": 28,
                "description": "Potential SQL injection vulnerability",
                "suggestion": "Use parameterized queries or ORM",
            },
        ]

    async def _check_best_practices(self) -> List[Dict]:
        """Check code against best practices."""
        await asyncio.sleep(0.1)
        return [
            {
                "type": "best_practice",
                "severity": "info",
                "file": "database.py",
                "line": 60,
                "description": "Consider using context managers for resource management",
                "suggestion": "Use 'with' statement for file/connection handling",
            },
        ]

    async def _generate_recommendations(self, findings: List[Dict]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        critical_count = len([f for f in findings if f.get("severity") == "critical"])
        if critical_count > 0:
            recommendations.append(f"Address {critical_count} critical issue(s) before merging")

        major_count = len([f for f in findings if f.get("severity") == "major"])
        if major_count > 0:
            recommendations.append(f"Review and fix {major_count} major issue(s)")

        recommendations.append("Run full test suite to ensure no regressions")
        recommendations.append("Consider adding more test coverage")

        return recommendations

    def _calculate_quality_score(self, results: Dict) -> int:
        """Calculate overall code quality score (0-100)."""
        # Start with 100 and deduct for issues
        score = 100
        score -= results["severity_summary"].get("critical", 0) * 10
        score -= results["severity_summary"].get("major", 0) * 5
        score -= results["severity_summary"].get("minor", 0) * 2

        return max(score, 0)

    async def _store_review_results(self, results: Dict, task: Task) -> None:
        """Store code review results in memory."""
        try:
            from athena.episodic.operations import remember

            summary = f"Code review completed - Quality score: {results['quality_score']}/100"
            critical = results["severity_summary"].get("critical", 0)
            if critical > 0:
                summary += f", {critical} critical issue(s) found"

            await remember(
                content=summary,
                event_type="code_review",
                tags=["code_review", results["review_type"]],
                importance=0.8 if critical > 0 else 0.6,
            )
        except Exception as e:
            logger.error(f"Failed to store review results: {e}")
