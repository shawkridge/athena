/**
 * Resource Monitor
 *
 * Monitors and enforces resource limits (timeout, memory, disk, file descriptors)
 * for sandboxed code execution.
 *
 * @see docs/SECURITY_MODEL.md for resource limit specification
 * @see src/runtime/deno_executor.ts for usage
 */

/**
 * Resource Limits
 */
export interface ResourceLimits {
  /** Execution timeout in milliseconds */
  timeout: number;

  /** Memory limit in MB */
  memory: number;

  /** Disk usage limit in MB */
  disk: number;

  /** File descriptor limit */
  fileDescriptors: number;
}

/**
 * Resource Usage
 */
export interface ResourceUsage {
  /** CPU time used in milliseconds */
  cpuTimeMs: number;

  /** Memory used in MB */
  memoryMb: number;

  /** Disk used in MB */
  diskMb: number;

  /** File descriptors used */
  fileDescriptorCount: number;

  /** Wall clock time in milliseconds */
  wallTimeMs: number;
}

/**
 * Resource Violation
 */
export interface ResourceViolation {
  /** Type of resource that was violated */
  type: "timeout" | "memory" | "disk" | "file_descriptor";

  /** The limit that was set */
  limit: number;

  /** Current usage at time of violation */
  current: number;

  /** Whether limit was exceeded */
  exceeded: boolean;
}

/**
 * Execution Monitor (Internal)
 */
interface ExecutionMonitor {
  /** Execution ID */
  executionId: string;

  /** Start time */
  startTimeMs: number;

  /** Resource limits */
  limits: ResourceLimits;

  /** Last known usage */
  lastUsage: ResourceUsage;

  /** Violations detected */
  violations: ResourceViolation[];

  /** Is currently monitoring */
  active: boolean;
}

/**
 * Resource Monitor
 *
 * Tracks and enforces resource limits for code execution.
 */
export class ResourceMonitor {
  private limits: ResourceLimits;
  private monitors: Map<string, ExecutionMonitor> = new Map();
  private checkInterval: number = 100; // Check every 100ms

  constructor(limits: ResourceLimits) {
    this.limits = limits;

    // Validate limits
    if (limits.timeout < 100) {
      throw new Error("Timeout must be at least 100ms");
    }
    if (limits.memory < 10) {
      throw new Error("Memory limit must be at least 10MB");
    }
    if (limits.disk < 1) {
      throw new Error("Disk limit must be at least 1MB");
    }
  }

  /**
   * Start monitoring execution
   */
  start(executionId: string): void {
    if (this.monitors.has(executionId)) {
      throw new Error(`Already monitoring execution: ${executionId}`);
    }

    const monitor: ExecutionMonitor = {
      executionId,
      startTimeMs: Date.now(),
      limits: { ...this.limits },
      lastUsage: {
        cpuTimeMs: 0,
        memoryMb: 0,
        diskMb: 0,
        fileDescriptorCount: 0,
        wallTimeMs: 0,
      },
      violations: [],
      active: true,
    };

    this.monitors.set(executionId, monitor);
  }

  /**
   * Check if execution has violated resource limits
   */
  check(executionId: string): ResourceViolation | null {
    const monitor = this.monitors.get(executionId);
    if (!monitor || !monitor.active) {
      return null;
    }

    // Get current resource usage
    const usage = this.getCurrentUsage(monitor);

    // Check timeout
    if (usage.wallTimeMs > monitor.limits.timeout) {
      const violation: ResourceViolation = {
        type: "timeout",
        limit: monitor.limits.timeout,
        current: usage.wallTimeMs,
        exceeded: true,
      };
      monitor.violations.push(violation);
      return violation;
    }

    // Check memory
    if (usage.memoryMb > monitor.limits.memory) {
      const violation: ResourceViolation = {
        type: "memory",
        limit: monitor.limits.memory,
        current: usage.memoryMb,
        exceeded: true,
      };
      monitor.violations.push(violation);
      return violation;
    }

    // Check disk
    if (usage.diskMb > monitor.limits.disk) {
      const violation: ResourceViolation = {
        type: "disk",
        limit: monitor.limits.disk,
        current: usage.diskMb,
        exceeded: true,
      };
      monitor.violations.push(violation);
      return violation;
    }

    // Check file descriptors
    if (usage.fileDescriptorCount > monitor.limits.fileDescriptors) {
      const violation: ResourceViolation = {
        type: "file_descriptor",
        limit: monitor.limits.fileDescriptors,
        current: usage.fileDescriptorCount,
        exceeded: true,
      };
      monitor.violations.push(violation);
      return violation;
    }

    return null;
  }

