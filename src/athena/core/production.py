"""Production hardening features - advisory locks and resource quotas."""

import time
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any
from dataclasses import dataclass

from .database import Database


@dataclass
class ResourceQuota:
    """Resource quota configuration."""

    resource_type: str
    limit: int
    current_usage: int = 0
    project_id: Optional[int] = None


class AdvisoryLock:
    """Advisory locking for multi-user safety."""

    def __init__(self, db: Database):
        self.db = db
        self._local_locks: Dict[str, int] = {}  # lock_key -> thread_id
        self._lock = threading.RLock()

    def acquire(self, lock_key: str, owner: str, timeout_seconds: int = 30) -> bool:
        """Acquire an advisory lock.

        Args:
            lock_key: Unique lock identifier
            owner: Lock owner identifier
            timeout_seconds: Timeout for lock acquisition

        Returns:
            True if lock acquired, False if timeout
        """
        start_time = time.time()

        with self._lock:
            # Check if we already own this lock
            if lock_key in self._local_locks:
                self._local_locks[lock_key] += 1  # Reference count
                return True

            while time.time() - start_time < timeout_seconds:
                try:
                    cursor = self.db.get_cursor()

                    # Try to insert lock record
                    expires_at = int(time.time()) + 300  # 5 minute default expiry
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO advisory_locks (lock_key, owner, acquired_at, expires_at)
                        VALUES (?, ?, ?, ?)
                    """,
                        (lock_key, owner, int(time.time()), expires_at),
                    )

                    if cursor.rowcount > 0:
                        # Lock acquired
                        # commit handled by cursor context
                        self._local_locks[lock_key] = threading.get_ident()
                        return True

                    # Check if existing lock is expired
                    cursor.execute(
                        """
                        SELECT owner, expires_at FROM advisory_locks
                        WHERE lock_key = ?
                    """,
                        (lock_key,),
                    )

                    row = cursor.fetchone()
                    if row and time.time() > row[1]:
                        # Lock is expired, try to take it
                        cursor.execute(
                            """
                            UPDATE advisory_locks
                            SET owner = ?, acquired_at = ?, expires_at = ?
                            WHERE lock_key = ? AND expires_at < ?
                        """,
                            (owner, int(time.time()), expires_at, lock_key, time.time()),
                        )

                        if cursor.rowcount > 0:
                            # commit handled by cursor context
                            self._local_locks[lock_key] = threading.get_ident()
                            return True

                except (OSError, ValueError, TypeError, KeyError):
                    pass  # Retry on database errors

                # Wait before retry
                time.sleep(0.1)

            return False

    def release(self, lock_key: str) -> bool:
        """Release an advisory lock.

        Args:
            lock_key: Lock identifier

        Returns:
            True if lock released, False if not owned by this instance
        """
        with self._lock:
            if lock_key not in self._local_locks:
                return False

            self._local_locks[lock_key] -= 1

            if self._local_locks[lock_key] > 0:
                # Still referenced, don't release
                return True

            # Remove from local tracking
            del self._local_locks[lock_key]

            try:
                cursor = self.db.get_cursor()
                cursor.execute(
                    """
                    DELETE FROM advisory_locks
                    WHERE lock_key = ?
                """,
                    (lock_key,),
                )
                # commit handled by cursor context
                return True
            except (OSError, ValueError, TypeError, KeyError):
                return False

    @contextmanager
    def lock(self, lock_key: str, owner: str, timeout_seconds: int = 30):
        """Context manager for advisory locks.

        Args:
            lock_key: Lock identifier
            owner: Lock owner
            timeout_seconds: Acquisition timeout

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        if not self.acquire(lock_key, owner, timeout_seconds):
            raise TimeoutError(f"Could not acquire lock '{lock_key}' within {timeout_seconds}s")

        try:
            yield
        finally:
            self.release(lock_key)

    def cleanup_expired(self):
        """Clean up expired locks.

        DESIGN: Cleanup errors are logged but don't crash (background maintenance).
        However, errors ARE VISIBLE in logs so issues can be debugged.
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                DELETE FROM advisory_locks
                WHERE expires_at < ?
            """,
                (time.time(),),
            )
            # commit handled by cursor context
        except (OSError, ValueError, TypeError, KeyError) as e:
            # Cleanup is best-effort (background maintenance), but we log failures
            # so they're visible for debugging database/permission issues
            logger.warning(
                f"Failed to cleanup expired advisory locks: {type(e).__name__}: {e}. "
                f"This may indicate database issues or permission problems."
            )


