"""PostgreSQL Health Check Module

Comprehensive health diagnostics for PostgreSQL database used by Athena memory system.

Provides:
- Connectivity verification
- Database existence check
- Required tables validation
- User permissions check
- Disk space monitoring
- Structured health status reporting
- Recovery recommendations
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Minor issues, can continue
    CRITICAL = "critical"   # Cannot proceed
    UNKNOWN = "unknown"     # Unable to determine


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    check_name: str
    passed: bool
    message: str
    severity: str = "info"  # info, warning, error


@dataclass
class PostgreSQLHealth:
    """Overall PostgreSQL health status."""
    healthy: bool
    status: HealthStatus
    checks: List[Dict]  # List of HealthCheckResult as dicts
    error: Optional[str] = None
    recommendations: List[str] = None
    stats: Dict = None

    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.stats is None:
            self.stats = {}


class PostgreSQLHealthCheck:
    """Comprehensive PostgreSQL health checking."""

    # Required tables for Athena system (currently 16 tables)
    REQUIRED_TABLES = [
        "episodic_events",           # Core: User interactions & tool executions
        "prospective_goals",         # Task management
        "prospective_tasks",         # Task management
        "projects",                  # Project context mapping
        "skills",                    # Learned workflows
        "procedures",                # Reusable procedures
        "memory_vectors",            # Semantic embeddings
        "memory_relationships",      # Knowledge graph
        "code_metadata",             # Codebase structure
        "code_dependencies",         # Import relationships
        "planning_decisions",        # Decision log
        "planning_scenarios",        # Scenario simulation
        "extracted_patterns",        # Pattern storage
        "consolidation_runs",        # Consolidation log
        "memory_conflicts",          # Contradiction tracking
        "performance_metrics",       # Profiling data
    ]

    def __init__(self, verbose: bool = False):
        """Initialize health checker.

        Args:
            verbose: Enable debug logging
        """
        self.verbose = verbose
        self.conn = None
        self.checks: List[HealthCheckResult] = []
        self.recommendations: List[str] = []

        if verbose:
            logging.basicConfig(level=logging.DEBUG)

    def _get_connection_params(self) -> Dict[str, str]:
        """Get PostgreSQL connection parameters from environment."""
        return {
            "host": os.environ.get("ATHENA_POSTGRES_HOST", "localhost"),
            "port": os.environ.get("ATHENA_POSTGRES_PORT", "5432"),
            "dbname": os.environ.get("ATHENA_POSTGRES_DB", "athena"),
            "user": os.environ.get("ATHENA_POSTGRES_USER", "postgres"),
            "password": os.environ.get("ATHENA_POSTGRES_PASSWORD", "postgres"),
        }

    def _add_check(
        self,
        name: str,
        passed: bool,
        message: str,
        severity: str = "info"
    ):
        """Record a health check result."""
        self.checks.append(
            HealthCheckResult(
                check_name=name,
                passed=passed,
                message=message,
                severity=severity
            )
        )

    def check_connectivity(self) -> bool:
        """Check if PostgreSQL is running and accessible.

        Returns:
            True if connection successful
        """
        try:
            import psycopg

            params = self._get_connection_params()

            if self.verbose:
                print(f"Attempting connection to {params['host']}:{params['port']}")

            conn = psycopg.connect(
                host=params["host"],
                port=int(params["port"]),
                user=params["user"],
                password=params["password"],
            )

            # Test connection with simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()

            self._add_check(
                "PostgreSQL Connectivity",
                True,
                f"Connected to PostgreSQL at {params['host']}:{params['port']}",
                "info"
            )

            return True

        except Exception as e:
            error_msg = str(e)

            # Parse error to provide better recommendations
            if "Connection refused" in error_msg or "could not connect" in error_msg:
                self._add_check(
                    "PostgreSQL Connectivity",
                    False,
                    f"Cannot connect to PostgreSQL at {params['host']}:{params['port']}",
                    "error"
                )
                self.recommendations.append(
                    f"Start PostgreSQL: pg_isready -h {params['host']} -p {params['port']}"
                )
                self.recommendations.append(
                    "Check PostgreSQL is running: psql --version && pg_isready"
                )

            elif "password" in error_msg.lower():
                self._add_check(
                    "PostgreSQL Connectivity",
                    False,
                    f"Authentication failed for user '{params['user']}'",
                    "error"
                )
                self.recommendations.append(
                    f"Verify PostgreSQL password for user '{params['user']}'"
                )
                self.recommendations.append(
                    "Check environment: ATHENA_POSTGRES_PASSWORD"
                )

            else:
                self._add_check(
                    "PostgreSQL Connectivity",
                    False,
                    f"Connection error: {error_msg}",
                    "error"
                )
                self.recommendations.append("Check PostgreSQL is running")

            return False

    def check_database_exists(self) -> bool:
        """Verify 'athena' database exists.

        Returns:
            True if database exists
        """
        try:
            import psycopg

            params = self._get_connection_params()
            dbname = params["dbname"]

            # Connect to default 'postgres' database first
            conn = psycopg.connect(
                host=params["host"],
                port=int(params["port"]),
                user=params["user"],
                password=params["password"],
                dbname="postgres",  # Connect to postgres DB to query databases
            )

            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (dbname,)
            )
            exists = cursor.fetchone() is not None
            cursor.close()
            conn.close()

            if exists:
                self._add_check(
                    "Database Exists",
                    True,
                    f"Database '{dbname}' exists",
                    "info"
                )
                return True
            else:
                self._add_check(
                    "Database Exists",
                    False,
                    f"Database '{dbname}' does not exist",
                    "error"
                )
                self.recommendations.append(
                    f"Create database: psql -U postgres -c 'CREATE DATABASE {dbname}'"
                )
                return False

        except Exception as e:
            self._add_check(
                "Database Exists",
                False,
                f"Error checking database: {str(e)}",
                "error"
            )
            return False

    def check_required_tables(self) -> bool:
        """Check all required tables exist.

        Returns:
            True if all tables present
        """
        try:
            import psycopg

            params = self._get_connection_params()

            conn = psycopg.connect(
                host=params["host"],
                port=int(params["port"]),
                user=params["user"],
                password=params["password"],
                dbname=params["dbname"],
            )

            cursor = conn.cursor()

            # Get list of existing tables
            cursor.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                """
            )
            existing_tables = {row[0] for row in cursor.fetchall()}

            # Check for required tables
            missing_tables = []
            for table in self.REQUIRED_TABLES:
                if table not in existing_tables:
                    missing_tables.append(table)

            cursor.close()
            conn.close()

            if missing_tables:
                self._add_check(
                    "Required Tables",
                    False,
                    f"Missing {len(missing_tables)} required tables: {', '.join(missing_tables[:3])}...",
                    "error"
                )
                self.recommendations.append(
                    f"Create missing tables by starting MCP server: memory-mcp"
                )
                return False
            else:
                self._add_check(
                    "Required Tables",
                    True,
                    f"All {len(self.REQUIRED_TABLES)} required tables exist",
                    "info"
                )
                return True

        except Exception as e:
            self._add_check(
                "Required Tables",
                False,
                f"Error checking tables: {str(e)}",
                "error"
            )
            return False

    def check_user_permissions(self) -> bool:
        """Verify user has required permissions.

        Returns:
            True if user has adequate permissions
        """
        try:
            import psycopg

            params = self._get_connection_params()

            conn = psycopg.connect(
                host=params["host"],
                port=int(params["port"]),
                user=params["user"],
                password=params["password"],
                dbname=params["dbname"],
            )

            cursor = conn.cursor()

            # Check for SELECT permission
            cursor.execute("SELECT COUNT(*) FROM episodic_events")
            cursor.fetchone()

            # Check for INSERT permission (on a test table or just check role)
            cursor.execute("SELECT current_user, session_user")
            user_info = cursor.fetchone()

            # Check if user can create tables (optional, informational)
            cursor.execute(
                """
                SELECT has_table_privilege(current_user, 'episodic_events', 'SELECT')
                """
            )
            has_select = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            if has_select:
                self._add_check(
                    "User Permissions",
                    True,
                    f"User '{params['user']}' has required permissions",
                    "info"
                )
                return True
            else:
                self._add_check(
                    "User Permissions",
                    False,
                    f"User '{params['user']}' lacks required permissions",
                    "error"
                )
                self.recommendations.append(
                    f"Grant permissions: psql -U postgres -d {params['dbname']} -c 'GRANT ALL ON ALL TABLES IN SCHEMA public TO {params['user']}'"
                )
                return False

        except Exception as e:
            self._add_check(
                "User Permissions",
                False,
                f"Error checking permissions: {str(e)}",
                "error"
            )
            return False

    def check_disk_space(self) -> Dict[str, int]:
        """Check PostgreSQL disk usage.

        Returns:
            Dict with disk_used (bytes) and disk_available (bytes)
        """
        try:
            import psycopg

            params = self._get_connection_params()

            conn = psycopg.connect(
                host=params["host"],
                port=int(params["port"]),
                user=params["user"],
                password=params["password"],
                dbname=params["dbname"],
            )

            cursor = conn.cursor()

            # Get database size
            cursor.execute(
                "SELECT pg_database_size(current_database())"
            )
            db_size = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            # Get filesystem disk space
            import shutil
            stat = shutil.disk_usage("/")

            self._add_check(
                "Disk Space",
                stat.free > 1_000_000_000,  # More than 1GB
                f"Database: {db_size / 1_000_000:.1f} MB, Free: {stat.free / 1_000_000_000:.1f} GB",
                "info"
            )

            return {
                "database_bytes": db_size,
                "available_bytes": stat.free,
            }

        except Exception as e:
            self._add_check(
                "Disk Space",
                False,
                f"Error checking disk space: {str(e)}",
                "warning"
            )
            return {}

    def get_full_status(self) -> PostgreSQLHealth:
        """Run all health checks and return comprehensive status.

        Returns:
            PostgreSQLHealth object with all check results and recommendations
        """
        # Run all checks
        connectivity = self.check_connectivity()

        if not connectivity:
            # If can't connect, can't check other things
            return PostgreSQLHealth(
                healthy=False,
                status=HealthStatus.CRITICAL,
                checks=[asdict(c) for c in self.checks],
                error="Cannot connect to PostgreSQL",
                recommendations=self.recommendations,
            )

        db_exists = self.check_database_exists()

        if not db_exists:
            return PostgreSQLHealth(
                healthy=False,
                status=HealthStatus.CRITICAL,
                checks=[asdict(c) for c in self.checks],
                error="Database 'athena' does not exist",
                recommendations=self.recommendations,
            )

        tables = self.check_required_tables()
        permissions = self.check_user_permissions()
        disk = self.check_disk_space()

        # Determine overall status
        all_passed = all(check.passed for check in self.checks)

        if all_passed:
            status = HealthStatus.HEALTHY
            healthy = True
            error = None
        else:
            # Check severity of failures
            critical_failures = [
                check for check in self.checks
                if check.severity == "error"
            ]

            if critical_failures:
                status = HealthStatus.CRITICAL
                healthy = False
                error = f"{len(critical_failures)} critical issue(s)"
            else:
                status = HealthStatus.DEGRADED
                healthy = False
                error = "Some checks failed (non-critical)"

        return PostgreSQLHealth(
            healthy=healthy,
            status=status,
            checks=[asdict(c) for c in self.checks],
            error=error,
            recommendations=self.recommendations,
            stats=disk,
        )


