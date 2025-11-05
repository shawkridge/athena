#!/usr/bin/env python3
"""
Hook Result Cache - Phase 8 Implementation

Caches hook execution results to avoid redundant computations.

Features:
- Result caching with TTL (time-to-live)
- Input hashing for cache keys
- Cache invalidation patterns
- Configurable per-hook TTL
- Metrics tracking

Usage:
    cache = HookResultCache()

    # Check for cached result
    result = cache.get_cached_result("user-prompt-submit", input_hash)
    if result:
        return result

    # Store result
    cache.store_result("user-prompt-submit", input_hash, result, ttl_seconds=60)

    # Invalidate on condition
    cache.invalidate_on_pattern("user-prompt-*")
"""

import json
import hashlib
import logging
import time
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import sqlite3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hook_cache")


@dataclass
class CacheEntry:
    """Single cache entry"""
    hook_name: str
    input_hash: str
    result: str  # JSON-serialized
    created_at: int
    expires_at: int
    hit_count: int = 0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return time.time() > self.expires_at

    def to_dict(self):
        return asdict(self)


@dataclass
class CacheStats:
    """Cache statistics"""
    total_entries: int
    total_hits: int
    total_misses: int
    expired_entries: int
    total_size_bytes: int
    avg_hit_rate: float

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate"""
        total = self.total_hits + self.total_misses
        return self.total_hits / total if total > 0 else 0.0


class HookResultCache:
    """
    Caches hook execution results

    Storage: SQLite database (~/.claude/hook_cache.db)
    """

    def __init__(self, db_path: Optional[str] = None, config_path: Optional[str] = None):
        """
        Initialize cache

        Args:
            db_path: Path to SQLite cache database
            config_path: Path to cache configuration JSON
        """
        if db_path is None:
            db_path = str(Path.home() / ".claude" / "hook_cache.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.config = self._load_config(config_path) if config_path else {
            "enabled": True,
            "ttl_default": 30,  # seconds
            "hooks": {}
        }

        self.conn = sqlite3.connect(str(self.db_path))
        self._ensure_schema()

        # Stats tracking
        self.hits = 0
        self.misses = 0

    def _load_config(self, config_path: str) -> Dict:
        """Load cache configuration"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"Failed to load config: {config_path}, using defaults")
            return {"enabled": True, "ttl_default": 30, "hooks": {}}

    def _ensure_schema(self):
        """Create cache table if needed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hook_cache (
                id INTEGER PRIMARY KEY,
                hook_name TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                hit_count INTEGER DEFAULT 0,
                size_bytes INTEGER DEFAULT 0,
                UNIQUE(hook_name, input_hash)
            )
        """)

        # Create stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_stats (
                hook_name TEXT PRIMARY KEY,
                hits INTEGER DEFAULT 0,
                misses INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0
            )
        """)

        self.conn.commit()

    def get_cached_result(self, hook_name: str, input_hash: str) -> Optional[str]:
        """
        Get cached result if available and not expired

        Args:
            hook_name: Name of hook
            input_hash: Hash of hook input

        Returns:
            Cached result JSON string, or None if not found/expired
        """
        if not self.config.get("enabled", True):
            return None

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT result, expires_at, hit_count FROM hook_cache
                WHERE hook_name = ? AND input_hash = ?
                LIMIT 1
            """, (hook_name, input_hash))

            row = cursor.fetchone()
            if not row:
                self.misses += 1
                self._record_miss(hook_name)
                return None

            result, expires_at, hit_count = row

            # Check if expired
            if time.time() > expires_at:
                logger.debug(f"Cache miss for {hook_name}: entry expired")
                self.misses += 1
                self._record_miss(hook_name)
                self._delete_entry(hook_name, input_hash)
                return None

            # Update hit count
            new_hit_count = hit_count + 1
            cursor.execute("""
                UPDATE hook_cache SET hit_count = ? WHERE hook_name = ? AND input_hash = ?
            """, (new_hit_count, hook_name, input_hash))
            self.conn.commit()

            self.hits += 1
            self._record_hit(hook_name)
            logger.debug(f"Cache hit for {hook_name} (hit_count={new_hit_count})")

            return result

        except sqlite3.Error as e:
            logger.error(f"Cache lookup error: {e}")
            return None

    def store_result(self, hook_name: str, input_hash: str, result: str,
                    ttl_seconds: Optional[int] = None) -> bool:
        """
        Store hook execution result

        Args:
            hook_name: Name of hook
            input_hash: Hash of hook input
            result: JSON-serialized result
            ttl_seconds: Time-to-live in seconds (uses config default if None)

        Returns:
            True if stored successfully
        """
        if not self.config.get("enabled", True):
            return False

        # Get TTL from config or use provided
        if ttl_seconds is None:
            hook_config = self.config.get("hooks", {}).get(hook_name, {})
            ttl_seconds = hook_config.get("ttl", self.config.get("ttl_default", 30))

        now = time.time()
        expires_at = int(now + ttl_seconds)
        size_bytes = len(result.encode('utf-8'))

        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO hook_cache
                (hook_name, input_hash, result, created_at, expires_at, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (hook_name, input_hash, result, int(now), expires_at, size_bytes))

            self.conn.commit()
            logger.debug(f"Cached result for {hook_name} (ttl={ttl_seconds}s)")
            return True

        except sqlite3.Error as e:
            logger.error(f"Cache store error: {e}")
            return False

    def invalidate_on_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern

        Uses SQL LIKE pattern matching.

        Examples:
            "user-prompt-*" -> invalidates all user-prompt-* hooks
            "post-*" -> invalidates all post-* hooks
            "%" -> invalidates all entries

        Args:
            pattern: SQL LIKE pattern

        Returns:
            Number of entries invalidated
        """
        try:
            cursor = self.conn.cursor()

            # Convert shell glob to SQL LIKE
            sql_pattern = pattern.replace("*", "%")

            cursor.execute("""
                DELETE FROM hook_cache WHERE hook_name LIKE ?
            """, (sql_pattern,))

            self.conn.commit()
            count = cursor.rowcount
            logger.info(f"Invalidated {count} cache entries for pattern: {pattern}")
            return count

        except sqlite3.Error as e:
            logger.error(f"Invalidation error: {e}")
            return 0

    def invalidate_expired(self) -> int:
        """
        Remove all expired entries from cache

        Returns:
            Number of entries removed
        """
        try:
            cursor = self.conn.cursor()
            now = int(time.time())

            cursor.execute("""
                DELETE FROM hook_cache WHERE expires_at <= ?
            """, (now,))

            self.conn.commit()
            count = cursor.rowcount
            logger.info(f"Cleaned up {count} expired cache entries")
            return count

        except sqlite3.Error as e:
            logger.error(f"Cleanup error: {e}")
            return 0

    def clear_cache(self, hook_name: Optional[str] = None) -> int:
        """
        Clear cache entries

        Args:
            hook_name: Clear specific hook cache (None = clear all)

        Returns:
            Number of entries removed
        """
        try:
            cursor = self.conn.cursor()

            if hook_name:
                cursor.execute("DELETE FROM hook_cache WHERE hook_name = ?", (hook_name,))
                logger.info(f"Cleared cache for {hook_name}")
            else:
                cursor.execute("DELETE FROM hook_cache")
                logger.info("Cleared all cache entries")

            self.conn.commit()
            return cursor.rowcount

        except sqlite3.Error as e:
            logger.error(f"Clear error: {e}")
            return 0

    def _delete_entry(self, hook_name: str, input_hash: str):
        """Delete single cache entry"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM hook_cache WHERE hook_name = ? AND input_hash = ?
            """, (hook_name, input_hash))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def _record_hit(self, hook_name: str):
        """Record cache hit for stats"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO cache_stats (hook_name, hits, misses)
                VALUES (?, 1, 0)
                ON CONFLICT(hook_name) DO UPDATE SET hits = hits + 1
            """, (hook_name,))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def _record_miss(self, hook_name: str):
        """Record cache miss for stats"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO cache_stats (hook_name, hits, misses)
                VALUES (?, 0, 1)
                ON CONFLICT(hook_name) DO UPDATE SET misses = misses + 1
            """, (hook_name,))
            self.conn.commit()
        except sqlite3.Error:
            pass

    def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        try:
            cursor = self.conn.cursor()

            # Get entry count and sizes
            cursor.execute("SELECT COUNT(*), SUM(size_bytes) FROM hook_cache")
            total_entries, total_size = cursor.fetchone()
            total_entries = total_entries or 0
            total_size = total_size or 0

            # Get expired count
            cursor.execute("""
                SELECT COUNT(*) FROM hook_cache WHERE expires_at <= ?
            """, (int(time.time()),))
            expired_count = cursor.fetchone()[0]

            # Get hit/miss totals
            cursor.execute("""
                SELECT SUM(hits), SUM(misses) FROM cache_stats
            """)
            total_hits, total_misses = cursor.fetchone()
            total_hits = total_hits or 0
            total_misses = total_misses or 0

            total_requests = total_hits + total_misses
            avg_hit_rate = (total_hits / total_requests
                           if total_requests > 0 else 0.0)

            return CacheStats(
                total_entries=total_entries,
                total_hits=total_hits,
                total_misses=total_misses,
                expired_entries=expired_count,
                total_size_bytes=total_size,
                avg_hit_rate=avg_hit_rate
            )

        except sqlite3.Error as e:
            logger.error(f"Stats error: {e}")
            return CacheStats(0, 0, 0, 0, 0, 0.0)

    def close(self):
        """Close cache database connection"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        self.close()