class ResourceManager:
    """Resource quota management."""

    def __init__(self, db: Database):
        self.db = db

    def set_quota(self, quota: ResourceQuota):
        """Set or update a resource quota.

        Args:
            quota: Quota configuration
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO resource_quotas
            (project_id, resource_type, quota_limit, current_usage, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                quota.project_id,
                quota.resource_type,
                quota.limit,
                quota.current_usage,
                int(time.time()),
            ),
        )

        # commit handled by cursor context

    def get_quota(
        self, resource_type: str, project_id: Optional[int] = None
    ) -> Optional[ResourceQuota]:
        """Get current quota for a resource.

        Args:
            resource_type: Type of resource
            project_id: Project ID (None for global)

        Returns:
            Current quota or None if not set
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            SELECT project_id, resource_type, quota_limit, current_usage, last_updated
            FROM resource_quotas
            WHERE resource_type = ? AND (project_id = ? OR project_id IS NULL)
            ORDER BY project_id NULLS LAST  -- Prefer project-specific over global
            LIMIT 1
        """,
            (resource_type, project_id),
        )

        row = cursor.fetchone()
        if not row:
            return None

        return ResourceQuota(
            project_id=row[0], resource_type=row[1], limit=row[2], current_usage=row[3]
        )

    def check_quota(
        self, resource_type: str, amount: int = 1, project_id: Optional[int] = None
    ) -> bool:
        """Check if quota allows the requested amount.

        Args:
            resource_type: Type of resource
            amount: Amount requested
            project_id: Project ID

        Returns:
            True if quota allows, False if exceeded
        """
        quota = self.get_quota(resource_type, project_id)
        if not quota:
            return True  # No quota set, allow

        return quota.current_usage + amount <= quota.limit

    def allocate_resource(
        self, resource_type: str, amount: int = 1, project_id: Optional[int] = None
    ) -> bool:
        """Allocate resource usage.

        Args:
            resource_type: Type of resource
            amount: Amount to allocate
            project_id: Project ID

        Returns:
            True if allocated, False if quota exceeded
        """
        if not self.check_quota(resource_type, amount, project_id):
            return False

        cursor = self.db.get_cursor()

        # Update or insert usage
        cursor.execute(
            """
            INSERT OR REPLACE INTO resource_quotas
            (project_id, resource_type, quota_limit, current_usage, last_updated)
            VALUES (
                ?,
                ?,
                COALESCE((SELECT quota_limit FROM resource_quotas
                         WHERE resource_type = ? AND (project_id = ? OR project_id IS NULL)
                         ORDER BY project_id NULLS LAST LIMIT 1), 0),
                COALESCE((SELECT current_usage FROM resource_quotas
                         WHERE resource_type = ? AND (project_id = ? OR project_id IS NULL)
                         ORDER BY project_id NULLS LAST LIMIT 1), 0) + ?,
                ?
            )
        """,
            (
                project_id,
                resource_type,
                resource_type,
                project_id,
                resource_type,
                project_id,
                amount,
                int(time.time()),
            ),
        )

        # commit handled by cursor context

        # Log the allocation
        self._log_usage(resource_type, amount, project_id, "allocate")

        return True

    def release_resource(
        self, resource_type: str, amount: int = 1, project_id: Optional[int] = None
    ):
        """Release allocated resource usage.

        Args:
            resource_type: Type of resource
            amount: Amount to release
            project_id: Project ID
        """
        cursor = self.db.get_cursor()

        cursor.execute(
            """
            UPDATE resource_quotas
            SET current_usage = MAX(0, current_usage - ?), last_updated = ?
            WHERE resource_type = ? AND (project_id = ? OR project_id IS NULL)
        """,
            (amount, int(time.time()), resource_type, project_id),
        )

        # commit handled by cursor context

        # Log the release
        self._log_usage(resource_type, -amount, project_id, "release")

    def _log_usage(
        self, resource_type: str, amount: int, project_id: Optional[int], operation: str
    ):
        """Log resource usage change.

        Args:
            resource_type: Type of resource
            amount: Amount changed (positive for allocate, negative for release)
            project_id: Project ID
            operation: Operation type

        DESIGN: Audit logging errors are visible but don't crash resource operations.
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            cursor = self.db.get_cursor()
            cursor.execute(
                """
                INSERT INTO resource_usage_log
                (project_id, resource_type, operation, amount, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """,
                (project_id, resource_type, operation, amount, int(time.time())),
            )
            # commit handled by cursor context
        except (OSError, ValueError, TypeError, KeyError) as e:
            # Audit logging is best-effort (doesn't affect resource operations)
            # but we log failures so they're visible for debugging
            logger.warning(
                f"Failed to log resource {operation} "
                f"(resource={resource_type}, amount={amount}): "
                f"{type(e).__name__}: {e}"
            )

    def get_usage_stats(self, project_id: Optional[int] = None, hours: int = 24) -> Dict[str, Any]:
        """Get resource usage statistics.

        Args:
            project_id: Project ID filter
            hours: Hours to look back

        Returns:
            Usage statistics
        """
        cursor = self.db.get_cursor()
        since_time = int(time.time()) - (hours * 3600)

        # Current quotas
        cursor.execute(
            """
            SELECT resource_type, quota_limit, current_usage
            FROM resource_quotas
            WHERE (? IS NULL OR project_id = ?) AND quota_limit > 0
        """,
            (project_id, project_id),
        )

        quotas = {}
        for row in cursor.fetchall():
            quotas[row[0]] = {
                "limit": row[1],
                "current": row[2],
                "utilization": row[2] / row[1] if row[1] > 0 else 0,
            }

        # Usage over time
        cursor.execute(
            """
            SELECT resource_type, operation, SUM(amount) as total_amount, COUNT(*) as operations
            FROM resource_usage_log
            WHERE timestamp >= ? AND (? IS NULL OR project_id = ?)
            GROUP BY resource_type, operation
        """,
            (since_time, project_id, project_id),
        )

        usage = {}
        for row in cursor.fetchall():
            resource_type = row[0]
            if resource_type not in usage:
                usage[resource_type] = {"allocate": 0, "release": 0, "net": 0, "operations": 0}

            usage[resource_type][row[1]] = row[2]
            usage[resource_type]["operations"] += row[3]

        # Calculate net usage
        for resource_type, stats in usage.items():
            stats["net"] = stats["allocate"] - stats["release"]

        return {"quotas": quotas, "usage": usage, "period_hours": hours}


# Global instances for easy access
_advisory_lock_instance: Optional[AdvisoryLock] = None
_resource_manager_instance: Optional[ResourceManager] = None


def get_advisory_lock(db: Database) -> AdvisoryLock:
    """Get global advisory lock instance."""
    global _advisory_lock_instance
    if _advisory_lock_instance is None:
        _advisory_lock_instance = AdvisoryLock(db)
    return _advisory_lock_instance


def get_resource_manager(db: Database) -> ResourceManager:
    """Get global resource manager instance."""
    global _resource_manager_instance
    if _resource_manager_instance is None:
        _resource_manager_instance = ResourceManager(db)
    return _resource_manager_instance
