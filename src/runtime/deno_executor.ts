/**
 * Deno Executor
 *
 * Main orchestrator for code execution in isolated Deno workers.
 * Manages worker pool, request queuing, resource monitoring, and cleanup.
 *
 * @see docs/MCP_CODE_EXECUTION_ARCHITECTURE.md for design
 * @see src/runtime/worker_pool.ts for worker lifecycle
 * @see src/runtime/resource_monitor.ts for resource enforcement
 */

import { WorkerPool, WorkerState, PoolStatus } from "./worker_pool.ts";
import { ResourceMonitor, ResourceUsage, ResourceViolation } from "./resource_monitor.ts";
import type { ToolContext, ExecutionError, ExecutionMetrics } from "../interfaces/execution.ts";

/**
 * Deno Executor Configuration
 */
export interface DenoExecutorConfig {
  /** Number of pre-warmed workers (default: 10) */
  workerCount: number;

  /** Worker startup timeout in milliseconds (default: 5000) */
  workerTimeout: number;

  /** Maximum concurrent executions (default: 50) */
  maxConcurrent: number;

  /** Log level for debugging */
  logLevel: "debug" | "info" | "warn" | "error";

  /** Enable performance metrics collection */
  enableMetrics: boolean;

  /** Working directory for Deno processes */
  workDir: string;

  /** Optional: Custom Deno command (default: "deno") */
  denoCommand?: string;
}

/**
 * Code Execution Context
 */
export interface ExecutionContext {
  /** Unique execution ID */
  id: string;

  /** Session ID for context */
  sessionId: string;

  /** TypeScript/JavaScript code to execute */
  code: string;

  /** Execution timeout in milliseconds */
  timeout: number;

  /** Memory limit in MB */
  memoryLimit: number;

  /** Maximum result size in bytes */
  maxResultSize: number;

  /** Available tools and state */
  toolContext: ToolContext;

  /** Optional: Custom environment variables */
  env?: Record<string, string>;
}

/**
 * Execution Result from Worker
 */
export interface ExecutionResult {
  /** Whether execution succeeded */
  success: boolean;

  /** Execution output/result */
  output?: unknown;

  /** Execution error (if any) */
  error?: ExecutionError;

  /** Console logs from execution */
  logs: LogEntry[];

  /** Execution metrics (timing, memory, etc.) */
  metrics: ExecutionMetrics;

  /** Resource usage tracking */
  resourceUsage: ResourceUsage;
}

/**
 * Log Entry from Code Execution
 */
export interface LogEntry {
  /** Log level */
  level: "debug" | "info" | "warn" | "error";

  /** Log message */
  message: string;

  /** Timestamp */
  timestamp: number;

  /** Optional: Stack trace for errors */
  stack?: string;
}

/**
 * Execution Request (Internal Queue)
 */
interface ExecutionRequest {
  /** Execution context */
  context: ExecutionContext;

  /** Promise resolver */
  resolve: (result: ExecutionResult) => void;

  /** Promise rejecter */
  reject: (error: Error) => void;

  /** Request timestamp */
  requestedAt: number;

  /** Timeout ID */
  timeoutId?: number;
}

/**
 * Execution State (Internal Tracking)
 */
interface ExecutionState {
  /** Execution ID */
  id: string;

  /** Current state */
  state: "queued" | "assigned" | "executing" | "done" | "error";

  /** Assigned worker (if any) */
  worker?: WorkerState;

  /** Start time */
  startTime?: number;

  /** End time */
  endTime?: number;

  /** Result (when done) */
  result?: ExecutionResult;

  /** Error (if failed) */
  error?: Error;
}

/**
 * Executor Metrics
 */
export interface ExecutorMetrics {
  /** Number of active workers */
  activeWorkers: number;

  /** Number of queued executions */
  queuedExecutions: number;

  /** Total executions completed */
  totalExecutions: number;

  /** Average execution latency (ms) */
  averageLatencyMs: number;

  /** Worker utilization percentage (0-100) */
  workerUtilization: number;

