"""MCP handlers for specialized code review operations."""

import logging

logger = logging.getLogger(__name__)


def register_review_tools(server):
    """Register code review tools with MCP server.

    Args:
        server: MCP server instance
    """

    @server.tool()
    async def review_code(
        code: str,
        reviewers: list = None,
        context: dict = None,
    ) -> dict:
        """Review code with specialized domain-specific reviewers.

        Per "teach AI to think like a senior engineer", code passes through specialized reviewers
        for style, security, architecture, performance, and accessibility before implementation.

        Args:
            code: Code to review
            reviewers: List of reviewer types to use (default: all)
                      Options: "style", "security", "architecture", "performance", "accessibility"
            context: Additional context for reviews (language, framework, etc.)

        Returns:
            {
                "code_size": int,
                "reviews": [
                    {
                        "reviewer": str,
                        "domain": str,
                        "score": float,
                        "issues": [
                            {
                                "severity": str,
                                "title": str,
                                "description": str,
                                "suggestion": str,
                            }
                        ],
                        "recommendations": [str],
                    }
                ],
                "overall_score": float,
                "blocking_issues": int,
                "ready_for_implementation": bool,
            }
        """
        try:
            from ..review.agents import REVIEW_AGENTS

            if not reviewers:
                reviewers = list(REVIEW_AGENTS.keys())
            else:
                # Map reviewer names to agent keys
                reviewer_map = {
                    "style": "style-reviewer",
                    "security": "security-reviewer",
                    "architecture": "architecture-reviewer",
                    "performance": "performance-reviewer",
                    "accessibility": "accessibility-reviewer",
                }
                reviewers = [reviewer_map.get(r, r) for r in reviewers]

            # Run reviews
            reviews = []
            scores = []
            total_issues = 0

            for reviewer_key in reviewers:
                if reviewer_key not in REVIEW_AGENTS:
                    logger.warning(f"Unknown reviewer: {reviewer_key}")
                    continue

                try:
                    reviewer_class = REVIEW_AGENTS[reviewer_key]
                    reviewer = reviewer_class()
                    result = await reviewer.review(code, context=context)

                    reviews.append({
                        "reviewer": reviewer.name,
                        "domain": reviewer.domain,
                        "score": result.score,
                        "total_issues": len(result.issues),
                        "summary": result.summary,
                        "issues": [
                            {
                                "severity": issue.severity.value,
                                "title": issue.title,
                                "description": issue.description,
                                "location": issue.location,
                                "suggestion": issue.suggestion,
                            }
                            for issue in result.issues
                        ],
                        "recommendations": result.recommendations,
                    })

                    scores.append(result.score)
                    total_issues += len(result.issues)

                except Exception as e:
                    logger.error(f"Error running reviewer {reviewer_key}: {e}")
                    reviews.append({
                        "reviewer": reviewer_key,
                        "error": str(e),
                    })

            # Calculate overall score
            overall_score = sum(scores) / len(scores) if scores else 0.0

            # Count blocking issues
            blocking_issues = sum(
                len([i for i in r.get("issues", []) if i["severity"] == "critical"])
                for r in reviews
            )

            return {
                "code_size": len(code),
                "reviewers_run": len(reviews),
                "overall_score": overall_score,
                "total_issues": total_issues,
                "blocking_issues": blocking_issues,
                "ready_for_implementation": blocking_issues == 0 and overall_score > 0.6,
                "reviews": reviews,
            }

        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return {
                "error": f"Code review failed: {str(e)}",
            }

    @server.tool()
    async def review_with_reviewer(
        code: str,
        reviewer_type: str,
        context: dict = None,
    ) -> dict:
        """Run a specific specialized reviewer on code.

        Args:
            code: Code to review
            reviewer_type: Type of reviewer ("style", "security", "architecture", "performance", "accessibility")
            context: Additional context for review

        Returns:
            {
                "reviewer": str,
                "domain": str,
                "score": float,
                "issues": [
                    {
                        "severity": str,
                        "title": str,
                        "description": str,
                        "suggestion": str,
                    }
                ],
                "recommendations": [str],
            }
        """
        try:
            from ..review.agents import REVIEW_AGENTS

            reviewer_map = {
                "style": "style-reviewer",
                "security": "security-reviewer",
                "architecture": "architecture-reviewer",
                "performance": "performance-reviewer",
                "accessibility": "accessibility-reviewer",
            }

            reviewer_key = reviewer_map.get(reviewer_type, reviewer_type)

            if reviewer_key not in REVIEW_AGENTS:
                return {
                    "error": f"Unknown reviewer type: {reviewer_type}",
                    "available": list(reviewer_map.keys()),
                }

            reviewer_class = REVIEW_AGENTS[reviewer_key]
            reviewer = reviewer_class()
            result = await reviewer.review(code, context=context)

            return {
                "reviewer": reviewer.name,
                "domain": reviewer.domain,
                "score": result.score,
                "summary": result.summary,
                "issues_found": len(result.issues),
                "issues": [
                    {
                        "severity": issue.severity.value,
                        "title": issue.title,
                        "description": issue.description,
                        "location": issue.location,
                        "suggestion": issue.suggestion,
                        "example": issue.example,
                    }
                    for issue in result.issues
                ],
                "recommendations": result.recommendations,
            }

        except Exception as e:
            logger.error(f"Review failed: {e}")
            return {
                "error": f"Review failed: {str(e)}",
            }

    @server.tool()
    def get_available_reviewers() -> dict:
        """Get information about available specialized reviewers.

        Returns:
            {
                "reviewers": [
                    {
                        "key": str,
                        "name": str,
                        "domain": str,
                        "checks": [str],
                    }
                ],
            }
        """
        try:
            from ..review.agents import REVIEW_AGENTS

            reviewers = []

            # Define what each reviewer checks
            reviewer_checks = {
                "style-reviewer": [
                    "Naming conventions",
                    "Code formatting",
                    "Line length",
                    "Docstrings",
                    "Spacing",
                ],
                "security-reviewer": [
                    "Dangerous functions (eval, exec)",
                    "SQL injection risks",
                    "Hardcoded credentials",
                    "Input validation",
                    "Exception handling",
                ],
                "architecture-reviewer": [
                    "Function size",
                    "Magic numbers",
                    "Wildcard imports",
                    "Design patterns",
                    "Separation of concerns",
                ],
                "performance-reviewer": [
                    "N+1 queries",
                    "List operations efficiency",
                    "Blocking operations",
                    "String operations",
                    "Algorithm complexity",
                ],
                "accessibility-reviewer": [
                    "Error message clarity",
                    "User guidance",
                    "Internationalization",
                    "Usability",
                    "Help documentation",
                ],
            }

            for key, agent_class in REVIEW_AGENTS.items():
                agent = agent_class()
                reviewers.append({
                    "key": key,
                    "name": agent.name,
                    "domain": agent.domain,
                    "checks": reviewer_checks.get(key, []),
                })

            return {
                "total_reviewers": len(reviewers),
                "reviewers": reviewers,
            }

        except Exception as e:
            logger.error(f"Failed to get reviewers: {e}")
            return {
                "error": f"Failed to get reviewers: {str(e)}",
            }

    @server.tool()
    async def review_and_suggest_fixes(
        code: str,
        reviewer_type: str = "security",
    ) -> dict:
        """Review code and generate suggested fixes.

        Args:
            code: Code to review
            reviewer_type: Type of reviewer to focus on

        Returns:
            {
                "original_code": str,
                "reviewer": str,
                "issues": int,
                "suggested_fixes": [
                    {
                        "original": str,
                        "fixed": str,
                        "reason": str,
                    }
                ],
            }
        """
        try:
            from ..review.agents import REVIEW_AGENTS

            reviewer_map = {
                "style": "style-reviewer",
                "security": "security-reviewer",
                "architecture": "architecture-reviewer",
                "performance": "performance-reviewer",
                "accessibility": "accessibility-reviewer",
            }

            reviewer_key = reviewer_map.get(reviewer_type, reviewer_type)

            if reviewer_key not in REVIEW_AGENTS:
                return {
                    "error": f"Unknown reviewer: {reviewer_type}",
                }

            reviewer_class = REVIEW_AGENTS[reviewer_key]
            reviewer = reviewer_class()
            result = await reviewer.review(code)

            # Generate suggested fixes from issues
            suggested_fixes = [
                {
                    "issue": issue.title,
                    "reason": issue.description,
                    "suggestion": issue.suggestion,
                }
                for issue in result.issues
                if issue.suggestion
            ]

            return {
                "reviewer": reviewer.name,
                "issues_found": len(result.issues),
                "fixable_issues": len(suggested_fixes),
                "overall_score": result.score,
                "suggested_fixes": suggested_fixes,
                "recommendations": result.recommendations,
            }

        except Exception as e:
            logger.error(f"Review and suggest failed: {e}")
            return {
                "error": f"Review and suggest failed: {str(e)}",
            }
