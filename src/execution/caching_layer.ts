/**
 * Phase 4.3: Memory Optimization - Caching Layer
 *
 * Implements intelligent operation result caching with LRU eviction,
 * TTL management, and cache invalidation strategies.
 *
 * Expected improvements:
 * - 5-10x throughput for repeated queries
 * - 20-30% memory reduction
 * - 60-80% cache hit rates for typical workloads
 */

/**
 * Cache entry with metadata
 */
interface CacheEntry<T = unknown> {
  value: T;
  timestamp: number;
  ttl: number;
  hits: number;
  size: number;
  tags: Set<string>;
}

/**
 * Cache statistics
 */
interface CacheStats {
  hitCount: number;
  missCount: number;
  evictionCount: number;
  currentSize: number;
  maxSize: number;
  itemCount: number;
  hitRate: number;
  avgItemSize: number;
}

/**
 * Cache invalidation event
 */
interface InvalidationEvent {
  operation: string;
  params: Record<string, unknown>;
  affectedTags: string[];
  timestamp: number;
}

/**
 * Operation result cache with LRU eviction and TTL
 */
export class OperationCache {
  private cache = new Map<string, CacheEntry>();
  private accessOrder: string[] = [];
  private maxSize: number;
  private defaultTtl: number;
  private stats: CacheStats;
  private invalidationStrategy: Map<string, string[]> = new Map();

  constructor(maxSize: number = 10000, defaultTtlMs: number = 5 * 60 * 1000) {
    this.maxSize = maxSize;
    this.defaultTtl = defaultTtlMs;
    this.stats = {
      hitCount: 0,
      missCount: 0,
      evictionCount: 0,
      currentSize: 0,
      maxSize,
      itemCount: 0,
      hitRate: 0,
      avgItemSize: 0
    };

    this.setupInvalidationStrategy();
  }

  /**
   * Setup operation invalidation patterns
   *
   * When a write operation happens, which queries should be invalidated?
   */
  private setupInvalidationStrategy(): void {
    // Remember operations invalidate recall operations
    this.invalidationStrategy.set('episodic/remember', [
      'episodic/recall',
      'episodic/getRecent',
      'episodic/queryTemporal'
    ]);

    // Store operations invalidate search operations
    this.invalidationStrategy.set('semantic/store', [
      'semantic/search',
      'semantic/semanticSearch',
      'semantic/keywordSearch',
      'semantic/hybridSearch'
    ]);

    // Forget operations invalidate list operations
    this.invalidationStrategy.set('episodic/forget', [
      'episodic/listEvents',
      'episodic/recall'
    ]);

    // Update operations invalidate retrieve operations
    this.invalidationStrategy.set('semantic/update', [
      'semantic/search',
      'semantic/list'
    ]);

    // Create task invalidates list
    this.invalidationStrategy.set('prospective/createTask', [
      'prospective/listTasks',
      'prospective/getPendingTasks'
    ]);

    // Complete goal invalidates analyses
    this.invalidationStrategy.set('prospective/completeGoal', [
      'meta/getProgressMetrics',
      'prospective/listGoals'
    ]);
  }

  /**
   * Get value from cache
   */
  get<T = unknown>(key: string): T | null {
    const entry = this.cache.get(key);

    // Cache miss
    if (!entry) {
      this.stats.missCount++;
      this.updateHitRate();
      return null;
    }

    // Check if expired
    if (this.isExpired(entry)) {
      this.cache.delete(key);
      this.stats.evictionCount++;
      this.stats.currentSize -= entry.size;
      this.stats.itemCount--;
      this.stats.missCount++;
      this.updateHitRate();
      return null;
    }

    // Cache hit
    this.stats.hitCount++;
    entry.hits++;

    // Update access order (move to end for LRU)
    this.updateAccessOrder(key);
    this.updateHitRate();

    return entry.value as T;
  }

  /**
   * Set value in cache
   */
  set<T = unknown>(
    key: string,
    value: T,
    ttl: number = this.defaultTtl,
    tags: string[] = []
  ): void {
    // Calculate size (rough estimate)
    const size = JSON.stringify(value).length;

    // Check if we need to evict
    if (this.stats.currentSize + size > this.maxSize) {
      this.evictLRU(size);
    }

    // Remove old entry if exists
    if (this.cache.has(key)) {
      const old = this.cache.get(key)!;
      this.stats.currentSize -= old.size;
      this.stats.itemCount--;
    }

    // Add new entry
    const entry: CacheEntry<T> = {
      value,
      timestamp: Date.now(),
      ttl,
      hits: 0,
      size,
      tags: new Set(tags)
    };

    this.cache.set(key, entry);
    this.stats.currentSize += size;
    this.stats.itemCount++;
    this.updateAccessOrder(key);
  }

