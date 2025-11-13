/**
 * Athena Local Cache - Simplified for AI-First Development
 *
 * Intelligent result caching with:
 * - LRU eviction for memory efficiency
 * - TTL-based expiration
 * - Smart invalidation on writes
 * - Zero HTTP overhead (local only)
 *
 * Expected improvements:
 * - 5-10x throughput for repeated queries
 * - Sub-10ms latency for cache hits
 * - 75%+ hit rate for typical workloads
 */

/**
 * Single cache entry
 */
interface CacheEntry<T = unknown> {
  value: T;
  timestamp: number;
  ttl: number;
  hits: number;
  tags: Set<string>;
}

/**
 * Cache statistics
 */
interface CacheStats {
  hitCount: number;
  missCount: number;
  hitRate: number;
  itemCount: number;
  memoryUsedMb: number;
}

/**
 * Local Cache - Optimized for single-user development
 *
 * No connection pooling, no distributed concerns, just pure performance.
 */
export class LocalCache {
  private cache = new Map<string, CacheEntry>();
  private accessOrder: string[] = [];
  private maxSize: number;
  private defaultTtl: number;
  private stats = {
    hitCount: 0,
    missCount: 0,
    itemCount: 0,
    memoryUsedBytes: 0
  };

  /**
   * Create local cache instance
   *
   * @param maxSize - Maximum number of entries (default 50K)
   * @param defaultTtlMs - Default time-to-live in milliseconds (default 5 min)
   */
  constructor(maxSize: number = 50000, defaultTtlMs: number = 5 * 60 * 1000) {
    this.maxSize = maxSize;
    this.defaultTtl = defaultTtlMs;
  }

