/**
 * Phase 4.3: Connection Pooling Layer
 *
 * Manages reusable connections to databases and external services.
 * Implements connection pooling with health checks, eviction, and metrics.
 */

/**
 * Connection interface
 */
interface Connection {
  id: string;
  state: 'idle' | 'active' | 'closed';
  createdAt: number;
  lastUsedAt: number;
  usageCount: number;
  healthCheck(): Promise<boolean>;
  close(): Promise<void>;
}

/**
 * Pool statistics
 */
interface PoolStats {
  totalConnections: number;
  activeConnections: number;
  idleConnections: number;
  closedConnections: number;
  createdCount: number;
  evictedCount: number;
  utilization: number;
  avgConnectionAge: number;
  totalRequests: number;
  avgWaitTimeMs: number;
}

/**
 * Pool configuration
 */
interface PoolConfig {
  maxConnections?: number;
  minConnections?: number;
  idleTimeout?: number;              // ms
  connectionTimeout?: number;         // ms
  validationInterval?: number;        // ms
  validator?: (conn: Connection) => Promise<boolean>;
}

/**
 * Connection Pool
 *
 * Manages a pool of reusable connections
 */
export class ConnectionPool {
  private available: Connection[] = [];
  private active: Map<string, Connection> = new Map();
  private closed: Set<string> = new Set();

  private maxConnections: number;
  private minConnections: number;
  private idleTimeout: number;
  private connectionTimeout: number;
  private validationInterval: number;
  private validator: (conn: Connection) => Promise<boolean>;

  private stats: PoolStats;
  private waitQueue: Array<{resolve: (conn: Connection) => void; reject: (err: Error) => void}> = [];
  private validationTimer?: NodeJS.Timer;
  private idleCheckTimer?: NodeJS.Timer;

  constructor(config: PoolConfig = {}) {
    this.maxConnections = config.maxConnections || 50;
    this.minConnections = config.minConnections || 5;
    this.idleTimeout = config.idleTimeout || 30 * 1000;
    this.connectionTimeout = config.connectionTimeout || 10 * 1000;
    this.validationInterval = config.validationInterval || 10 * 1000;
    this.validator = config.validator || this.defaultValidator;

    this.stats = {
      totalConnections: 0,
      activeConnections: 0,
      idleConnections: 0,
      closedConnections: 0,
      createdCount: 0,
      evictedCount: 0,
      utilization: 0,
      avgConnectionAge: 0,
      totalRequests: 0,
      avgWaitTimeMs: 0
    };

    // Start health checks
    this.startHealthChecks();
    this.startIdleChecks();
  }