  /** Total memory usage (MB) */
  memoryUsageMb: number;

  /** Total errors */
  totalErrors: number;

  /** Resource violations */
  resourceViolations: Record<string, number>;

  /** Uptime (ms) */
  uptimeMs: number;
}

/**
 * Deno Executor
 *
 * Main orchestrator for code execution in isolated Deno workers.
 */
export class DenoExecutor {
  private config: DenoExecutorConfig;
  private workerPool: WorkerPool;
  private resourceMonitor: ResourceMonitor;
  private executionQueue: ExecutionRequest[] = [];
  private executionStates: Map<string, ExecutionState> = new Map();
  private metrics: ExecutorMetrics;
  private startTime: number = 0;
  private logger: Logger;
  private initialized: boolean = false;
  private shutdownStarted: boolean = false;

  constructor(config: DenoExecutorConfig) {
    this.config = {
      workerCount: 10,
      workerTimeout: 5000,
      maxConcurrent: 50,
      logLevel: "info",
      enableMetrics: true,
      workDir: "/tmp/athena/sandbox",
      ...config,
    };

    this.logger = new Logger(this.config.logLevel);
    this.metrics = this.initializeMetrics();

    // Initialize worker pool
    this.workerPool = new WorkerPool({
      size: this.config.workerCount,
      timeout: this.config.workerTimeout,
      maxAge: 1000, // Recycle after 1000 executions
      idleTimeout: 300000, // Kill if idle >5min
    });

    // Initialize resource monitor with fixed limits
    this.resourceMonitor = new ResourceMonitor({
      timeout: 5000,
      memory: 100,
      disk: 10,
      fileDescriptors: 10,
    });
  }

  /**
   * Initialize executor: warm up worker pool
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      this.logger.warn("Executor already initialized");
      return;
    }

    this.logger.info(
      `Initializing DenoExecutor with ${this.config.workerCount} workers...`
    );
    this.startTime = Date.now();

    try {
      // Warm up worker pool
      const startWarmup = Date.now();
      await this.workerPool.warmup();
      const warmupTime = Date.now() - startWarmup;

      this.logger.info(
        `Worker pool warmed up in ${warmupTime}ms (${this.config.workerCount} workers ready)`
      );

      // Start background metrics collection
      this.startMetricsCollection();

      this.initialized = true;
    } catch (error) {
      this.logger.error(`Failed to initialize executor: ${error}`);
      throw new Error(`Executor initialization failed: ${error}`);
    }
  }

  /**
   * Execute code in sandbox
   */
  async execute(context: ExecutionContext): Promise<ExecutionResult> {
    if (!this.initialized) {
      throw new Error("Executor not initialized");
    }

    if (this.shutdownStarted) {
      throw new Error("Executor is shutting down");
    }

    if (this.executionQueue.length >= this.config.maxConcurrent) {
      throw new Error(
        `Queue full (${this.config.maxConcurrent}). Please retry later.`
      );
    }

    return new Promise((resolve, reject) => {
      const request: ExecutionRequest = {
        context,
        resolve,
        reject,
        requestedAt: Date.now(),
      };

      // Track execution state
      const state: ExecutionState = {
        id: context.id,
        state: "queued",
      };
      this.executionStates.set(context.id, state);

      // Add to queue
      this.executionQueue.push(request);

      // Process queue asynchronously
      this.processQueue();

      // Set timeout for execution
      const timeoutMs = context.timeout + 1000; // Add 1s buffer
      request.timeoutId = setTimeout(() => {
        this.handleExecutionTimeout(context.id);
      }, timeoutMs) as any;
    });
  }

