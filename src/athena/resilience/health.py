"""Health Checks & Monitoring.

Provides system health checking, custom health check registration,
and comprehensive health reporting for operational visibility.
"""

import logging
import time
import shutil
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

    def is_ok(self) -> bool:
        """Check if status is acceptable (healthy or degraded)."""
        return self in (self.HEALTHY, self.DEGRADED)

    def __lt__(self, other: "HealthStatus") -> bool:
        """Compare health statuses (lower is worse)."""
        order = {self.UNHEALTHY: 0, self.DEGRADED: 1, self.HEALTHY: 2}
        return order[self] < order[other]

    def __le__(self, other: "HealthStatus") -> bool:
        """Compare health statuses."""
        return self < other or self == other


@dataclass
class HealthReport:
    """Health check result."""

    name: str
    status: HealthStatus
    message: str = ""
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


@dataclass
class SystemHealth:
    """Complete system health report."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    checks: List[HealthReport] = field(default_factory=list)

    def overall_status(self) -> HealthStatus:
        """Get overall system status (worst of all checks)."""
        if not self.checks:
            return HealthStatus.HEALTHY

        statuses = [check.status for check in self.checks]
        # Return the worst status (using comparison operators)
        worst = HealthStatus.HEALTHY
        for status in statuses:
            if status < worst:
                worst = status
        return worst

    def is_healthy(self) -> bool:
        """Check if overall system is healthy."""
        return self.overall_status() == HealthStatus.HEALTHY

    def is_degraded(self) -> bool:
        """Check if system is degraded."""
        return self.overall_status() == HealthStatus.DEGRADED

    def is_unhealthy(self) -> bool:
        """Check if system is unhealthy."""
        return self.overall_status() == HealthStatus.UNHEALTHY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status().value,
            "is_healthy": self.is_healthy(),
            "checks": [check.to_dict() for check in self.checks],
        }


class HealthChecker:
    """System health checking with custom check registration."""

    def __init__(self):
        """Initialize health checker."""
        self.checks: Dict[str, Callable[[], HealthReport]] = {}
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register built-in health checks."""
        self.register("system_memory", self._check_system_memory)
        self.register("disk_space", self._check_disk_space)

    def register(self, name: str, check: Callable[[], HealthReport]) -> None:
        """Register custom health check.

        Args:
            name: Check identifier
            check: Callable returning HealthReport
        """
        self.checks[name] = check
        logger.debug(f"Registered health check: {name}")

    def _check_system_memory(self) -> HealthReport:
        """Check system memory availability."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            available_percent = memory.available / memory.total * 100

            if available_percent < 5:
                status = HealthStatus.UNHEALTHY
                message = f"Critical memory pressure: {available_percent:.1f}% available"
            elif available_percent < 15:
                status = HealthStatus.DEGRADED
                message = f"Low memory: {available_percent:.1f}% available"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory healthy: {available_percent:.1f}% available"

            start = time.perf_counter()
            duration = (time.perf_counter() - start) * 1000

            return HealthReport(
                name="system_memory",
                status=status,
                message=message,
                duration_ms=duration,
                details={
                    "available_percent": available_percent,
                    "available_bytes": memory.available,
                    "total_bytes": memory.total,
                },
            )
        except Exception as e:
            logger.error("System memory check failed", exc_info=True)
            return HealthReport(
                name="system_memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
            )

    def _check_disk_space(self) -> HealthReport:
        """Check disk space availability."""
        try:
            start = time.perf_counter()

            home_path = Path.home()
            disk_usage = shutil.disk_usage(home_path)
            available_percent = disk_usage.free / disk_usage.total * 100

            if disk_usage.free < 1_000_000_000:  # <1GB
                status = HealthStatus.UNHEALTHY
                message = f"Critical disk space: {disk_usage.free / 1e9:.1f}GB free"
            elif disk_usage.free < 5_000_000_000:  # <5GB
                status = HealthStatus.DEGRADED
                message = f"Low disk space: {disk_usage.free / 1e9:.1f}GB free"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space healthy: {disk_usage.free / 1e9:.1f}GB free"

            duration = (time.perf_counter() - start) * 1000

            return HealthReport(
                name="disk_space",
                status=status,
                message=message,
                duration_ms=duration,
                details={
                    "available_percent": available_percent,
                    "free_bytes": disk_usage.free,
                    "total_bytes": disk_usage.total,
                },
            )
        except Exception as e:
            logger.error("Disk space check failed", exc_info=True)
            return HealthReport(
                name="disk_space",
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
            )

    def check(self, name: str) -> HealthReport:
        """Run single health check.

        Args:
            name: Check identifier

        Returns:
            HealthReport

        Raises:
            ValueError: If check not found
        """
        if name not in self.checks:
            raise ValueError(f"Health check not found: {name}")

        try:
            return self.checks[name]()
        except Exception as e:
            logger.error(f"Health check '{name}' failed", exc_info=True)
            return HealthReport(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
            )

    def check_all(self) -> SystemHealth:
        """Run all registered health checks.

        Returns:
            SystemHealth with all check results
        """
        health = SystemHealth()

        for check_name in self.checks:
            try:
                report = self.check(check_name)
                health.checks.append(report)
            except Exception as e:
                logger.error(f"Error running check {check_name}", exc_info=True)
                health.checks.append(
                    HealthReport(
                        name=check_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Check error: {str(e)}",
                    )
                )

        return health

    def get_summary(self) -> Dict[str, Any]:
        """Get health summary for logging."""
        health = self.check_all()
        return {
            "overall_status": health.overall_status().value,
            "is_healthy": health.is_healthy(),
            "checks_passed": sum(1 for c in health.checks if c.status == HealthStatus.HEALTHY),
            "checks_degraded": sum(1 for c in health.checks if c.status == HealthStatus.DEGRADED),
            "checks_failed": sum(1 for c in health.checks if c.status == HealthStatus.UNHEALTHY),
            "total_checks": len(health.checks),
        }
