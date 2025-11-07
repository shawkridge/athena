/**
 * Code Execution Interfaces
 *
 * Core contracts for the MCP code execution engine.
 * Defines the request/response contracts for executing TypeScript code
 * in the Deno sandbox.
 *
 * @see docs/SECURITY_MODEL.md for security model
 * @see docs/API_CONTRACTS.md for detailed documentation
 */

/**
 * Tool Context
 *
 * Context available to executing code, includes:
 * - Available tools (safe operations whitelist)
 * - Session state (persistent across executions in same session)
 * - Execution metadata (session ID, user ID, etc.)
 */
export interface ToolContext {
  /** Unique session identifier */
  sessionId: string;

  /** User identifier (optional) */
  userId?: string;

  /** List of available tool operations */
  availableTools: string[];

  /** Session state (persisted across executions) */
  sessionState: Record<string, unknown>;

  /** Request metadata */
  metadata: {
    /** Start time of execution */
    startTime: number;

    /** Execution timeout in milliseconds */
    timeout: number;

    /** Memory limit in MB */
    memoryLimit: number;

    /** Request ID for tracing */
    requestId: string;
  };
}

/**
 * Code Execution Request
 *
 * Request to execute TypeScript code in the sandbox.
 */
export interface CodeExecutionRequest {
  /** TypeScript code to execute */
  code: string;

  /** Tool context (available tools, session state) */
  toolContext: ToolContext;

  /** Execution timeout in milliseconds (default: 5000) */
  timeout?: number;

  /** Memory limit in MB (default: 100) */
  memoryLimit?: number;

  /** Maximum result size in bytes (default: 10MB) */
  maxResultSize?: number;

  /** Enable output filtering (default: true) */
  enableOutputFiltering?: boolean;

  /** Enable execution logging (default: true) */
  enableLogging?: boolean;

  /** Optional metadata for tracing */
  metadata?: Record<string, unknown>;
}

/**
 * Execution Metrics
 *
 * Performance metrics for a code execution.
 */
export interface ExecutionMetrics {
  /** Total execution time in milliseconds */
  executionTimeMs: number;

  /** Peak memory usage in MB */
  memoryPeakMb: number;

  /** Number of tool calls made */
  toolCallsCount: number;

  /** Average latency per tool call in milliseconds */
  avgToolLatencyMs: number;

  /** Number of timeouts encountered */
  timeoutCount: number;

  /** Number of errors encountered */
  errorCount: number;

  /** Result size in bytes */
  resultSizeBytes: number;

  /** Whether output was filtered */
  outputFiltered: boolean;

  /** Custom metrics */
  custom?: Record<string, unknown>;
}

/**
 * Execution Error
 *
 * Error information from code execution.
 */
export interface ExecutionError {
  /** Error type (syntax, runtime, timeout, etc.) */
  type:
    | "syntax_error"
    | "runtime_error"
    | "timeout_error"
    | "resource_error"
    | "permission_error"
    | "validation_error";

  /** Human-readable error message */
  message: string;

  /** Stack trace (if available) */
  stack?: string;

  /** Line number where error occurred (if available) */
  line?: number;

  /** Column number where error occurred (if available) */
  column?: number;

  /** Source code snippet around error (if available) */
  snippet?: string;

  /** Suggested fix (if available) */
  suggestion?: string;
}

/**
 * Code Execution Result
 *
 * Result of executing TypeScript code in the sandbox.
 */
export interface CodeExecutionResult {
  /** Whether execution succeeded */
  success: boolean;

  /** Output/return value from code */
  output?: unknown;

  /** Execution errors (if any) */
  errors: ExecutionError[];

  /** Console logs during execution */
  logs: string[];

  /** Execution metrics (timing, memory, etc.) */
  metrics: ExecutionMetrics;

  /** Session state after execution (updated) */
  sessionState: Record<string, unknown>;

  /** Whether result was filtered for sensitive data */
  wasFiltered: boolean;

