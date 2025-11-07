/**
 * Phase 4.4: Circuit Breaker Pattern
 *
 * Implements circuit breaker for resilience under failure conditions.
 * Prevents cascading failures and provides graceful degradation.
 */

/**
 * Circuit breaker state
 */
type CircuitState = 'closed' | 'open' | 'half-open';

/**
 * Circuit breaker statistics
 */
interface CircuitBreakerStats {
  state: CircuitState;
  successCount: number;
  failureCount: number;
  successRate: number;
  lastFailureTime?: number;
  totalOpenDuration: number;
  trips: number;
}

/**
 * Circuit Breaker configuration
 */
interface CircuitBreakerConfig {
  failureThreshold?: number;      // 0-1: failure rate to trip
  successThreshold?: number;      // 0-1: success rate to close
  timeout?: number;                // ms: half-open timeout
  volumeThreshold?: number;        // min requests before evaluating
  onStateChange?: (from: CircuitState, to: CircuitState) => void;
}

/**
 * Circuit Breaker
 *
 * Manages resilience with circuit breaker pattern
 */
export class CircuitBreaker {
  private state: CircuitState = 'closed';
  private successCount = 0;
  private failureCount = 0;
  private lastFailureTime?: number;
  private openedAt?: number;
  private totalOpenDuration = 0;
  private trips = 0;

  private failureThreshold: number;
  private successThreshold: number;
  private timeout: number;
  private volumeThreshold: number;
  private onStateChange?: (from: CircuitState, to: CircuitState) => void;

  private halfOpenTimer?: NodeJS.Timer;
  private resetInterval?: NodeJS.Timer;

  constructor(config: CircuitBreakerConfig = {}) {
    this.failureThreshold = config.failureThreshold || 0.5;      // 50%
    this.successThreshold = config.successThreshold || 0.8;      // 80%
    this.timeout = config.timeout || 60 * 1000;                   // 60s
    this.volumeThreshold = config.volumeThreshold || 10;          // min 10 requests
    this.onStateChange = config.onStateChange;

    // Reset stats periodically
    this.resetInterval = setInterval(() => {
      this.resetStats();
    }, this.timeout);
  }

  /**
   * Execute operation through circuit breaker
   */
  async execute<T = unknown>(fn: () => Promise<T>): Promise<T> {
    // Check circuit state
    if (this.state === 'open') {
      throw new Error('Circuit breaker is OPEN - service unavailable');
    }

    try {
      const result = await fn();
      this.recordSuccess();
      return result;
    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }

  /**
   * Execute with fallback
   */
  async executeWithFallback<T = unknown>(
    fn: () => Promise<T>,
    fallback: () => Promise<T>
  ): Promise<T> {
    try {
      return await this.execute(fn);
    } catch (error) {
      // If circuit is open, use fallback
      if (this.state === 'open') {
        return await fallback();
      }
      throw error;
    }
  }

  /**
   * Get circuit breaker status
   */
  getStatus(): {state: CircuitState; failures: number; successes: number} {
    return {
      state: this.state,
      failures: this.failureCount,
      successes: this.successCount
    };
  }

  /**
   * Get detailed statistics
   */
  getStats(): CircuitBreakerStats {
    const total = this.successCount + this.failureCount;
    const successRate = total > 0 ? this.successCount / total : 0;

    return {
      state: this.state,
      successCount: this.successCount,
      failureCount: this.failureCount,
      successRate,
      lastFailureTime: this.lastFailureTime,
      totalOpenDuration: this.totalOpenDuration,
      trips: this.trips
    };
  }

  /**
   * Reset circuit breaker
   */
  reset(): void {
    const oldState = this.state;
    this.state = 'closed';
    this.successCount = 0;
    this.failureCount = 0;
    this.openedAt = undefined;

    if (this.onStateChange && oldState !== this.state) {
      this.onStateChange(oldState, this.state);
    }
  }

  /**
   * Manually open circuit
   */
  open(): void {
    if (this.state !== 'open') {
      this.changeState('open');
    }
  }

  /**
   * Manually close circuit
   */
  close(): void {
    if (this.state !== 'closed') {
      this.changeState('closed');
      this.successCount = 0;
      this.failureCount = 0;
    }
  }

  /**
   * Get estimated recovery time
   */
  getRecoveryETA(): number {
    if (this.state !== 'open' || !this.openedAt) {
      return 0;
    }

    const elapsed = Date.now() - this.openedAt;
    return Math.max(0, this.timeout - elapsed);
  }

  /**
   * Destroy circuit breaker
   */
  destroy(): void {
    if (this.halfOpenTimer) {
      clearTimeout(this.halfOpenTimer);
    }
    if (this.resetInterval) {
      clearInterval(this.resetInterval);
    }
  }

  /**
   * Record successful operation
   */
  private recordSuccess(): void {
    this.successCount++;
    this.evaluateState();
  }

  /**
   * Record failed operation
   */
  private recordFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();
    this.evaluateState();
  }

