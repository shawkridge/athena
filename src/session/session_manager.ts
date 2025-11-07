/**
 * Session Manager
 *
 * Manages execution sessions with persistent state across multiple code runs.
 * Handles session lifecycle, variable storage, execution history, and cleanup.
 *
 * @see src/session/session_store.ts for persistence layer
 */

/**
 * Session Configuration
 */
export interface SessionConfig {
  /** Session time-to-live in milliseconds (default: 24 hours) */
  ttl: number;

  /** Maximum concurrent sessions (default: 1000) */
  maxSessions: number;

  /** Enable persistent storage */
  persistState: boolean;

  /** Cleanup interval in milliseconds (default: 1 hour) */
  cleanupInterval: number;
}

/**
 * Execution Record
 */
export interface ExecutionRecord {
  /** Execution timestamp */
  timestamp: number;

  /** Code that was executed */
  code: string;

  /** Execution result */
  result: unknown;

  /** Error (if any) */
  error?: Error;

  /** Execution metrics */
  metrics: ExecutionMetrics;
}

/**
 * Execution Metrics
 */
export interface ExecutionMetrics {
  executionTimeMs: number;
  memoryPeakMb: number;
  toolCallsCount: number;
  avgToolLatencyMs: number;
}

/**
 * Session State
 */
export interface Session {
  /** Unique session ID */
  id: string;

  /** User ID (optional) */
  userId?: string;

  /** Session creation timestamp */
  createdAt: number;

  /** Last activity timestamp */
  lastActivity: number;

  /** Session variables (user-accessible) */
  variables: Map<string, unknown>;

  /** Tool-specific state */
  toolState: Record<string, unknown>;

  /** Execution history (last N records) */
  executionHistory: ExecutionRecord[];

  /** Custom metadata */
  metadata: Record<string, unknown>;

  /** Whether session is active */
  active: boolean;
}

/**
 * Session Manager
 *
 * Manages session lifecycle and persistence.
 */
export class SessionManager {
  private sessions: Map<string, Session> = new Map();
  private config: SessionConfig;
  private cleanupIntervalId?: number;

  constructor(config: Partial<SessionConfig> = {}) {
    this.config = {
      ttl: 24 * 60 * 60 * 1000, // 24 hours
      maxSessions: 1000,
      persistState: true,
      cleanupInterval: 60 * 60 * 1000, // 1 hour
      ...config,
    };

    // Start cleanup interval
    this.startCleanup();
  }

  /**
   * Create a new session
   */
  createSession(userId?: string): string {
    if (this.sessions.size >= this.config.maxSessions) {
      throw new Error(
        `Maximum sessions (${this.config.maxSessions}) reached. Please retry later.`
      );
    }

    const sessionId = this.generateSessionId();
    const now = Date.now();

    const session: Session = {
      id: sessionId,
      userId,
      createdAt: now,
      lastActivity: now,
      variables: new Map(),
      toolState: {},
      executionHistory: [],
      metadata: {},
      active: true,
    };

    this.sessions.set(sessionId, session);

    console.log(
      `[SessionManager] Created session: ${sessionId}${userId ? ` (user: ${userId})` : ""}`
    );

    return sessionId;
  }

  /**
   * Get session by ID
   */
  getSession(sessionId: string): Session | null {
    const session = this.sessions.get(sessionId);

    if (!session) {
      return null;
    }

    // Check if session has expired
    if (Date.now() - session.lastActivity > this.config.ttl) {
      console.log(
        `[SessionManager] Session expired: ${sessionId}`
      );
      this.sessions.delete(sessionId);
      return null;
    }

    return session;
  }

  /**
   * Set session variable
   */
  setVariable(
    sessionId: string,
    name: string,
    value: unknown
  ): void {
    const session = this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    session.variables.set(name, value);
    session.lastActivity = Date.now();
  }

  /**
   * Get session variable
   */
  getVariable(sessionId: string, name: string): unknown {
    const session = this.getSession(sessionId);
    if (!session) {
      return undefined;
    }

    session.lastActivity = Date.now();
    return session.variables.get(name);
  }

  /**
   * Delete session variable
   */
  deleteVariable(sessionId: string, name: string): boolean {
    const session = this.getSession(sessionId);
    if (!session) {
      return false;
    }

    session.lastActivity = Date.now();
    return session.variables.delete(name);
  }

