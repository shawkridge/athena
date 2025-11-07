/**
 * Athena Local Resilience - Simplified Circuit Breaker for Solo Development
 *
 * Provides graceful failure handling without distributed complexity.
 * Perfect for local AI-first development where you want fast failure recovery
 * and clear visibility into failures.
 *
 * Three states:
 * - CLOSED: Normal operation, all calls go through
 * - OPEN: Too many failures, fast-fail new calls
 * - HALF_OPEN: Recovery mode, limited calls to test if service recovered
 */

/**
 * Circuit state
 */
type CircuitState = 'closed' | 'open' | 'half_open';

/**
 * Circuit breaker status
 */
interface CircuitStatus {
  state: CircuitState;
  failures: number;
  successes: number;
  failureRate: number;
  nextRetryAt?: number;
}

/**
 * Local Circuit Breaker - Optimized for single-user local execution
 *
 * Simpler than distributed version: no multi-instance concerns, just
 * pure local resilience for graceful failure handling.
 *
 * @example
 *   const breaker = new LocalCircuitBreaker({
 *     failureThreshold: 0.5,    // Open at 50% failure
 *     successThreshold: 0.8,    // Close at 80% success
 *     timeout: 60000            // 60 second timeout
 *   });
 *
 *   try {
 *     const result = await breaker.execute(() =>
 *       recall('query', 10)
 *     );
 *   } catch (error) {
 *     // Handle failure or fallback
 *   }
 */
export class LocalCircuitBreaker {
  private state: CircuitState = 'closed';
  private failures = 0;
  private successes = 0;
  private lastFailureTime?: number;
  private openedAt?: number;

  private failureThreshold: number;
  private successThreshold: number;
  private timeout: number;
  private minVolume: number = 5;  // Minimum requests before evaluating

  private recoveryTimer?: NodeJS.Timer;

  constructor(config: {
    failureThreshold?: number;   // 0-1: failure rate to open circuit
    successThreshold?: number;   // 0-1: success rate to close circuit
    timeout?: number;             // ms: time before retrying after open
  } = {}) {
    this.failureThreshold = config.failureThreshold || 0.5;      // 50%
    this.successThreshold = config.successThreshold || 0.8;      // 80%
    this.timeout = config.timeout || 60 * 1000;                   // 60s
  }

