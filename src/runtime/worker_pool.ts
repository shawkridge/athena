/**
 * Worker Pool
 *
 * Manages a pool of pre-warmed Deno workers for parallel code execution.
 * Implements lifecycle management, health checks, and graceful cleanup.
 *
 * @see docs/MCP_CODE_EXECUTION_ARCHITECTURE.md for design
 * @see src/runtime/deno_executor.ts for usage
 */

/**
 * Worker State
 */
export interface WorkerState {
  /** Unique worker ID */
  id: string;

  /** Worker process (Deno process) */
  process?: any; // Would be Deno.Process in real implementation

  /** Is worker available for assignment */
  available: boolean;

  /** Last time worker was used */
  lastUsed: number;

  /** Number of executions completed */
  executionCount: number;

  /** Current execution ID (if busy) */
  currentExecutionId?: string;

  /** Memory usage in MB */
  memoryUsageMb: number;

  /** Worker health status */
  health: "healthy" | "degraded" | "failed";

  /** Error count */
  errorCount: number;

  /** Created at timestamp */
  createdAt: number;
}

/**
 * Worker Pool Configuration
 */
export interface WorkerPoolConfig {
  /** Total number of workers */
  size: number;

  /** Worker startup timeout (ms) */
  timeout: number;

  /** Recycle worker after N executions */
  maxAge: number;

  /** Kill worker if idle > N ms */
  idleTimeout: number;
}

/**
 * Pool Status
 */
export interface PoolStatus {
  /** Total workers in pool */
  total: number;

  /** Available workers */
  available: number;

  /** Busy workers */
  busy: number;

  /** Average worker age in executions */
  averageAge: number;

  /** Total memory used by all workers (MB) */
  memoryUsageMb: number;

  /** Worker health distribution */
  health: {
    healthy: number;
    degraded: number;
    failed: number;
  };

  /** Average error rate across workers */
  avgErrorRate: number;
}

/**
 * Worker Pool
 *
 * Manages lifecycle of pre-warmed Deno workers.
 */
export class WorkerPool {
  private workers: WorkerState[] = [];
  private available: Set<string> = new Set();
  private waitingList: Array<{
    resolve: (worker: WorkerState) => void;
    reject: (error: Error) => void;
  }> = [];
  private config: WorkerPoolConfig;
  private nextWorkerId = 0;
  private healthCheckInterval?: number;
  private recycleInterval?: number;

  constructor(config: WorkerPoolConfig) {
    this.config = config;
  }

  /**
   * Initialize and warm up worker pool
   */
  async warmup(): Promise<void> {
    console.log(
      `[WorkerPool] Warming up ${this.config.size} workers...`
    );

    const startTime = Date.now();
    const workers: Promise<WorkerState>[] = [];

    // Start all workers in parallel
    for (let i = 0; i < this.config.size; i++) {
      workers.push(this.createWorker());
    }

    // Wait for all workers to start
    const results = await Promise.allSettled(workers);

    let successCount = 0;
    let failureCount = 0;

    for (const result of results) {
      if (result.status === "fulfilled") {
        this.workers.push(result.value);
        this.available.add(result.value.id);
        successCount++;
      } else {
        failureCount++;
        console.error(
          `[WorkerPool] Failed to start worker: ${result.reason}`
        );
      }
    }

    const warmupTime = Date.now() - startTime;

    if (failureCount > 0) {
      throw new Error(
        `Failed to start all workers: ${failureCount}/${this.config.size} failed`
      );
    }

    console.log(
      `[WorkerPool] All ${successCount} workers warmed up in ${warmupTime}ms`
    );

    // Start background health checks
    this.startHealthChecks();
  }

  /**
   * Create a new worker
   */
  private async createWorker(): Promise<WorkerState> {
    const workerId = `worker-${this.nextWorkerId++}`;

    return new Promise((resolve, reject) => {
      // Set timeout for worker startup
      const timeoutId = setTimeout(() => {
        reject(new Error(`Worker startup timeout: ${workerId}`));
      }, this.config.timeout);

      try {
        // Simulate worker startup
        // Real implementation would:
        // 1. Start Deno process with security permissions
        // 2. Load code execution runtime
        // 3. Wait for "ready" message

        const worker: WorkerState = {
          id: workerId,
          available: true,
          lastUsed: Date.now(),
          executionCount: 0,
          memoryUsageMb: 20, // Initial memory
          health: "healthy",
          errorCount: 0,
          createdAt: Date.now(),
        };

        clearTimeout(timeoutId);
        resolve(worker);
      } catch (error) {
        clearTimeout(timeoutId);
        reject(error);
      }
    });
  }