def compute_input_hash(hook_input: Dict) -> str:
    """
    Compute hash of hook input for cache key

    Args:
        hook_input: Hook input dictionary

    Returns:
        SHA256 hash of input JSON
    """
    input_json = json.dumps(hook_input, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(input_json.encode()).hexdigest()[:16]


def main():
    """CLI for cache management"""
    import argparse

    parser = argparse.ArgumentParser(description="Hook Result Cache Manager")
    parser.add_argument("--db", help="Path to cache database")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--clear", action="store_true", help="Clear all cache")
    parser.add_argument("--clear-hook", help="Clear cache for specific hook")
    parser.add_argument("--invalidate", help="Invalidate entries matching pattern")
    parser.add_argument("--cleanup", action="store_true", help="Remove expired entries")

    args = parser.parse_args()

    cache = HookResultCache(args.db)

    if args.stats:
        stats = cache.get_stats()
        print(json.dumps(asdict(stats), indent=2))

    elif args.clear:
        count = cache.clear_cache()
        print(f"Cleared {count} cache entries")

    elif args.clear_hook:
        count = cache.clear_cache(args.clear_hook)
        print(f"Cleared {count} entries for {args.clear_hook}")

    elif args.invalidate:
        count = cache.invalidate_on_pattern(args.invalidate)
        print(f"Invalidated {count} entries for pattern: {args.invalidate}")

    elif args.cleanup:
        count = cache.invalidate_expired()
        print(f"Cleaned up {count} expired entries")

    else:
        parser.print_help()

    cache.close()


if __name__ == "__main__":
    main()