  /**
   * Execute operation through circuit breaker
   *
   * @example
   *   const result = await breaker.execute(() => recall('query'));
   */
  async execute<T = unknown>(fn: () => Promise<T>): Promise<T> {
    // Fast-fail if open
    if (this.state === 'open') {
      throw new Error('Circuit breaker is OPEN');
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
   *
   * If circuit is open, use fallback instead of throwing.
   *
   * @example
   *   const result = await breaker.executeWithFallback(
   *     () => recall('query', 10),
   *     () => getRecent(10)  // Fallback
   *   );
   */
  async executeWithFallback<T = unknown>(
    fn: () => Promise<T>,
    fallback: () => Promise<T>
  ): Promise<T> {
    try {
      return await this.execute(fn);
    } catch (error) {
      if (this.state === 'open') {
        // Circuit open - use fallback
        return await fallback();
      }
      throw error;
    }
  }

  /**
   * Get circuit status
   *
   * @example
   *   const status = breaker.getStatus();
   *   if (status.state === 'open') {
   *     console.log('Service unhealthy, retrying in', status.nextRetryAt);
   *   }
   */
  getStatus(): CircuitStatus {
    const total = this.successes + this.failures;
    const failureRate = total > 0 ? this.failures / total : 0;

    return {
      state: this.state,
      failures: this.failures,
      successes: this.successes,
      failureRate,
      nextRetryAt: this.state === 'open' ? this.openedAt! + this.timeout : undefined
    };
  }

  /**
   * Reset circuit breaker
   */
  reset(): void {
    this.state = 'closed';
    this.failures = 0;
    this.successes = 0;
    this.openedAt = undefined;

    if (this.recoveryTimer) {
      clearTimeout(this.recoveryTimer);
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
    }
  }

  /**
   * Destroy and cleanup
   */
  destroy(): void {
    if (this.recoveryTimer) {
      clearTimeout(this.recoveryTimer);
    }
  }

  /**
   * Private: Record successful call
   */
  private recordSuccess(): void {
    this.successes++;
    this.evaluateState();
  }

  /**
   * Private: Record failed call
   */
  private recordFailure(): void {
    this.failures++;
    this.lastFailureTime = Date.now();
    this.evaluateState();
  }

  /**
   * Private: Evaluate if state should change
   */
  private evaluateState(): void {
    const total = this.successes + this.failures;

    // Not enough data yet
    if (total < this.minVolume) {
      return;
    }

    const failureRate = this.failures / total;
    const successRate = this.successes / total;

    switch (this.state) {
      case 'closed':
        // Trip if failure rate is too high
        if (failureRate > this.failureThreshold) {
          this.changeState('open');
        }
        break;

      case 'open':
        // After timeout, try recovery
        if (this.openedAt && Date.now() - this.openedAt > this.timeout) {
          this.changeState('half_open');
        }
        break;

      case 'half_open':
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
   * Private: Change state with logging
   */
  private changeState(newState: CircuitState): void {
    const oldState = this.state;
    this.state = newState;

    // Log state change
    console.log(
      `[Circuit Breaker] ${oldState} → ${newState} ` +
      `(${this.successes} successes, ${this.failures} failures)`
    );

    // Set up recovery timer for open state
    if (newState === 'open') {
      this.openedAt = Date.now();

      this.recoveryTimer = setTimeout(() => {
        this.changeState('half_open');
      }, this.timeout);
    }

    // Reset counters when closing
    if (newState === 'closed') {
      this.successes = 0;
      this.failures = 0;
      this.openedAt = undefined;
    }
  }
}

/**
 * Multi-operation circuit breaker manager
 *
 * Manage breakers for different operation types.
 *
 * @example
 *   const manager = new CircuitBreakerManager();
 *
 *   const result = await manager.execute(
 *     'episodic/recall',
 *     () => recall('query', 10)
 *   );
 */
export class CircuitBreakerManager {
  private breakers = new Map<string, LocalCircuitBreaker>();
  private config: {
    failureThreshold: number;
    successThreshold: number;
    timeout: number;
  };

  constructor(config: {
    failureThreshold?: number;
    successThreshold?: number;
    timeout?: number;
  } = {}) {
    this.config = {
      failureThreshold: config.failureThreshold || 0.5,
      successThreshold: config.successThreshold || 0.8,
      timeout: config.timeout || 60000
    };
  }

  /**
   * Execute operation with circuit breaker
   *
   * @example
   *   const result = await manager.execute(
   *     'semantic/search',
   *     () => search('query', 10)
   *   );
   */
  async execute<T = unknown>(
    operation: string,
    fn: () => Promise<T>
  ): Promise<T> {
    const breaker = this.getBreaker(operation);
    return await breaker.execute(fn);
  }

  /**
   * Execute with fallback
   *
   * @example
   *   const result = await manager.executeWithFallback(
   *     'recall',
   *     () => recall('query', 10),
   *     () => getRecent(10)
   *   );
   */
  async executeWithFallback<T = unknown>(
    operation: string,
    fn: () => Promise<T>,
    fallback: () => Promise<T>
  ): Promise<T> {
    const breaker = this.getBreaker(operation);
    return await breaker.executeWithFallback(fn, fallback);
  }

  /**
   * Get all breaker statuses
   */
  getAllStatuses() {
    const statuses: Record<string, CircuitStatus> = {};

    for (const [operation, breaker] of this.breakers) {
      statuses[operation] = breaker.getStatus();
    }

    return statuses;
  }

  /**
   * Reset all breakers
   */
  resetAll(): void {
    for (const breaker of this.breakers.values()) {
      breaker.reset();
    }
  }

  /**
   * Cleanup
   */
  destroy(): void {
    for (const breaker of this.breakers.values()) {
      breaker.destroy();
    }
    this.breakers.clear();
  }

  /**
   * Private: Get or create breaker for operation
   */
  private getBreaker(operation: string): LocalCircuitBreaker {
    if (!this.breakers.has(operation)) {
      this.breakers.set(
        operation,
        new LocalCircuitBreaker(this.config)
      );
    }

    return this.breakers.get(operation)!;
  }
}

/**
 * Singleton circuit breaker manager instance
 */
let sharedManager: CircuitBreakerManager | null = null;

/**
 * Get shared circuit breaker manager
 *
 * @example
 *   const result = await getCircuitBreakerManager().execute(
 *     'recall',
 *     () => recall('query', 10)
 *   );
 */
export function getCircuitBreakerManager(): CircuitBreakerManager {
  if (!sharedManager) {
    sharedManager = new CircuitBreakerManager({
      failureThreshold: 0.5,
      successThreshold: 0.8,
      timeout: 60000
    });
  }
  return sharedManager;
}