  /**
   * Get value from cache
   *
   * @example
   *   const result = cache.get('recall:{"query":"test"}');
   *   if (result) {
   *     return result;
   *   }
   */
  get<T = unknown>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      this.stats.missCount++;
      return null;
    }

    // Check expiration
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key);
      this.stats.memoryUsedBytes -= JSON.stringify(entry.value).length;
      this.stats.itemCount--;
      this.stats.missCount++;
      return null;
    }

    // Cache hit
    this.stats.hitCount++;
    entry.hits++;
    this.updateAccessOrder(key);

    return entry.value as T;
  }

  /**
   * Set value in cache
   *
   * @example
   *   cache.set(
   *     'recall:{"query":"test"}',
   *     [memory1, memory2],
   *     5 * 60 * 1000,
   *     ['episodic/recall', 'query:test']
   *   );
   */
  set<T = unknown>(
    key: string,
    value: T,
    ttl: number = this.defaultTtl,
    tags: string[] = []
  ): void {
    const size = JSON.stringify(value).length;

    // Evict if needed
    if (this.cache.size >= this.maxSize) {
      this.evictLRU();
    }

    // Remove old entry if exists
    if (this.cache.has(key)) {
      const old = this.cache.get(key)!;
      this.stats.memoryUsedBytes -= JSON.stringify(old.value).length;
    }

    // Add entry
    const entry: CacheEntry<T> = {
      value,
      timestamp: Date.now(),
      ttl,
      hits: 0,
      tags: new Set(tags)
    };

    this.cache.set(key, entry);
    this.stats.memoryUsedBytes += size;
    this.stats.itemCount++;
    this.updateAccessOrder(key);
  }

  /**
   * Clear all cache
   */
  clear(): void {
    this.cache.clear();
    this.accessOrder = [];
    this.stats = {
      hitCount: 0,
      missCount: 0,
      itemCount: 0,
      memoryUsedBytes: 0
    };
  }

  /**
   * Invalidate cache by operation
   *
   * When a write operation happens, invalidate related caches.
   *
   * @example
   *   // After remember() call
   *   cache.invalidateByOperation('episodic/remember');
   *   // Clears: recall, getRecent, queryTemporal caches
   */
  invalidateByOperation(operation: string): number {
    const invalidationMap: Record<string, string[]> = {
      'episodic/remember': ['episodic/recall', 'episodic/getRecent', 'episodic/queryTemporal'],
      'semantic/store': ['semantic/search', 'semantic/semanticSearch', 'semantic/keywordSearch', 'semantic/hybridSearch'],
      'episodic/forget': ['episodic/listEvents', 'episodic/recall'],
      'semantic/update': ['semantic/search', 'semantic/list'],
      'prospective/createTask': ['prospective/listTasks', 'prospective/getPendingTasks'],
      'prospective/completeGoal': ['meta/getProgressMetrics', 'prospective/listGoals']
    };

    const affectedOps = invalidationMap[operation] || [];
    let cleared = 0;

    for (const affectedOp of affectedOps) {
      for (const [key] of this.cache) {
        if (key.startsWith(affectedOp + ':')) {
          const entry = this.cache.get(key)!;
          this.cache.delete(key);
          this.stats.memoryUsedBytes -= JSON.stringify(entry.value).length;
          this.stats.itemCount--;
          cleared++;
        }
      }
    }

    return cleared;
  }

  /**
   * Invalidate by tag
   *
   * @example
   *   cache.invalidateByTag('user-data');
   */
  invalidateByTag(tag: string): number {
    let cleared = 0;
    const keysToDelete: string[] = [];

    for (const [key, entry] of this.cache) {
      if (entry.tags.has(tag)) {
        keysToDelete.push(key);
        cleared++;
      }
    }

    for (const key of keysToDelete) {
      const entry = this.cache.get(key)!;
      this.cache.delete(key);
      this.stats.memoryUsedBytes -= JSON.stringify(entry.value).length;
    }

    this.stats.itemCount -= cleared;
    return cleared;
  }

  /**
   * Get cache statistics
   *
   * @example
   *   const stats = cache.getStats();
   *   console.log(`Hit rate: ${(stats.hitRate * 100).toFixed(1)}%`);
   */
  getStats(): CacheStats {
    const total = this.stats.hitCount + this.stats.missCount;
    const hitRate = total > 0 ? this.stats.hitCount / total : 0;

    return {
      hitCount: this.stats.hitCount,
      missCount: this.stats.missCount,
      hitRate,
      itemCount: this.stats.itemCount,
      memoryUsedMb: this.stats.memoryUsedBytes / 1024 / 1024
    };
  }

  /**
   * Warm cache with frequently used queries
   *
   * Pre-populate cache with common queries to eliminate first-query latency.
   *
   * @example
   *   cache.warmCache([
   *     { key: 'recall:{"query":"database"}', value: [...] },
   *     { key: 'search:{"query":"optimization"}', value: [...] }
   *   ]);
   */
  warmCache(entries: Array<{key: string; value: unknown; ttl?: number}>): void {
    for (const entry of entries) {
      this.set(entry.key, entry.value, entry.ttl);
    }
  }

  /**
   * Get detailed stats for monitoring
   */
  getDetailedStats() {
    const sorted = Array.from(this.cache.entries())
      .sort((a, b) => b[1].hits - a[1].hits)
      .slice(0, 10);

    const topKeys = sorted.map(([key, entry]) => ({
      key,
      hits: entry.hits,
      age: Date.now() - entry.timestamp,
      size: JSON.stringify(entry.value).length
    }));

    return {
      ...this.getStats(),
      topKeys,
      oldestEntry: this.accessOrder.length > 0
        ? Date.now() - (this.cache.get(this.accessOrder[0])?.timestamp || 0)
        : 0
    };
  }

  /**
   * Private: Update access order for LRU
   */
  private updateAccessOrder(key: string): void {
    this.accessOrder = this.accessOrder.filter(k => k !== key);
    this.accessOrder.push(key);
  }

  /**
   * Private: Evict least recently used entry
   */
  private evictLRU(): void {
    if (this.accessOrder.length > 0) {
      const oldestKey = this.accessOrder.shift()!;
      const entry = this.cache.get(oldestKey);
      if (entry) {
        this.cache.delete(oldestKey);
        this.stats.memoryUsedBytes -= JSON.stringify(entry.value).length;
        this.stats.itemCount--;
      }
    }
  }
}

/**
 * Wrapped operation executor with automatic caching
 *
 * Transparently caches operation results.
 *
 * @example
 *   const cached = new CachedExecutor(cache);
 *   const result = await cached.execute(
 *     'episodic/recall',
 *     { query: 'test', limit: 10 },
 *     (op, params) => callOperation(op, params)
 *   );
 */
export class CachedExecutor {
  constructor(private cache: LocalCache) {}