  /**
   * Evaluate if state should change
   */
  private evaluateState(): void {
    const total = this.successCount + this.failureCount;

    // Not enough data
    if (total < this.volumeThreshold) {
      return;
    }

    const failureRate = this.failureCount / total;
    const successRate = this.successCount / total;

    switch (this.state) {
      case 'closed':
        // Trip if failure rate is too high
        if (failureRate > this.failureThreshold) {
          this.changeState('open');
        }
        break;

      case 'open':
        // After timeout, try half-open
        if (this.openedAt && Date.now() - this.openedAt > this.timeout) {
          this.changeState('half-open');
        }
        break;

      case 'half-open':
        // Close if success rate is high
        if (successRate > this.successThreshold) {
          this.changeState('closed');
        }
        // Reopen if failure rate is high
        else if (failureRate > this.failureThreshold) {
          this.changeState('open');
        }
        break;
    }
  }

  /**
   * Change circuit state
   */
  private changeState(newState: CircuitState): void {
    const oldState = this.state;
    this.state = newState;

    // Track open duration
    if (oldState === 'open' && newState !== 'open') {
      if (this.openedAt) {
        this.totalOpenDuration += Date.now() - this.openedAt;
      }
    }

    if (newState === 'open' && oldState !== 'open') {
      this.openedAt = Date.now();
      this.trips++;

      // After timeout, try to recover
      this.halfOpenTimer = setTimeout(() => {
        this.changeState('half-open');
      }, this.timeout);
    }

    if (newState === 'closed') {
      this.successCount = 0;
      this.failureCount = 0;
      this.openedAt = undefined;
    }

    if (this.onStateChange) {
      this.onStateChange(oldState, newState);
    }
  }

  /**
   * Reset statistics periodically
   */
  private resetStats(): void {
    // Keep state but reset counts
    if (this.state === 'closed') {
      // Only reset if we haven't had recent failures
      if (!this.lastFailureTime || Date.now() - this.lastFailureTime > this.timeout * 2) {
        this.successCount = 0;
        this.failureCount = 0;
      }
    }
  }
}

/**
 * Multi-circuit breaker system
 */
export class CircuitBreakerManager {
  private breakers: Map<string, CircuitBreaker> = new Map();

  /**
   * Get or create circuit breaker for operation
   */
  getBreaker(operation: string, config?: CircuitBreakerConfig): CircuitBreaker {
    if (!this.breakers.has(operation)) {
      const breaker = new CircuitBreaker({
        ...config,
        onStateChange: (from, to) => {
          console.log(`Circuit breaker '${operation}': ${from} → ${to}`);
        }
      });
      this.breakers.set(operation, breaker);
    }

    return this.breakers.get(operation)!;
  }

  /**
   * Execute with circuit breaker
   */
  async execute<T = unknown>(
    operation: string,
    fn: () => Promise<T>,
    config?: CircuitBreakerConfig
  ): Promise<T> {
    const breaker = this.getBreaker(operation, config);
    return await breaker.execute(fn);
  }

  /**
   * Get all breaker statistics
   */
  getAllStats() {
    const stats: Record<string, CircuitBreakerStats> = {};

    for (const [operation, breaker] of this.breakers) {
      stats[operation] = breaker.getStats();
    }

    return stats;
  }

  /**
   * Destroy all breakers
   */
  destroy(): void {
    for (const breaker of this.breakers.values()) {
      breaker.destroy();
    }
    this.breakers.clear();
  }
}

/**
 * Singleton circuit breaker manager
 */
export const circuitBreakerManager = new CircuitBreakerManager();

/**
 * Usage example
 */
export async function exampleUsage() {
  const breaker = new CircuitBreaker({
    failureThreshold: 0.5,      // Trip at 50% failures
    successThreshold: 0.8,      // Close at 80% success
    timeout: 60 * 1000          // 60s timeout
  });

  // Execute with protection
  try {
    const result = await breaker.executeWithFallback(
      () => callRiskyOperation(),
      () => getDefaultResult()      // Fallback when open
    );
    console.log('Operation succeeded:', result);
  } catch (error) {
    console.error('Circuit breaker failed:', error);
  }

  // Check status
  const stats = breaker.getStats();
  console.log('Circuit state:', stats.state);
  console.log('Success rate:', (stats.successRate * 100).toFixed(1) + '%');

  function callRiskyOperation(): Promise<unknown> {
    return Promise.resolve({});
  }

  function getDefaultResult(): Promise<unknown> {
    return Promise.resolve({});
  }
}