  /**
   * Acquire a worker from the pool
   *
   * Blocks until a worker is available or timeout expires.
   */
  async acquire(timeoutMs: number): Promise<WorkerState | null> {
    // Check if worker available immediately
    if (this.available.size > 0) {
      const workerId = this.available.values().next().value as string;
      const worker = this.workers.find((w) => w.id === workerId);

      if (worker && worker.health === "healthy") {
        this.available.delete(workerId);
        worker.available = false;
        return worker;
      }
    }

    // Wait for worker with timeout
    return new Promise((resolve) => {
      const timeoutId = setTimeout(() => {
        // Remove from waiting list
        const index = this.waitingList.findIndex(
          (item) => item.resolve === resolve
        );
        if (index >= 0) {
          this.waitingList.splice(index, 1);
        }
        resolve(null);
      }, timeoutMs);

      this.waitingList.push({
        resolve: (worker) => {
          clearTimeout(timeoutId);
          resolve(worker);
        },
        reject: (error) => {
          clearTimeout(timeoutId);
          resolve(null);
        },
      });
    });
  }

  /**
   * Release a worker back to the pool
   */
  release(worker: WorkerState): void {
    if (!worker) {
      return;
    }

    worker.available = true;
    worker.lastUsed = Date.now();
    worker.executionCount++;

    // Check if worker should be recycled
    if (worker.executionCount >= this.config.maxAge) {
      console.log(`[WorkerPool] Recycling worker ${worker.id} (reached max age)`);
      this.recycleWorker(worker);
      return;
    }

    // Check if next worker in waiting list can use this
    if (this.waitingList.length > 0) {
      const waiter = this.waitingList.shift();
      if (waiter) {
        worker.available = false;
        waiter.resolve(worker);
        return;
      }
    }

    // Add back to available pool
    this.available.add(worker.id);
  }

  /**
   * Recycle a worker (shut down and restart)
   */
  private async recycleWorker(worker: WorkerState): Promise<void> {
    // Remove from available pool
    this.available.delete(worker.id);

    // Remove from workers list
    const index = this.workers.findIndex((w) => w.id === worker.id);
    if (index >= 0) {
      this.workers.splice(index, 1);
    }

    try {
      // In real implementation, would shut down the Deno process
      // await worker.process?.close();
    } catch (error) {
      console.error(
        `[WorkerPool] Error shutting down worker ${worker.id}: ${error}`
      );
    }

    // Create replacement worker
    try {
      const newWorker = await this.createWorker();
      this.workers.push(newWorker);
      this.available.add(newWorker.id);
    } catch (error) {
      console.error(
        `[WorkerPool] Error creating replacement worker: ${error}`
      );
    }
  }

  /**
   * Get pool status
   */
  getStatus(): PoolStatus {
    const busy = this.config.size - this.available.size;
    const totalExecutions = this.workers.reduce(
      (sum, w) => sum + w.executionCount,
      0
    );
    const totalMemory = this.workers.reduce(
      (sum, w) => sum + w.memoryUsageMb,
      0
    );
    const totalErrors = this.workers.reduce((sum, w) => sum + w.errorCount, 0);

    const health = {
      healthy: this.workers.filter((w) => w.health === "healthy").length,
      degraded: this.workers.filter((w) => w.health === "degraded").length,
      failed: this.workers.filter((w) => w.health === "failed").length,
    };

    return {
      total: this.workers.length,
      available: this.available.size,
      busy,
      averageAge:
        this.workers.length > 0
          ? Math.round(totalExecutions / this.workers.length)
          : 0,
      memoryUsageMb: totalMemory,
      health,
      avgErrorRate:
        this.workers.length > 0 ? totalErrors / this.workers.length : 0,
    };
  }

  /**
   * Start background health checks
   */
  private startHealthChecks(): void {
    this.healthCheckInterval = setInterval(() => {
      for (const worker of this.workers) {
        // Simple health check: check if worker is still responsive
        // Real implementation would send ping/pong messages

        // If worker has high error count, mark as degraded
        if (worker.errorCount > 10) {
          worker.health = "degraded";
        }

        // If idle for too long, consider recycling
        if (
          Date.now() - worker.lastUsed > this.config.idleTimeout &&
          worker.available
        ) {
          console.log(
            `[WorkerPool] Recycling idle worker ${worker.id}`
          );
          this.recycleWorker(worker);
        }
      }
    }, 30000) as any;
  }

  /**
   * Shutdown all workers gracefully
   */
  async shutdown(): Promise<void> {
    console.log("[WorkerPool] Shutting down worker pool...");

    // Clear intervals
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
    if (this.recycleInterval) {
      clearInterval(this.recycleInterval);
    }

    // Reject all waiting requests
    for (const waiter of this.waitingList) {
      waiter.reject(new Error("Worker pool shutting down"));
    }
    this.waitingList = [];

    // Shutdown all workers
    const shutdownPromises = this.workers.map(async (worker) => {
      try {
        // Real implementation would: await worker.process?.close();
      } catch (error) {
        console.error(
          `[WorkerPool] Error shutting down worker ${worker.id}: ${error}`
        );
      }
    });

    await Promise.all(shutdownPromises);

    this.workers = [];
    this.available.clear();

    console.log("[WorkerPool] All workers shut down");
  }

  /**
   * Get worker by ID (for debugging)
   */
  getWorker(workerId: string): WorkerState | undefined {
    return this.workers.find((w) => w.id === workerId);
  }

  /**
   * Get all workers (for debugging)
   */
  getAllWorkers(): WorkerState[] {
    return [...this.workers];
  }
}

export default WorkerPool;