  /**
   * Process execution queue
   */
  private async processQueue(): Promise<void> {
    // Prevent concurrent queue processing
    if (this.processingQueue) {
      return;
    }
    this.processingQueue = true;

    try {
      while (this.executionQueue.length > 0 && !this.shutdownStarted) {
        // Try to acquire a worker with timeout
        const request = this.executionQueue[0];
        const worker = await this.workerPool.acquire(100);

        if (worker) {
          // Remove from queue and execute
          this.executionQueue.shift();

          // Execute asynchronously
          this.executeOnWorker(request, worker).catch((error) => {
            this.logger.error(`Worker execution error: ${error}`);
            request.reject(error);
          });
        } else {
          // No worker available, wait a bit
          await new Promise((resolve) => setTimeout(resolve, 50));
        }
      }
    } finally {
      this.processingQueue = false;
    }
  }

  private processingQueue = false;

  /**
   * Execute code on specific worker
   */
  private async executeOnWorker(
    request: ExecutionRequest,
    worker: WorkerState
  ): Promise<void> {
    const { context } = request;
    const executionState = this.executionStates.get(context.id);

    if (!executionState) {
      throw new Error(`Execution state not found: ${context.id}`);
    }

    // Update state
    executionState.state = "assigned";
    executionState.worker = worker;
    executionState.startTime = Date.now();

    // Start resource monitoring
    this.resourceMonitor.start(context.id);

    try {
      this.logger.debug(`Executing on worker ${worker.id}: ${context.id}`);

      // Send code to worker for execution
      // This is simplified - real implementation would use IPC
      const result = await this.executeCodeInWorker(worker, context);

      // Check resource violations
      const violation = this.resourceMonitor.check(context.id);
      if (violation) {
        this.logger.warn(
          `Resource violation: ${violation.type} (limit: ${violation.limit}, current: ${violation.current})`
        );
        this.metrics.resourceViolations[violation.type] =
          (this.metrics.resourceViolations[violation.type] || 0) + 1;
      }

      // Get resource usage
      const resourceUsage = this.resourceMonitor.stop(context.id);

      // Update execution state
      executionState.state = "done";
      executionState.endTime = Date.now();
      executionState.result = {
        ...result,
        resourceUsage,
      };

      // Update metrics
      const duration = executionState.endTime - (executionState.startTime || 0);
      this.updateMetrics(duration, result);

      // Clear timeout
      if (request.timeoutId) {
        clearTimeout(request.timeoutId);
      }

      // Return result
      request.resolve(executionState.result);
    } catch (error) {
      // Update execution state
      executionState.state = "error";
      executionState.error = error as Error;

      this.logger.error(
        `Execution failed: ${context.id}: ${error}`
      );

      // Update metrics
      this.metrics.totalErrors++;

      // Clear timeout
      if (request.timeoutId) {
        clearTimeout(request.timeoutId);
      }

      // Reject promise
      request.reject(error as Error);
    } finally {
      // Release worker back to pool
      this.workerPool.release(worker);

      // Continue processing queue
      this.processQueue();
    }
  }

  /**
   * Execute code in worker (simplified version)
   *
   * Real implementation would:
   * 1. Serialize code and context
   * 2. Send to worker process via IPC
   * 3. Wait for response with timeout
   * 4. Deserialize result
   */
  private async executeCodeInWorker(
    worker: WorkerState,
    context: ExecutionContext
  ): Promise<Omit<ExecutionResult, "resourceUsage">> {
    // Simulate execution with placeholder
    // Real implementation would communicate with worker process

    return {
      success: true,
      output: { placeholder: "Worker execution would happen here" },
      logs: [
        {
          level: "info",
          message: "Code executed successfully",
          timestamp: Date.now(),
        },
      ],
      metrics: {
        executionTimeMs: 100,
        memoryPeakMb: 10,
        toolCallsCount: 0,
        avgToolLatencyMs: 0,
        timeoutCount: 0,
        errorCount: 0,
        resultSizeBytes: 1024,
      },
    };
  }