  /**
   * Execute operation with caching
   */
  async execute<T = unknown>(
    operation: string,
    params: Record<string, unknown>,
    executor: (op: string, params: Record<string, unknown>) => Promise<T>
  ): Promise<T> {
    const key = this.buildCacheKey(operation, params);

    // Check cache for read operations
    if (this.isReadOperation(operation)) {
      const cached = this.cache.get<T>(key);
      if (cached !== null) {
        return cached;
      }
    }

    // Execute operation
    const result = await executor(operation, params);

    // Cache result if appropriate
    if (this.isCacheable(operation)) {
      const ttl = this.getTTL(operation);
      const tags = [operation, ...this.extractTags(operation, params)];

      if (ttl > 0) {
        this.cache.set(key, result, ttl, tags);
      }
    }

    // Invalidate related caches after writes
    if (this.isWriteOperation(operation)) {
      this.cache.invalidateByOperation(operation);
    }

    return result;
  }

  /**
   * Check if operation is read-only
   */
  private isReadOperation(operation: string): boolean {
    const readPrefixes = ['recall', 'search', 'list', 'get', 'find', 'analyze'];
    return readPrefixes.some(p => operation.toLowerCase().includes(p));
  }

  /**
   * Check if operation modifies state
   */
  private isWriteOperation(operation: string): boolean {
    const writePrefixes = ['remember', 'store', 'create', 'update', 'delete', 'forget', 'consolidate'];
    return writePrefixes.some(p => operation.toLowerCase().includes(p));
  }

  /**
   * Check if operation result should be cached
   */
  private isCacheable(operation: string): boolean {
    return !operation.includes('delete') && !operation.includes('forget');
  }

  /**
   * Get TTL for operation
   */
  private getTTL(operation: string): number {
    const ttls: Record<string, number> = {
      'episodic/recall': 5 * 60 * 1000,
      'semantic/search': 5 * 60 * 1000,
      'graph/searchEntities': 10 * 60 * 1000,
      'meta/memoryHealth': 30 * 1000,
      'meta/getExpertise': 2 * 60 * 1000,
      'meta/getCognitiveLoad': 60 * 1000
    };

    return ttls[operation] || 5 * 60 * 1000;  // Default 5 minutes
  }

  /**
   * Build cache key from operation and params
   */
  private buildCacheKey(operation: string, params: Record<string, unknown>): string {
    const relevant = this.filterParams(params);
    return `${operation}:${JSON.stringify(relevant)}`;
  }

  /**
   * Filter out non-cacheable parameters
   */
  private filterParams(params: Record<string, unknown>): Record<string, unknown> {
    const excluded = ['sessionId', 'userId', 'timestamp', 'createdAt', 'updatedAt'];
    const result: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(params)) {
      if (!excluded.includes(key)) {
        result[key] = value;
      }
    }

    return result;
  }

  /**
   * Extract tags for cache entry
   */
  private extractTags(operation: string, params: Record<string, unknown>): string[] {
    const tags = [operation.split('/')[0]];  // Layer name

    if (operation.includes('search') && params.query) {
      tags.push(`query:${params.query}`);
    }

    if (params.entityId) {
      tags.push(`entity:${params.entityId}`);
    }

    return tags;
  }
}

/**
 * Singleton cache instance
 */
let sharedCache: LocalCache | null = null;

/**
 * Get or create the shared cache instance
 */
export function getSharedCache(
  maxSize: number = 50000,
  ttlMs: number = 5 * 60 * 1000
): LocalCache {
  if (!sharedCache) {
    sharedCache = new LocalCache(maxSize, ttlMs);
  }
  return sharedCache;
}

/**
 * Create a cached version of a function
 *
 * @example
 *   const cachedRecall = createCachedFunction(
 *     recall,
 *     { ttl: 5 * 60 * 1000 }
 *   );
 *
 *   const results = await cachedRecall('query', 10);
 */
export function createCachedFunction<T extends (...args: any[]) => Promise<unknown>>(
  fn: T,
  options: {ttl?: number} = {}
): T {
  const cache = getSharedCache();
  const ttl = options.ttl || 5 * 60 * 1000;

  return (async (...args: any[]) => {
    const key = `fn:${fn.name}:${JSON.stringify(args)}`;
    let result = cache.get(key);

    if (result === null) {
      result = await fn(...args);
      cache.set(key, result, ttl);
    }

    return result;
  }) as T;
}
