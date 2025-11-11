"""Health check infrastructure for Memory MCP.

Provides system health monitoring and status reporting.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthReport:
    """Health report for a system component."""

    name: str
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthChecker:
    """Perform health checks on Memory MCP system."""

    def __init__(self):
        """Initialize health checker."""
        self.checks: Dict[str, callable] = {}
        self.history: List[HealthReport] = []

    def register_check(self, name: str, check_func: callable):
        """Register a health check function."""
        self.checks[name] = check_func

    def perform_check(self, name: str) -> HealthReport:
        """Perform a health check."""
        if name not in self.checks:
            return HealthReport(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check '{name}' not registered",
            )

        try:
            check_func = self.checks[name]
            result = check_func()

            report = HealthReport(
                name=name,
                status=result.get("status", HealthStatus.HEALTHY),
                message=result.get("message", ""),
                latency_ms=result.get("latency_ms"),
            )
        except Exception as e:
            report = HealthReport(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
            )

        self.history.append(report)
        return report

    def perform_all_checks(self) -> Dict[str, HealthReport]:
        """Perform all registered health checks."""
        results = {}
        for name in self.checks:
            results[name] = self.perform_check(name)
        return results

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status."""
        if not self.checks:
            return HealthStatus.HEALTHY

        statuses = [report.status for report in self.perform_all_checks().values()]

        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def get_report(self) -> Dict:
        """Get comprehensive health report."""
        checks = self.perform_all_checks()

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": self.get_overall_status().value,
            "checks": {
                name: {
                    "status": report.status.value,
                    "message": report.message,
                    "latency_ms": report.latency_ms,
                    "timestamp": report.timestamp.isoformat(),
                }
                for name, report in checks.items()
            },
        }


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get or create the global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
        # Register default checks
        _register_default_checks(_health_checker)
    return _health_checker


def _register_default_checks(checker: HealthChecker):
    """Register default health checks."""

    def check_memory_availability():
        """Check system memory availability."""
        import psutil

        try:
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Memory usage {memory.percent}%",
                }
            return {
                "status": HealthStatus.HEALTHY,
                "message": f"Memory usage {memory.percent}%",
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": f"Memory check failed: {str(e)}",
            }

    def check_disk_space():
        """Check disk space availability."""
        import psutil
        import os

        try:
            disk = psutil.disk_usage("/")
            if disk.percent > 90:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Disk usage {disk.percent}%",
                }
            return {
                "status": HealthStatus.HEALTHY,
                "message": f"Disk usage {disk.percent}%",
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": f"Disk check failed: {str(e)}",
            }

    checker.register_check("memory", check_memory_availability)
    checker.register_check("disk", check_disk_space)


# Standard health checks for specific components
def create_database_check(db_path: str):
    """Create a database connectivity check."""

    def check():
        """Check database connectivity."""
        import time
        try:
            start = time.perf_counter()
            # PostgreSQL connection should be used instead
            conn.execute("SELECT 1")
            conn.close()
            latency = (time.perf_counter() - start) * 1000

            if latency > 1000:
                return {
                    "status": HealthStatus.DEGRADED,
                    "message": f"Database query latency {latency:.0f}ms",
                    "latency_ms": latency,
                }

            return {
                "status": HealthStatus.HEALTHY,
                "message": "Database connectivity OK",
                "latency_ms": latency,
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"Database check failed: {str(e)}",
            }

    return check


def create_embedding_check():
    """Create an embedding model availability check."""

    def check():
        """Check embedding model availability."""
        import time

        try:
            # Try to get embeddings
            import subprocess

            start = time.perf_counter()
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                timeout=5,
            )
            latency = (time.perf_counter() - start) * 1000

            if result.returncode != 0:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "Ollama not responding",
                }

            return {
                "status": HealthStatus.HEALTHY,
                "message": "Embedding model available",
                "latency_ms": latency,
            }
        except Exception as e:
            return {
                "status": HealthStatus.DEGRADED,
                "message": f"Embedding check failed: {str(e)}",
            }

    return check