  /**
   * Acquire a connection from the pool
   */
  async acquire(): Promise<Connection> {
    const startTime = Date.now();

    // Try to get available connection
    while (this.available.length > 0) {
      const conn = this.available.pop()!;

      // Check if connection is still valid
      if (await this.isValid(conn)) {
        conn.state = 'active';
        conn.lastUsedAt = Date.now();
        conn.usageCount++;
        this.active.set(conn.id, conn);
        this.updateStats();
        return conn;
      } else {
        // Connection is invalid, close it
        await conn.close();
        this.closed.add(conn.id);
        this.stats.closedConnections++;
      }
    }

    // Create new connection if under limit
    if (this.stats.totalConnections < this.maxConnections) {
      const conn = await this.createConnection();
      conn.state = 'active';
      this.active.set(conn.id, conn);
      this.updateStats();
      return conn;
    }

    // Wait for available connection
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.waitQueue = this.waitQueue.filter(item => item.resolve !== resolve);
        reject(new Error(`Connection timeout after ${this.connectionTimeout}ms`));
      }, this.connectionTimeout);

      this.waitQueue.push({
        resolve: (conn) => {
          clearTimeout(timeout);
          resolve(conn);
        },
        reject: (err) => {
          clearTimeout(timeout);
          reject(err);
        }
      });
    });
  }

  /**
   * Release a connection back to the pool
   */
  release(conn: Connection): void {
    if (this.active.has(conn.id)) {
      this.active.delete(conn.id);
      conn.state = 'idle';
      this.available.push(conn);

      // Check if someone is waiting
      if (this.waitQueue.length > 0) {
        const waiter = this.waitQueue.shift()!;
        const nextConn = this.available.pop()!;
        nextConn.state = 'active';
        this.active.set(nextConn.id, nextConn);
        waiter.resolve(nextConn);
      }

      this.updateStats();
    }
  }

  /**
   * Close a specific connection
   */
  async close(conn: Connection): Promise<void> {
    if (this.active.has(conn.id)) {
      this.active.delete(conn.id);
    }

    const index = this.available.indexOf(conn);
    if (index !== -1) {
      this.available.splice(index, 1);
    }

    await conn.close();
    this.closed.add(conn.id);
    this.stats.closedConnections++;
    this.updateStats();
  }

  /**
   * Close all connections and shut down pool
   */
  async drain(): Promise<void> {
    // Close active connections
    for (const conn of this.active.values()) {
      await conn.close();
      this.closed.add(conn.id);
    }
    this.active.clear();

    // Close available connections
    for (const conn of this.available) {
      await conn.close();
      this.closed.add(conn.id);
    }
    this.available = [];

    // Stop timers
    if (this.validationTimer) {
      clearInterval(this.validationTimer);
    }
    if (this.idleCheckTimer) {
      clearInterval(this.idleCheckTimer);
    }

    this.updateStats();
  }

  /**
   * Get pool statistics
   */
  getStats(): PoolStats {
    return { ...this.stats };
  }

  /**
   * Get detailed pool information
   */
  getInfo() {
    return {
      stats: this.stats,
      connections: {
        available: this.available.map(c => ({
          id: c.id,
          state: c.state,
          age: Date.now() - c.createdAt,
          usageCount: c.usageCount
        })),
        active: Array.from(this.active.values()).map(c => ({
          id: c.id,
          state: c.state,
          age: Date.now() - c.createdAt,
          usageCount: c.usageCount
        }))
      },
      waiting: this.waitQueue.length
    };
  }

  /**
   * Create a new connection
   */
  private async createConnection(): Promise<Connection> {
    const id = `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    const conn: Connection = {
      id,
      state: 'idle',
      createdAt: Date.now(),
      lastUsedAt: Date.now(),
      usageCount: 0,
      healthCheck: async () => this.validator(conn as Connection),
      close: async () => {
        // Mock close
      }
    };

    this.stats.totalConnections++;
    this.stats.createdCount++;

    return conn;
  }

  /**
   * Check if connection is valid
   */
  private async isValid(conn: Connection): Promise<boolean> {
    try {
      return await conn.healthCheck();
    } catch (error) {
      return false;
    }
  }

  /**
   * Default health check validator
   */
  private async defaultValidator(conn: Connection): Promise<boolean> {
    // Check if connection is too old
    const age = Date.now() - conn.createdAt;
    if (age > 60 * 60 * 1000) {  // 1 hour
      return false;
    }

    // Check if idle too long
    const idleTime = Date.now() - conn.lastUsedAt;
    if (idleTime > this.idleTimeout) {
      return false;
    }

    return true;
  }

  /**
   * Start periodic health checks
   */
  private startHealthChecks(): void {
    this.validationTimer = setInterval(async () => {
      const toRemove: Connection[] = [];

      // Validate all available connections
      for (const conn of this.available) {
        if (!(await this.isValid(conn))) {
          toRemove.push(conn);
        }
      }

      // Remove invalid connections
      for (const conn of toRemove) {
        await this.close(conn);
        this.stats.evictedCount++;
      }

      // Ensure minimum connections
      while (this.stats.totalConnections < this.minConnections) {
        const conn = await this.createConnection();
        this.available.push(conn);
      }

      this.updateStats();
    }, this.validationInterval);
  }

  /**
   * Start idle connection checks
   */
  private startIdleChecks(): void {
    this.idleCheckTimer = setInterval(async () => {
      const now = Date.now();
      const toClose: Connection[] = [];

      // Check for idle connections
      for (const conn of this.available) {
        const idleTime = now - conn.lastUsedAt;
        if (idleTime > this.idleTimeout) {
          toClose.push(conn);
        }
      }

      // Close idle connections
      for (const conn of toClose) {
        if (this.stats.totalConnections > this.minConnections) {
          await this.close(conn);
        }
      }

      this.updateStats();
    }, this.idleTimeout);
  }

  /**
   * Update pool statistics
   */
  private updateStats(): void {
    this.stats.totalConnections = this.stats.createdCount - this.stats.closedConnections;
    this.stats.activeConnections = this.active.size;
    this.stats.idleConnections = this.available.length;
    this.stats.utilization = this.stats.totalConnections > 0
      ? this.stats.activeConnections / this.stats.totalConnections
      : 0;

    if (this.available.length > 0) {
      const totalAge = this.available.reduce((sum, conn) => sum + (Date.now() - conn.createdAt), 0);
      this.stats.avgConnectionAge = totalAge / this.available.length;
    }

    this.stats.totalRequests = Array.from(this.active.values()).reduce((sum, conn) => sum + conn.usageCount, 0) +
                                this.available.reduce((sum, conn) => sum + conn.usageCount, 0);
  }
}

/**
 * Connection pool factory with pre-configured pools
 */
export class ConnectionPoolManager {
  private pools: Map<string, ConnectionPool> = new Map();

  /**
   * Create or get a connection pool
   */
  getPool(name: string, config?: PoolConfig): ConnectionPool {
    if (!this.pools.has(name)) {
      this.pools.set(name, new ConnectionPool(config));
    }
    return this.pools.get(name)!;
  }

  /**
   * Get database connection pool
   */
  getDatabasePool(): ConnectionPool {
    return this.getPool('database', {
      maxConnections: 50,
      minConnections: 5,
      idleTimeout: 30 * 1000,
      validationInterval: 10 * 1000
    });
  }

  /**
   * Get MCP tool connection pool
   */
  getMCPPool(): ConnectionPool {
    return this.getPool('mcp-tools', {
      maxConnections: 20,
      minConnections: 2,
      idleTimeout: 60 * 1000,
      validationInterval: 15 * 1000
    });
  }

  /**
   * Get HTTP client pool
   */
  getHTTPPool(): ConnectionPool {
    return this.getPool('http-client', {
      maxConnections: 100,
      minConnections: 10,
      idleTimeout: 60 * 1000,
      validationInterval: 20 * 1000
    });
  }

  /**
   * Drain all pools
   */
  async drainAll(): Promise<void> {
    for (const pool of this.pools.values()) {
      await pool.drain();
    }
  }

  /**
   * Get statistics for all pools
   */
  getAllStats() {
    const stats: Record<string, PoolStats> = {};
    for (const [name, pool] of this.pools) {
      stats[name] = pool.getStats();
    }
    return stats;
  }
}

/**
 * Singleton pool manager instance
 */
export const poolManager = new ConnectionPoolManager();

/**
 * Helper function to execute with pooled connection
 */
export async function withPooledConnection<T>(
  poolName: string,
  fn: (conn: Connection) => Promise<T>,
  config?: PoolConfig
): Promise<T> {
  const pool = poolManager.getPool(poolName, config);
  const conn = await pool.acquire();

  try {
    return await fn(conn);
  } finally {
    pool.release(conn);
  }
}