  /** Original result size before filtering (bytes) */
  originalSizeBytes: number;

  /** Filtered result size (bytes) */
  filteredSizeBytes: number;
}

/**
 * Tool Call
 *
 * Information about a call to a tool adapter.
 */
export interface ToolCall {
  /** Tool operation name (e.g., "episodic/recall") */
  operation: string;

  /** Parameters passed to tool */
  parameters: Record<string, unknown>;

  /** Result from tool */
  result: unknown;

  /** Execution time in milliseconds */
  executionTimeMs: number;

  /** Whether call succeeded */
  success: boolean;

  /** Error (if any) */
  error?: ExecutionError;
}

/**
 * Execution Log Entry
 *
 * Single entry in execution log.
 */
export interface ExecutionLogEntry {
  /** Timestamp of execution */
  timestamp: string;

  /** Session ID */
  sessionId: string;

  /** Code hash (SHA-256) */
  codeHash: string;

  /** Code length in bytes */
  codeLength: number;

  /** Code execution request (sanitized) */
  request: Omit<CodeExecutionRequest, "code">;

  /** Execution result */
  result: CodeExecutionResult;

  /** User ID (if available) */
  userId?: string;

  /** Source/context (if available) */
  source?: string;
}

/**
 * Session State
 *
 * Persistent state maintained across executions in same session.
 */
export interface SessionState {
  /** Session ID */
  sessionId: string;

  /** User ID (optional) */
  userId?: string;

  /** Execution count in this session */
  executionCount: number;

  /** Total execution time in milliseconds */
  totalExecutionTimeMs: number;

  /** Session creation timestamp */
  createdAt: string;

  /** Last execution timestamp */
  lastExecutedAt: string;

  /** Session state (custom data) */
  data: Record<string, unknown>;

  /** Session metadata */
  metadata: {
    /** Whether session is active */
    active: boolean;

    /** Timeout duration in milliseconds */
    timeout: number;

    /** Maximum results per execution */
    maxResults: number;
  };
}

/**
 * Tool Adapter Interface
 *
 * Interface that tool adapters must implement.
 * Bridges between sandbox code and Python tool handlers.
 */
export interface ToolAdapter {
  /** Tool name */
  name: string;

  /** Tool category (episodic, semantic, etc.) */
  category: string;

  /** List of operations this adapter supports */
  operations: Operation[];

  /**
   * Execute a tool operation
   *
   * @param operation - Operation name (e.g., "recall")
   * @param params - Operation parameters
   * @param context - Execution context
   * @returns Operation result
   */
  execute(
    operation: string,
    params: Record<string, unknown>,
    context: ToolContext
  ): Promise<unknown>;

  /**
   * Get operation signature
   *
   * @param operation - Operation name
   * @returns Operation details (parameters, return type, etc.)
   */
  getOperation(operation: string): Operation | undefined;

  /**
   * Validate operation parameters
   *
   * @param operation - Operation name
   * @param params - Parameters to validate
   * @returns Validation result
   */
  validateParameters(
    operation: string,
    params: Record<string, unknown>
  ): ValidationResult;
}

/**
 * Tool Operation
 *
 * Metadata for a single tool operation.
 */
export interface Operation {
  /** Operation name (e.g., "recall") */
  name: string;

  /** Full operation ID (e.g., "episodic/recall") */
  id: string;

  /** Human-readable description */
  description: string;

  /** Parameter specifications */
  parameters: ParameterSpec[];

  /** Return value type specification */
  returns: TypeSpec;

  /** Whether operation is deprecated */
  deprecated?: boolean;

  /** Replacement operation (if deprecated) */
  replacedBy?: string;

  /** Examples of usage */
  examples?: string[];

  /** Related operations */
  related?: string[];
}

/**
 * Parameter Specification
 *
 * Specification for a single parameter.
 */
export interface ParameterSpec {
  /** Parameter name */
  name: string;