  /**
   * Stop monitoring and return final resource usage
   */
  stop(executionId: string): ResourceUsage {
    const monitor = this.monitors.get(executionId);
    if (!monitor) {
      return {
        cpuTimeMs: 0,
        memoryMb: 0,
        diskMb: 0,
        fileDescriptorCount: 0,
        wallTimeMs: 0,
      };
    }

    monitor.active = false;

    // Get final usage
    const finalUsage = this.getCurrentUsage(monitor);

    // Cleanup
    this.monitors.delete(executionId);

    return finalUsage;
  }

  /**
   * Get current resource usage for execution
   */
  getUsage(executionId: string): ResourceUsage {
    const monitor = this.monitors.get(executionId);
    if (!monitor) {
      return {
        cpuTimeMs: 0,
        memoryMb: 0,
        diskMb: 0,
        fileDescriptorCount: 0,
        wallTimeMs: 0,
      };
    }

    return this.getCurrentUsage(monitor);
  }

  /**
   * Get current usage snapshot
   */
  private getCurrentUsage(monitor: ExecutionMonitor): ResourceUsage {
    const now = Date.now();
    const wallTimeMs = now - monitor.startTimeMs;

    // In real implementation, would query:
    // 1. /proc/[pid]/stat for CPU time
    // 2. /proc/[pid]/status for memory
    // 3. du on sandbox directory for disk
    // 4. lsof for file descriptors

    // Simulated values for now
    return {
      cpuTimeMs: Math.min(wallTimeMs * 0.8, 5000), // Estimate CPU as 80% of wall time
      memoryMb: this.getSimulatedMemory(wallTimeMs),
      diskMb: this.getSimulatedDisk(wallTimeMs),
      fileDescriptorCount: this.getSimulatedFileDescriptors(wallTimeMs),
      wallTimeMs,
    };
  }

  /**
   * Get simulated memory usage (for testing)
   */
  private getSimulatedMemory(wallTimeMs: number): number {
    // Simulate gradual memory increase
    // In real implementation, would read from /proc/[pid]/status
    return Math.min(50 + (wallTimeMs / 100) * 0.1, 100); // Max 100MB
  }

  /**
   * Get simulated disk usage (for testing)
   */
  private getSimulatedDisk(wallTimeMs: number): number {
    // Simulate disk usage
    // In real implementation, would use du command
    return Math.min((wallTimeMs / 100) * 0.01, 10); // Max 10MB
  }

  /**
   * Get simulated file descriptor count (for testing)
   */
  private getSimulatedFileDescriptors(wallTimeMs: number): number {
    // In real implementation, would parse lsof output
    return Math.min(3 + Math.floor((wallTimeMs / 100) * 0.1), 10); // Start at 3 (stdin, stdout, stderr)
  }

  /**
   * Get all violations for execution
   */
  getViolations(executionId: string): ResourceViolation[] {
    const monitor = this.monitors.get(executionId);
    return monitor ? monitor.violations : [];
  }

  /**
   * Get limit configuration
   */
  getLimits(): ResourceLimits {
    return { ...this.limits };
  }

  /**
   * Check if any executions are currently being monitored
   */
  hasActiveMonitors(): boolean {
    return this.monitors.size > 0;
  }

  /**
   * Get count of active monitors
   */
  getActiveMonitorCount(): number {
    return Array.from(this.monitors.values()).filter((m) => m.active).length;
  }
}

export default ResourceMonitor;
