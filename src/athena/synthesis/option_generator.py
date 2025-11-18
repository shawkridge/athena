"""Option generator for creating detailed solution options with sophisticated analysis."""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptionScore:
    """Scoring for an option."""

    simplicity: float  # 0.0-1.0
    performance: float  # 0.0-1.0
    scalability: float  # 0.0-1.0
    maintainability: float  # 0.0-1.0
    reliability: float  # 0.0-1.0
    cost: float  # 0.0-1.0 (higher = more expensive)

    def overall_score(self, weights: Dict[str, float] = None) -> float:
        """Calculate weighted overall score."""
        default_weights = {
            "simplicity": 0.2,
            "performance": 0.2,
            "scalability": 0.2,
            "maintainability": 0.2,
            "reliability": 0.1,
            "cost": 0.1,
        }
        weights = weights or default_weights

        total = (
            self.simplicity * weights.get("simplicity", 0)
            + self.performance * weights.get("performance", 0)
            + self.scalability * weights.get("scalability", 0)
            + self.maintainability * weights.get("maintainability", 0)
            + self.reliability * weights.get("reliability", 0)
            + (1.0 - self.cost) * weights.get("cost", 0)  # Lower cost is better
        )
        return min(1.0, max(0, total))


class OptionGenerator:
    """Generates detailed solution options with analysis."""

    def generate_options(
        self,
        problem: str,
        num_options: int = 3,
        context: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """Generate detailed solution options.

        Args:
            problem: Problem statement
            num_options: Number of options to generate (1-5)
            context: Additional context

        Returns:
            List of detailed option dictionaries
        """
        options = []

        # Generate options based on problem classification
        option_templates = self._classify_and_get_templates(problem)

        for i, template in enumerate(option_templates[:num_options]):
            option = self._elaborate_option(
                problem,
                template,
                context or {},
                i + 1,
            )
            options.append(option)

        return options

    def _classify_and_get_templates(self, problem: str) -> List[Dict[str, Any]]:
        """Classify problem and get relevant templates."""
        problem_lower = problem.lower()

        # Caching/performance optimization
        if any(
            word in problem_lower for word in ["slow", "fast", "performance", "cache", "latency"]
        ):
            return [
                self._template_simple_optimization(),
                self._template_distributed_optimization(),
                self._template_architectural_optimization(),
            ]

        # Scaling/growth
        if any(word in problem_lower for word in ["scale", "grow", "load", "concurrent", "users"]):
            return [
                self._template_vertical_scaling(),
                self._template_horizontal_scaling(),
                self._template_architectural_redesign(),
            ]

        # Reliability/resilience
        if any(word in problem_lower for word in ["fail", "reliable", "robust", "crash", "error"]):
            return [
                self._template_defensive_programming(),
                self._template_resilience_patterns(),
                self._template_distributed_resilience(),
            ]

        # Data/storage
        if any(word in problem_lower for word in ["data", "database", "storage", "query", "index"]):
            return [
                self._template_optimization(),
                self._template_caching_layer(),
                self._template_redesign(),
            ]

        # Default templates for generic problems
        return [
            self._template_pragmatic_approach(),
            self._template_balanced_approach(),
            self._template_comprehensive_approach(),
        ]

    def _template_simple_optimization(self) -> Dict[str, Any]:
        """Template: Simple direct optimization."""
        return {
            "name": "Simple Optimization",
            "philosophy": "Direct problem-solving with minimal changes",
            "implementation_complexity": "low",
            "time_to_value": "1-2 days",
            "risk": "low",
            "scalability": "limited",
            "description": "Identify and fix the root cause with targeted optimization",
            "example": "Add missing database index, optimize query",
            "best_when": "Single clear bottleneck identified",
            "worst_when": "Systemic performance issue",
        }

    def _template_distributed_optimization(self) -> Dict[str, Any]:
        """Template: Distributed/caching approach."""
        return {
            "name": "Distributed Optimization",
            "philosophy": "Use caching and distribution to spread load",
            "implementation_complexity": "medium",
            "time_to_value": "3-5 days",
            "risk": "medium",
            "scalability": "good",
            "description": "Add caching layers (Redis, CDN) or distribute computation",
            "example": "Add Redis cache, use CDN for static assets",
            "best_when": "Repeated computation or data access",
            "worst_when": "One-time expensive operations",
        }

    def _template_architectural_optimization(self) -> Dict[str, Any]:
        """Template: Architectural redesign."""
        return {
            "name": "Architectural Redesign",
            "philosophy": "Rethink fundamental approach",
            "implementation_complexity": "high",
            "time_to_value": "2-4 weeks",
            "risk": "high",
            "scalability": "excellent",
            "description": "Redesign system architecture for better performance characteristics",
            "example": "Move to event-driven, async processing, streaming",
            "best_when": "Current architecture fundamentally limited",
            "worst_when": "Quick fix needed",
        }

    def _template_vertical_scaling(self) -> Dict[str, Any]:
        """Template: Vertical scaling."""
        return {
            "name": "Vertical Scaling",
            "philosophy": "Make the current server more powerful",
            "implementation_complexity": "low",
            "time_to_value": "immediate",
            "risk": "low",
            "scalability": "limited",
            "description": "Upgrade CPU, memory, or storage on existing server",
            "example": "Upgrade server from 8GB to 32GB RAM",
            "best_when": "Temporary traffic spike, single bottleneck",
            "worst_when": "Unlimited growth expected",
        }

    def _template_horizontal_scaling(self) -> Dict[str, Any]:
        """Template: Horizontal scaling."""
        return {
            "name": "Horizontal Scaling",
            "philosophy": "Distribute work across multiple servers",
            "implementation_complexity": "medium",
            "time_to_value": "1-2 weeks",
            "risk": "medium",
            "scalability": "excellent",
            "description": "Deploy application across multiple servers with load balancing",
            "example": "Add load balancer, deploy to 3+ server instances",
            "best_when": "Sustained growth, redundancy desired",
            "worst_when": "Single-threaded app, shared state",
        }

    def _template_architectural_redesign(self) -> Dict[str, Any]:
        """Template: Complete redesign."""
        return {
            "name": "Architectural Redesign",
            "philosophy": "Fundamentally restructure for unlimited scale",
            "implementation_complexity": "high",
            "time_to_value": "4-12 weeks",
            "risk": "high",
            "scalability": "unlimited",
            "description": "Move to microservices, event-driven, or cloud-native design",
            "example": "Microservices with Kubernetes, event streaming",
            "best_when": "Long-term sustained growth required",
            "worst_when": "Need to ship quickly",
        }

    def _template_defensive_programming(self) -> Dict[str, Any]:
        """Template: Defensive programming."""
        return {
            "name": "Defensive Programming",
            "philosophy": "Prevent errors through validation and checks",
            "implementation_complexity": "low",
            "time_to_value": "immediate",
            "risk": "low",
            "scalability": "good",
            "description": "Add validation, error handling, and fail-safes",
            "example": "Input validation, bounds checking, error recovery",
            "best_when": "Preventing known failure modes",
            "worst_when": "Complex distributed system failures",
        }

    def _template_resilience_patterns(self) -> Dict[str, Any]:
        """Template: Resilience patterns."""
        return {
            "name": "Resilience Patterns",
            "philosophy": "Graceful degradation and recovery",
            "implementation_complexity": "medium",
            "time_to_value": "1-2 weeks",
            "risk": "medium",
            "scalability": "good",
            "description": "Circuit breaker, retry logic, timeouts, fallbacks",
            "example": "Circuit breaker for external services, exponential backoff",
            "best_when": "Intermittent failures, external dependencies",
            "worst_when": "Complete failure is acceptable",
        }

    def _template_distributed_resilience(self) -> Dict[str, Any]:
        """Template: Distributed resilience."""
        return {
            "name": "Distributed Resilience",
            "philosophy": "Multiple redundant services and data replication",
            "implementation_complexity": "high",
            "time_to_value": "3-8 weeks",
            "risk": "high",
            "scalability": "excellent",
            "description": "Multi-region deployment, data replication, consensus protocols",
            "example": "Multi-region DB, service mesh, event sourcing",
            "best_when": "High availability critical",
            "worst_when": "Cost is primary concern",
        }

    def _template_optimization(self) -> Dict[str, Any]:
        """Template: Direct optimization."""
        return {
            "name": "Direct Optimization",
            "philosophy": "Fix queries and access patterns",
            "implementation_complexity": "low",
            "time_to_value": "1-3 days",
            "risk": "low",
            "description": "Add indexes, optimize queries, tune parameters",
        }

    def _template_caching_layer(self) -> Dict[str, Any]:
        """Template: Add caching."""
        return {
            "name": "Caching Layer",
            "philosophy": "Cache expensive computations and queries",
            "implementation_complexity": "medium",
            "time_to_value": "3-5 days",
            "risk": "medium",
            "description": "Redis, memcached, or application-level caching",
        }

    def _template_redesign(self) -> Dict[str, Any]:
        """Template: Complete redesign."""
        return {
            "name": "Data Architecture Redesign",
            "philosophy": "Rethink data model and storage",
            "implementation_complexity": "high",
            "time_to_value": "2-6 weeks",
            "risk": "high",
            "description": "Denormalization, sharding, document model, etc.",
        }

    def _template_pragmatic_approach(self) -> Dict[str, Any]:
        """Template: Pragmatic straightforward approach."""
        return {
            "name": "Pragmatic Straightforward Approach",
            "philosophy": "Simplest possible solution that solves the problem",
            "implementation_complexity": "low",
            "time_to_value": "immediate",
            "risk": "low",
            "scalability": "limited",
        }

    def _template_balanced_approach(self) -> Dict[str, Any]:
        """Template: Balanced approach."""
        return {
            "name": "Balanced Approach",
            "philosophy": "Good trade-off between complexity and capability",
            "implementation_complexity": "medium",
            "time_to_value": "1 week",
            "risk": "medium",
            "scalability": "good",
        }

    def _template_comprehensive_approach(self) -> Dict[str, Any]:
        """Template: Comprehensive approach."""
        return {
            "name": "Comprehensive Robust Approach",
            "philosophy": "Production-grade solution with all features",
            "implementation_complexity": "high",
            "time_to_value": "4-8 weeks",
            "risk": "high",
            "scalability": "excellent",
        }

    def _elaborate_option(
        self,
        problem: str,
        template: Dict[str, Any],
        context: Dict[str, Any],
        sequence: int,
    ) -> Dict[str, Any]:
        """Elaborate a template into a detailed option."""
        option = {
            "option_id": f"option_{sequence}",
            "name": template.get("name", f"Option {sequence}"),
            "philosophy": template.get("philosophy", ""),
            "description": template.get("description", ""),
            "implementation_complexity": template.get("implementation_complexity", "medium"),
            "time_to_value": template.get("time_to_value", "1 week"),
            "risk_level": template.get("risk", "medium"),
            "scalability": template.get("scalability", "good"),
            "example": template.get("example", ""),
            "best_when": template.get("best_when", ""),
            "worst_when": template.get("worst_when", ""),
        }

        # Add scoring
        option["scores"] = self._score_option(option, context)

        # Add details
        option["details"] = {
            "implementation_steps": self._get_steps(option["name"]),
            "required_skills": self._get_skills(option["name"]),
            "dependencies": self._get_dependencies(option["name"]),
            "testing_strategy": self._get_testing(option["name"]),
            "rollback_plan": self._get_rollback(option["name"]),
            "monitoring": self._get_monitoring(option["name"]),
        }

        return option

    def _score_option(
        self,
        option: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, float]:
        """Score an option across dimensions."""
        complexity_map = {
            "low": 0.8,
            "medium": 0.5,
            "high": 0.2,
        }

        simplicity = complexity_map.get(option.get("implementation_complexity", "medium"), 0.5)
        scalability_map = {
            "limited": 0.3,
            "good": 0.7,
            "excellent": 0.95,
        }
        scalability = scalability_map.get(option.get("scalability", "good"), 0.7)

        risk_map = {
            "low": 0.9,
            "medium": 0.5,
            "high": 0.2,
        }
        reliability = risk_map.get(option.get("risk_level", "medium"), 0.5)

        return {
            "simplicity": simplicity,
            "performance": 0.7,  # Default
            "scalability": scalability,
            "maintainability": simplicity,
            "reliability": reliability,
            "cost": 0.5,  # Default
            "overall": (simplicity + scalability + reliability) / 3,
        }

    def _get_steps(self, option_name: str) -> List[str]:
        """Get implementation steps for option."""
        steps_map = {
            "Direct Optimization": [
                "Profile and identify bottleneck",
                "Add database indexes",
                "Optimize hot queries",
                "Verify performance improvement",
            ],
            "Distributed Optimization": [
                "Set up Redis or cache layer",
                "Implement cache invalidation",
                "Add cache warming strategy",
                "Monitor cache hit rate",
            ],
            "Vertical Scaling": [
                "Upgrade server hardware",
                "Monitor new resource usage",
                "Optimize for new capacity",
            ],
            "Horizontal Scaling": [
                "Make application stateless",
                "Set up load balancer",
                "Deploy to multiple servers",
                "Configure auto-scaling",
            ],
        }
        return steps_map.get(option_name, ["Implement", "Test", "Deploy", "Monitor"])

    def _get_skills(self, option_name: str) -> List[str]:
        """Get required skills for option."""
        skills_map = {
            "Direct Optimization": ["SQL", "Database indexing", "Query optimization"],
            "Distributed Optimization": ["Redis/Memcached", "Cache strategies"],
            "Vertical Scaling": ["Infrastructure", "Hardware", "OS tuning"],
            "Horizontal Scaling": ["Load balancing", "Orchestration", "Networking"],
        }
        return skills_map.get(option_name, ["Software Engineering"])

    def _get_dependencies(self, option_name: str) -> List[str]:
        """Get external dependencies for option."""
        deps_map = {
            "Distributed Optimization": ["Redis server", "Cache client library"],
            "Horizontal Scaling": ["Load balancer", "Orchestration platform"],
        }
        return deps_map.get(option_name, [])

    def _get_testing(self, option_name: str) -> str:
        """Get testing strategy for option."""
        return "Load test with expected traffic patterns, verify success metrics"

    def _get_rollback(self, option_name: str) -> str:
        """Get rollback plan for option."""
        return "Gradual rollout with feature flags, ability to revert if issues detected"

    def _get_monitoring(self, option_name: str) -> List[str]:
        """Get monitoring recommendations."""
        return [
            "Track implementation progress",
            "Monitor key performance metrics",
            "Alert on failures or regressions",
            "Dashboard for visibility",
        ]