  /** Parameter type */
  type: TypeSpec;

  /** Whether parameter is required */
  required: boolean;

  /** Default value (if any) */
  default?: unknown;

  /** Human-readable description */
  description: string;

  /** Validation rules */
  validation?: ValidationRule[];
}

/**
 * Type Specification
 *
 * Specification for a data type.
 */
export interface TypeSpec {
  /** Type name (string, number, object, array, etc.) */
  name: string;

  /** For arrays: element type */
  elementType?: TypeSpec;

  /** For objects: property specifications */
  properties?: Record<string, TypeSpec>;

  /** For enum: allowed values */
  enum?: unknown[];

  /** For union: possible types */
  oneOf?: TypeSpec[];

  /** For optional: inner type */
  inner?: TypeSpec;

  /** Human-readable description */
  description?: string;
}

/**
 * Validation Rule
 *
 * Rule for validating a parameter value.
 */
export interface ValidationRule {
  /** Rule type (minLength, maxLength, pattern, etc.) */
  type:
    | "minLength"
    | "maxLength"
    | "minimum"
    | "maximum"
    | "pattern"
    | "enum"
    | "custom";

  /** Rule value (regex pattern, min value, etc.) */
  value?: unknown;

  /** Error message if validation fails */
  message: string;
}

/**
 * Validation Result
 *
 * Result of parameter validation.
 */
export interface ValidationResult {
  /** Whether validation passed */
  valid: boolean;

  /** Validation errors (if any) */
  errors: ValidationError[];

  /** Validated and coerced parameters */
  parameters?: Record<string, unknown>;
}

/**
 * Validation Error
 *
 * Error from parameter validation.
 */
export interface ValidationError {
  /** Parameter name that failed validation */
  parameter: string;

  /** Error message */
  message: string;

  /** Actual value that failed validation */
  actual?: unknown;

  /** Expected value or constraint */
  expected?: unknown;

  /** Rule that failed */
  rule?: ValidationRule;
}

/**
 * Code Execution Options
 *
 * Optional configuration for code execution.
 */
export interface CodeExecutionOptions {
  /** Timeout in milliseconds */
  timeout?: number;

  /** Memory limit in MB */
  memoryLimit?: number;

  /** Maximum result size in MB */
  maxResultSize?: number;

  /** Enable output filtering */
  enableOutputFiltering?: boolean;

  /** Enable execution logging */
  enableLogging?: boolean;

  /** Enable performance monitoring */
  enableMetrics?: boolean;

  /** Custom metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Execution Statistics
 *
 * Aggregated statistics for executions.
 */
export interface ExecutionStatistics {
  /** Total executions */
  totalExecutions: number;

  /** Successful executions */
  successfulExecutions: number;

  /** Failed executions */
  failedExecutions: number;

  /** Average execution time in milliseconds */
  avgExecutionTimeMs: number;

  /** P50 execution time in milliseconds */
  p50ExecutionTimeMs: number;

  /** P95 execution time in milliseconds */
  p95ExecutionTimeMs: number;

  /** P99 execution time in milliseconds */
  p99ExecutionTimeMs: number;

  /** Average memory usage in MB */
  avgMemoryMb: number;

  /** Peak memory usage in MB */
  peakMemoryMb: number;

  /** Success rate (0-1) */
  successRate: number;

  /** Most common error types */
  commonErrors: Record<string, number>;

  /** Most frequently called tools */
  frequentTools: Record<string, number>;
}

export default {
  ToolContext,
  CodeExecutionRequest,
  CodeExecutionResult,
  ExecutionMetrics,
  ExecutionError,
  ToolCall,
  ExecutionLogEntry,
  SessionState,
  ToolAdapter,
  Operation,
  ParameterSpec,
  TypeSpec,
  ValidationRule,
  ValidationResult,
  ValidationError,
  CodeExecutionOptions,
  ExecutionStatistics,
};