  /**
   * Get all session variables
   */
  getVariables(sessionId: string): Record<string, unknown> {
    const session = this.getSession(sessionId);
    if (!session) {
      return {};
    }

    const variables: Record<string, unknown> = {};
    for (const [key, value] of session.variables) {
      variables[key] = value;
    }

    return variables;
  }

  /**
   * Update tool state
   */
  setToolState(
    sessionId: string,
    toolName: string,
    state: unknown
  ): void {
    const session = this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    session.toolState[toolName] = state;
    session.lastActivity = Date.now();
  }

  /**
   * Get tool state
   */
  getToolState(sessionId: string, toolName: string): unknown {
    const session = this.getSession(sessionId);
    if (!session) {
      return null;
    }

    session.lastActivity = Date.now();
    return session.toolState[toolName];
  }

  /**
   * Record execution in session history
   */
  recordExecution(
    sessionId: string,
    code: string,
    result: unknown,
    metrics: ExecutionMetrics,
    error?: Error
  ): void {
    const session = this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    const record: ExecutionRecord = {
      timestamp: Date.now(),
      code,
      result,
      error,
      metrics,
    };

    // Keep last 100 records
    session.executionHistory.unshift(record);
    if (session.executionHistory.length > 100) {
      session.executionHistory = session.executionHistory.slice(0, 100);
    }

    session.lastActivity = Date.now();
  }

  /**
   * Get execution history
   */
  getExecutionHistory(
    sessionId: string,
    limit: number = 10
  ): ExecutionRecord[] {
    const session = this.getSession(sessionId);
    if (!session) {
      return [];
    }

    session.lastActivity = Date.now();
    return session.executionHistory.slice(0, limit);
  }

  /**
   * Close session (mark inactive)
   */
  closeSession(sessionId: string): void {
    const session = this.getSession(sessionId);
    if (session) {
      session.active = false;
      console.log(
        `[SessionManager] Closed session: ${sessionId}`
      );
    }
  }

  /**
   * Delete session
   */
  deleteSession(sessionId: string): void {
    this.sessions.delete(sessionId);
    console.log(
      `[SessionManager] Deleted session: ${sessionId}`
    );
  }

  /**
   * Get session count
   */
  getSessionCount(): number {
    return this.sessions.size;
  }

  /**
   * Get sessions for user
   */
  getSessionsByUser(userId: string): Session[] {
    const userSessions: Session[] = [];

    for (const session of this.sessions.values()) {
      if (session.userId === userId && this.getSession(session.id)) {
        userSessions.push(session);
      }
    }

    return userSessions;
  }

  /**
   * Get session metadata
   */
  getSessionMetadata(sessionId: string): Record<string, unknown> | null {
    const session = this.getSession(sessionId);
    if (!session) {
      return null;
    }

    return {
      id: session.id,
      userId: session.userId,
      createdAt: session.createdAt,
      lastActivity: session.lastActivity,
      active: session.active,
      variableCount: session.variables.size,
      executionCount: session.executionHistory.length,
      ageMs: Date.now() - session.createdAt,
      inactiveMs: Date.now() - session.lastActivity,
      ...session.metadata,
    };
  }

  /**
   * Start background cleanup
   */
  private startCleanup(): void {
    this.cleanupIntervalId = setInterval(() => {
      this.cleanup();
    }, this.config.cleanupInterval) as any;
  }

  /**
   * Cleanup expired sessions
   */
  private cleanup(): void {
    const now = Date.now();
    let cleaned = 0;

    for (const [sessionId, session] of this.sessions) {
      if (now - session.lastActivity > this.config.ttl) {
        this.sessions.delete(sessionId);
        cleaned++;
      }
    }

    if (cleaned > 0) {
      console.log(
        `[SessionManager] Cleaned up ${cleaned} expired sessions`
      );
    }
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    return `sess-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Shutdown manager
   */
  async shutdown(): Promise<void> {
    if (this.cleanupIntervalId) {
      clearInterval(this.cleanupIntervalId);
    }

    console.log(
      `[SessionManager] Shutting down with ${this.sessions.size} active sessions`
    );

    // Optionally persist sessions to database here
    // await this.persistAllSessions();
  }
}

export default SessionManager;