  /**
   * Handle execution timeout
   */
  private handleExecutionTimeout(executionId: string): void {
    const state = this.executionStates.get(executionId);
    if (state && state.state !== "done" && state.state !== "error") {
      state.state = "error";
      state.error = new Error("Execution timeout (5s limit exceeded)");

      this.logger.warn(`Execution timeout: ${executionId}`);
      this.metrics.totalErrors++;

      // Find and reject the request
      const requestIndex = this.executionQueue.findIndex(
        (r) => r.context.id === executionId
      );
      if (requestIndex >= 0) {
        const request = this.executionQueue.splice(requestIndex, 1)[0];
        request.reject(state.error);
      }
    }
  }

  /**
   * Get current metrics
   */
  getMetrics(): ExecutorMetrics {
    const poolStatus = this.workerPool.getStatus();

    return {
      activeWorkers: poolStatus.busy,
      queuedExecutions: this.executionQueue.length,
      totalExecutions: this.metrics.totalExecutions,
      averageLatencyMs: this.metrics.averageLatencyMs,
      workerUtilization: (poolStatus.busy / poolStatus.total) * 100,
      memoryUsageMb: poolStatus.memoryUsageMb,
      totalErrors: this.metrics.totalErrors,
      resourceViolations: this.metrics.resourceViolations,
      uptimeMs: Date.now() - this.startTime,
    };
  }

  /**
   * Graceful shutdown
   */
  async shutdown(): Promise<void> {
    if (this.shutdownStarted) {
      return;
    }

    this.logger.info("Shutting down DenoExecutor...");
    this.shutdownStarted = true;

    // Wait for in-flight executions
    const maxWaitMs = 10000;
    const startWait = Date.now();
    while (
      this.executionQueue.length > 0 &&
      Date.now() - startWait < maxWaitMs
    ) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // Force-reject remaining queued requests
    for (const request of this.executionQueue) {
      request.reject(new Error("Executor shutting down"));
    }
    this.executionQueue = [];

    // Shutdown worker pool
    await this.workerPool.shutdown();

    this.logger.info("DenoExecutor shutdown complete");
  }

  /**
   * Initialize metrics
   */
  private initializeMetrics(): ExecutorMetrics {
    return {
      activeWorkers: 0,
      queuedExecutions: 0,
      totalExecutions: 0,
      averageLatencyMs: 0,
      workerUtilization: 0,
      memoryUsageMb: 0,
      totalErrors: 0,
      resourceViolations: {},
      uptimeMs: 0,
    };
  }

  /**
   * Start background metrics collection
   */
  private startMetricsCollection(): void {
    if (!this.config.enableMetrics) {
      return;
    }

    // Collect metrics every 10 seconds
    const intervalId = setInterval(() => {
      const poolStatus = this.workerPool.getStatus();
      const executionMetrics = this.getMetrics();

      if (this.config.logLevel === "debug") {
        this.logger.debug(
          `Metrics: workers=${poolStatus.busy}/${poolStatus.total}, queued=${this.executionQueue.length}, avg_latency=${executionMetrics.averageLatencyMs}ms`
        );
      }
    }, 10000);

    // Store interval ID for cleanup on shutdown
    (this as any).metricsCollectionId = intervalId;
  }

  /**
   * Update metrics after execution
   */
  private updateMetrics(
    executionTimeMs: number,
    result: Omit<ExecutionResult, "resourceUsage">
  ): void {
    this.metrics.totalExecutions++;

    // Update average latency using exponential moving average
    const alpha = 0.1; // Weight for new value
    this.metrics.averageLatencyMs =
      this.metrics.averageLatencyMs * (1 - alpha) + executionTimeMs * alpha;
  }
}

/**
 * Simple Logger
 */
class Logger {
  constructor(private level: string) {}

  debug(message: string): void {
    if (["debug"].includes(this.level)) {
      console.log(`[DEBUG] ${message}`);
    }
  }

  info(message: string): void {
    if (["debug", "info"].includes(this.level)) {
      console.log(`[INFO] ${message}`);
    }
  }

  warn(message: string): void {
    if (["debug", "info", "warn"].includes(this.level)) {
      console.warn(`[WARN] ${message}`);
    }
  }

  error(message: string): void {
    console.error(`[ERROR] ${message}`);
  }
}

export default DenoExecutor;