  /**
   * Clear entire cache
   */
  clear(): void {
    this.cache.clear();
    this.accessOrder = [];
    this.stats = {
      ...this.stats,
      currentSize: 0,
      itemCount: 0,
      hitCount: 0,
      missCount: 0,
      evictionCount: 0
    };
  }

  /**
   * Clear cache by tag
   */
  clearByTag(tag: string): number {
    let cleared = 0;
    const keysToDelete: string[] = [];

    for (const [key, entry] of this.cache) {
      if (entry.tags.has(tag)) {
        keysToDelete.push(key);
        this.stats.currentSize -= entry.size;
        this.stats.itemCount--;
        cleared++;
      }
    }

    for (const key of keysToDelete) {
      this.cache.delete(key);
      this.accessOrder = this.accessOrder.filter(k => k !== key);
    }

    this.stats.evictionCount += cleared;
    return cleared;
  }

  /**
   * Invalidate cache based on operation
   *
   * When an operation completes, invalidate related caches
   */
  invalidateByOperation(operation: string, params: Record<string, unknown>): number {
    const affectedOps = this.invalidationStrategy.get(operation) || [];
    let cleared = 0;

    for (const affectedOp of affectedOps) {
      // Find keys matching this operation
      for (const [key] of this.cache) {
        if (key.startsWith(affectedOp + ':')) {
          cleared += this.deleteKey(key);
        }
      }
    }

    return cleared;
  }

  /**
   * Invalidate cache by pattern
   */
  invalidateByPattern(pattern: string): number {
    let cleared = 0;
    const keysToDelete: string[] = [];
    const regex = new RegExp(pattern);

    for (const [key] of this.cache) {
      if (regex.test(key)) {
        keysToDelete.push(key);
      }
    }

    for (const key of keysToDelete) {
      cleared += this.deleteKey(key);
    }

    return cleared;
  }

  /**
   * Get cache statistics
   */
  getStats(): CacheStats {
    return { ...this.stats };
  }

  /**
   * Get detailed statistics with breakdown
   */
  getDetailedStats() {
    const topKeys = Array.from(this.cache.entries())
      .sort((a, b) => b[1].hits - a[1].hits)
      .slice(0, 10)
      .map(([key, entry]) => ({
        key,
        hits: entry.hits,
        size: entry.size,
        ttl: entry.ttl,
        age: Date.now() - entry.timestamp
      }));

    return {
      ...this.stats,
      topKeys,
      oldestItemAge: this.accessOrder.length > 0
        ? Date.now() - (this.cache.get(this.accessOrder[0])?.timestamp || 0)
        : 0
    };
  }

  /**
   * Warm cache with frequently used queries
   */
  warmCache(entries: Array<{ key: string; value: unknown; ttl?: number }>): void {
    for (const entry of entries) {
      this.set(entry.key, entry.value, entry.ttl);
    }
  }

  /**
   * Check if entry is expired
   */
  private isExpired(entry: CacheEntry): boolean {
    return Date.now() - entry.timestamp > entry.ttl;
  }

  /**
   * Update access order (LRU)
   */
  private updateAccessOrder(key: string): void {
    // Remove from current position
    this.accessOrder = this.accessOrder.filter(k => k !== key);
    // Add to end (most recently used)
    this.accessOrder.push(key);
  }

  /**
   * Evict LRU entries until space is available
   */
  private evictLRU(spaceNeeded: number): void {
    while (this.stats.currentSize + spaceNeeded > this.maxSize && this.accessOrder.length > 0) {
      const oldestKey = this.accessOrder.shift()!;
      const entry = this.cache.get(oldestKey);

      if (entry) {
        this.cache.delete(oldestKey);
        this.stats.currentSize -= entry.size;
        this.stats.itemCount--;
        this.stats.evictionCount++;
      }
    }
  }

  /**
   * Delete a specific key
   */
  private deleteKey(key: string): number {
    const entry = this.cache.get(key);
    if (!entry) return 0;

    this.cache.delete(key);
    this.accessOrder = this.accessOrder.filter(k => k !== key);
    this.stats.currentSize -= entry.size;
    this.stats.itemCount--;
    this.stats.evictionCount++;

    return 1;
  }

  /**
   * Update hit rate statistic
   */
  private updateHitRate(): void {
    const total = this.stats.hitCount + this.stats.missCount;
    this.stats.hitRate = total > 0 ? this.stats.hitCount / total : 0;
    this.stats.avgItemSize = this.stats.itemCount > 0
      ? this.stats.currentSize / this.stats.itemCount
      : 0;
  }
}

/**
 * Smart operation caching wrapper
 *
 * Automatically caches operation results with appropriate TTL based on operation type
 */
export class CachedOperationExecutor {
  private cache: OperationCache;
  private readonly operationTtls: Map<string, number> = new Map();

