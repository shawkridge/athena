"""Batch operations for high-throughput database operations."""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional

from athena.core.database import Database
from athena.core.exceptions import TransactionError

logger = logging.getLogger(__name__)


class BatchOperation:
    """Single batch operation for deferred execution."""

    def __init__(self, operation_type: str, sql: str, params: list, description: str = ""):
        """Initialize batch operation.

        Args:
            operation_type: Type of operation (INSERT, UPDATE, DELETE)
            sql: SQL statement
            params: Parameter list
            description: Human-readable description
        """
        self.operation_type = operation_type
        self.sql = sql
        self.params = params
        self.description = description
        self.created_at = datetime.now()

    def __repr__(self) -> str:
        return f"<BatchOp {self.operation_type}: {self.description}>"


class BatchExecutor:
    """Executor for batch database operations."""

    def __init__(self, db: Database, batch_size: int = 1000, auto_commit: bool = True):
        """Initialize batch executor.

        Args:
            db: Database connection
            batch_size: Number of operations per batch (default: 1000)
            auto_commit: Auto-commit when batch fills
        """
        self.db = db
        self.batch_size = batch_size
        self.auto_commit = auto_commit
        self.operations: list[BatchOperation] = []
        self.stats = {
            "total_operations": 0,
            "batches_executed": 0,
            "total_time_ms": 0,
            "operations_per_second": 0,
        }

    def add_insert(self, sql: str, params: list, description: str = "") -> "BatchExecutor":
        """Add INSERT operation to batch.

        Args:
            sql: SQL INSERT statement
            params: Parameter list
            description: Operation description

        Returns:
            Self for chaining
        """
        self.operations.append(BatchOperation("INSERT", sql, params, description))

        if self.auto_commit and len(self.operations) >= self.batch_size:
            self.execute()

        return self

    def add_update(self, sql: str, params: list, description: str = "") -> "BatchExecutor":
        """Add UPDATE operation to batch.

        Args:
            sql: SQL UPDATE statement
            params: Parameter list
            description: Operation description

        Returns:
            Self for chaining
        """
        self.operations.append(BatchOperation("UPDATE", sql, params, description))

        if self.auto_commit and len(self.operations) >= self.batch_size:
            self.execute()

        return self

    def add_delete(self, sql: str, params: list, description: str = "") -> "BatchExecutor":
        """Add DELETE operation to batch.

        Args:
            sql: SQL DELETE statement
            params: Parameter list
            description: Operation description

        Returns:
            Self for chaining
        """
        self.operations.append(BatchOperation("DELETE", sql, params, description))

        if self.auto_commit and len(self.operations) >= self.batch_size:
            self.execute()

        return self

    def add_operation(self, operation: BatchOperation) -> "BatchExecutor":
        """Add pre-built operation to batch.

        Args:
            operation: BatchOperation instance

        Returns:
            Self for chaining
        """
        self.operations.append(operation)

        if self.auto_commit and len(self.operations) >= self.batch_size:
            self.execute()

        return self

    def execute(self, silent: bool = False) -> dict:
        """Execute all pending operations in a transaction.

        Args:
            silent: Don't print progress

        Returns:
            Execution statistics
        """
        if not self.operations:
            return {
                "success": True,
                "operations": 0,
                "time_ms": 0,
                "throughput": 0,
            }

        start_time = time.time()

        try:
            cursor = self.db.get_cursor()

            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")

            # Execute all operations
            for op in self.operations:
                cursor.execute(op.sql, op.params)

            # Commit transaction
            cursor.execute("COMMIT")
            # commit handled by cursor context

            elapsed_ms = (time.time() - start_time) * 1000
            throughput = len(self.operations) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

            # Update stats
            self.stats["total_operations"] += len(self.operations)
            self.stats["batches_executed"] += 1
            self.stats["total_time_ms"] += elapsed_ms
            self.stats["operations_per_second"] = (
                self.stats["total_operations"] / (self.stats["total_time_ms"] / 1000)
                if self.stats["total_time_ms"] > 0
                else 0
            )

            if not silent:
                print(
                    f"✓ Executed {len(self.operations)} operations in {elapsed_ms:.2f}ms "
                    f"({throughput:.0f} ops/sec)"
                )

            # Clear operations
            self.operations.clear()

            return {
                "success": True,
                "operations": len(self.operations),
                "time_ms": elapsed_ms,
                "throughput": throughput,
            }

        except Exception as e:
            try:
                cursor.execute("ROLLBACK")
            except (TransactionError, Exception) as rollback_error:
                logger.debug(f"ROLLBACK failed during batch error handling: {rollback_error}")

            print(f"✗ Batch execution failed: {e}")

            return {
                "success": False,
                "error": str(e),
                "operations": len(self.operations),
            }

    def pending_count(self) -> int:
        """Get number of pending operations.

        Returns:
            Count of pending operations
        """
        return len(self.operations)

    def get_stats(self) -> dict:
        """Get execution statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()

    def clear(self):
        """Clear pending operations without executing."""
        self.operations.clear()


class BulkInsertBuilder:
    """Builder for efficient bulk inserts."""

    def __init__(self, table: str, columns: list[str], batch_size: int = 1000):
        """Initialize bulk insert builder.

        Args:
            table: Table name
            columns: Column names
            batch_size: Batch size for execution
        """
        self.table = table
        self.columns = columns
        self.batch_size = batch_size
        self.rows: list[tuple] = []

    def add_row(self, *values) -> "BulkInsertBuilder":
        """Add row to insert.

        Args:
            *values: Column values in order

        Returns:
            Self for chaining
        """
        if len(values) != len(self.columns):
            raise ValueError(f"Expected {len(self.columns)} values, got {len(values)}")

        self.rows.append(tuple(values))
        return self

    def add_rows(self, rows: list[tuple]) -> "BulkInsertBuilder":
        """Add multiple rows to insert.

        Args:
            rows: List of row tuples

        Returns:
            Self for chaining
        """
        for row in rows:
            self.add_row(*row)

        return self

    def build_sql(self) -> str:
        """Build INSERT SQL for current rows.

        Returns:
            SQL statement
        """
        if not self.rows:
            return ""

        col_list = ", ".join(self.columns)
        placeholders = ", ".join(["?" for _ in self.columns])

        return f"INSERT INTO {self.table} ({col_list}) VALUES ({placeholders})"

    def get_batch_parameters(self) -> list[tuple]:
        """Get all row parameters.

        Returns:
            List of parameter tuples
        """
        return self.rows.copy()

    def execute(self, db: Database) -> dict:
        """Execute bulk insert.

        Args:
            db: Database connection

        Returns:
            Execution statistics
        """
        if not self.rows:
            return {"success": True, "rows": 0, "time_ms": 0}

        start_time = time.time()
        sql = self.build_sql()

        try:
            cursor = db.conn.cursor()
            cursor.execute("BEGIN TRANSACTION")

            for row in self.rows:
                cursor.execute(sql, row)

            cursor.execute("COMMIT")
            db.conn.commit()

            elapsed_ms = (time.time() - start_time) * 1000
            throughput = len(self.rows) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

            print(
                f"✓ Inserted {len(self.rows)} rows into {self.table} "
                f"in {elapsed_ms:.2f}ms ({throughput:.0f} rows/sec)"
            )

            return {
                "success": True,
                "rows": len(self.rows),
                "time_ms": elapsed_ms,
                "throughput": throughput,
            }

        except Exception as e:
            try:
                cursor.execute("ROLLBACK")
            except (TransactionError, Exception) as rollback_error:
                logger.debug(f"ROLLBACK failed during bulk insert error handling: {rollback_error}")

            print(f"✗ Bulk insert failed: {e}")

            return {
                "success": False,
                "error": str(e),
                "rows": len(self.rows),
            }

    def clear(self):
        """Clear all pending rows."""
        self.rows.clear()


class BatchProcessor:
    """Process items in batches with custom callback."""

    def __init__(self, items: list[Any], batch_size: int = 100):
        """Initialize batch processor.

        Args:
            items: Items to process
            batch_size: Batch size
        """
        self.items = items
        self.batch_size = batch_size

    def process(self, callback: Callable[[list[Any]], None]) -> dict:
        """Process items in batches.

        Args:
            callback: Function to call for each batch

        Returns:
            Processing statistics
        """
        total_batches = (len(self.items) + self.batch_size - 1) // self.batch_size
        start_time = time.time()

        for i in range(total_batches):
            start_idx = i * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(self.items))

            batch = self.items[start_idx:end_idx]
            callback(batch)

        elapsed_ms = (time.time() - start_time) * 1000
        throughput = len(self.items) / (elapsed_ms / 1000) if elapsed_ms > 0 else 0

        return {
            "total_items": len(self.items),
            "batch_size": self.batch_size,
            "total_batches": total_batches,
            "time_ms": elapsed_ms,
            "throughput": throughput,
        }