def main():
    """Run health check and print results."""
    import json

    checker = PostgreSQLHealthCheck(verbose=False)
    health = checker.get_full_status()

    # Print results
    print("\n" + "=" * 60)
    print("PostgreSQL Health Check Results")
    print("=" * 60)

    for check in health.checks:
        status = "✓" if check["passed"] else "✗"
        print(f"{status} {check['check_name']}: {check['message']}")

    print("\n" + "-" * 60)

    if health.healthy:
        print("✅ STATUS: HEALTHY")
    elif health.status == HealthStatus.CRITICAL:
        print("🔴 STATUS: CRITICAL")
    else:
        print("🟡 STATUS: DEGRADED")

    if health.error:
        print(f"Error: {health.error}")

    if health.recommendations:
        print("\nRecommendations:")
        for i, rec in enumerate(health.recommendations, 1):
            print(f"  {i}. {rec}")

    if health.stats:
        print("\nDisk Usage:")
        db_mb = health.stats.get("database_bytes", 0) / 1_000_000
        avail_gb = health.stats.get("available_bytes", 0) / 1_000_000_000
        print(f"  Database: {db_mb:.1f} MB")
        print(f"  Available: {avail_gb:.1f} GB")

    print("=" * 60 + "\n")

    # Return exit code
    if health.status == HealthStatus.CRITICAL:
        return 2
    elif health.status == HealthStatus.DEGRADED:
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