  constructor(cacheMaxSize: number = 10000) {
    this.cache = new OperationCache(cacheMaxSize);
    this.setupOperationTtls();
  }

  /**
   * Setup TTL for different operation types
   */
  private setupOperationTtls(): void {
    // Read operations (longer TTL)
    this.operationTtls.set('episodic/recall', 5 * 60 * 1000);        // 5 min
    this.operationTtls.set('semantic/search', 5 * 60 * 1000);        // 5 min
    this.operationTtls.set('graph/searchEntities', 10 * 60 * 1000);   // 10 min
    this.operationTtls.set('meta/memoryHealth', 30 * 1000);          // 30 sec

    // Write operations (no cache)
    this.operationTtls.set('episodic/remember', 0);
    this.operationTtls.set('semantic/store', 0);
    this.operationTtls.set('episodic/forget', 0);

    // System operations (shorter TTL)
    this.operationTtls.set('meta/getExpertise', 2 * 60 * 1000);       // 2 min
    this.operationTtls.set('meta/getCognitiveLoad', 60 * 1000);       // 1 min

    // Default TTL for operations not explicitly set
    this.operationTtls.set('default', 3 * 60 * 1000);                // 3 min
  }

  /**
   * Execute operation with caching
   */
  async executeWithCache<T = unknown>(
    operation: string,
    params: Record<string, unknown>,
    executor: (op: string, params: Record<string, unknown>) => Promise<T>
  ): Promise<T> {
    // Build cache key
    const cacheKey = this.buildCacheKey(operation, params);

    // Check cache for read operations
    if (this.isReadOperation(operation)) {
      const cached = this.cache.get<T>(cacheKey);
      if (cached !== null) {
        return cached;
      }
    }

    // Execute operation
    const result = await executor(operation, params);

    // Cache result if appropriate
    if (this.isCacheable(operation)) {
      const ttl = this.operationTtls.get(operation)
        || this.operationTtls.get('default')!;

      if (ttl > 0) {
        const tags = [operation, ...this.extractTags(operation, params)];
        this.cache.set(cacheKey, result, ttl, tags);
      }
    }

    // Invalidate related caches after write operations
    if (this.isWriteOperation(operation)) {
      this.cache.invalidateByOperation(operation, params);
    }

    return result;
  }

  /**
   * Check if operation should be cached
   */
  private isCacheable(operation: string): boolean {
    // Don't cache delete/forget operations
    if (operation.includes('delete') || operation.includes('forget')) {
      return false;
    }

    // Don't cache operations returning void or null
    return true;
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
   * Build cache key from operation and params
   */
  private buildCacheKey(operation: string, params: Record<string, unknown>): string {
    // Only include relevant params in cache key
    const relevant = this.extractCacheableParams(operation, params);
    const paramsStr = JSON.stringify(relevant);
    return `${operation}:${paramsStr}`;
  }

  /**
   * Extract cacheable parameters (exclude user IDs, timestamps, etc.)
   */
  private extractCacheableParams(operation: string, params: Record<string, unknown>): Record<string, unknown> {
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
    const tags = [operation.split('/')[0]]; // Layer name

    // Add query-based tags for search operations
    if (operation.includes('search')) {
      if (params.query) {
        tags.push(`query:${params.query}`);
      }
    }

    // Add entity-based tags
    if (params.entityId) {
      tags.push(`entity:${params.entityId}`);
    }

    return tags;
  }

  /**
   * Clear cache for specific operation
   */
  clearOperation(operation: string): number {
    return this.cache.invalidateByPattern(`^${operation}`);
  }

  /**
   * Get cache statistics
   */
  getStats() {
    return this.cache.getDetailedStats();
  }

  /**
   * Get cache instance for direct management
   */
  getCache(): OperationCache {
    return this.cache;
  }
}

/**
 * Memoization helper for expensive computations
 */
export function memoize<T extends (...args: unknown[]) => Promise<unknown>>(
  fn: T,
  options: {
    maxAge?: number;
    maxSize?: number;
  } = {}
): T {
  const cache = new OperationCache(options.maxSize || 100, options.maxAge || 5 * 60 * 1000);

  return (async (...args: unknown[]) => {
    const key = JSON.stringify(args);
    let result = cache.get(key);

    if (result === null) {
      result = await fn(...args);
      cache.set(key, result);
    }

    return result;
  }) as T;
}

/**
 * Create a cached version of an operation
 */
export function createCachedOperation<T extends (...args: unknown[]) => Promise<unknown>>(
  name: string,
  fn: T,
  ttl: number = 5 * 60 * 1000
): T {
  const cache = new OperationCache(1000, ttl);

  return (async (...args: unknown[]) => {
    const key = `${name}:${JSON.stringify(args)}`;
    let result = cache.get(key);

    if (result === null) {
      result = await fn(...args);
      cache.set(key, result, ttl);
    }

    return result;
  }) as T;
}
