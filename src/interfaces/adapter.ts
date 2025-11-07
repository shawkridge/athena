/**
 * Tool Adapter Interface & Contracts
 *
 * This file defines the interface that all MCP tool adapters must implement.
 * Tool adapters bridge between TypeScript code running in the Deno sandbox
 * and Python handlers in the Athena core.
 *
 * @see docs/API_CONTRACTS.md for comprehensive documentation
 * @see src/interfaces/execution.ts for execution context types
 */

import type {
  ToolContext,
  ExecutionError,
  ValidationResult,
  ValidationError,
} from "./execution.ts";

/**
 * Tool Adapter
 *
 * Main interface that all MCP tool adapters must implement.
 * Adapters expose safe operations as TypeScript functions.
 */
export interface ToolAdapter {
  /** Unique adapter name (e.g., "episodic", "semantic") */
  name: string;

  /** Category of operations (e.g., "memory", "retrieval") */
  category: string;

  /** Version of adapter API (semver) */
  version: string;

  /** List of operations this adapter supports */
  operations: ToolOperation[];

  /**
   * Execute a tool operation
   *
   * @param operationName - Name of operation (e.g., "recall")
   * @param parameters - Operation parameters (validated)
   * @param context - Execution context (session, tools, state)
   * @returns Promise resolving to operation result
   * @throws ExecutionError on failure
   */
  execute(
    operationName: string,
    parameters: Record<string, unknown>,
    context: ToolContext
  ): Promise<unknown>;

  /**
   * Get operation metadata
   *
   * @param operationName - Operation to look up
   * @returns Operation metadata or undefined if not found
   */
  getOperation(operationName: string): ToolOperation | undefined;

  /**
   * Validate operation parameters
   *
   * @param operationName - Operation to validate for
   * @param parameters - Parameters to validate
   * @returns ValidationResult with valid flag and errors
   */
  validateParameters(
    operationName: string,
    parameters: Record<string, unknown>
  ): ValidationResult;

  /**
   * Check if operation is available
   *
   * @param operationName - Operation to check
   * @returns Whether operation exists and is available
   */
  hasOperation(operationName: string): boolean;

  /**
   * Get adapter status
   *
   * @returns AdapterStatus with health and availability info
   */
  getStatus(): AdapterStatus;

  /**
   * Cleanup resources (optional)
   *
   * Called when adapter is being shut down
   */
  dispose?(): Promise<void>;
}

/**
 * Tool Operation
 *
 * Metadata for a single operation exposed by a tool adapter.
 */
export interface ToolOperation {
  /** Operation name (e.g., "recall", "remember") */
  name: string;

  /** Full operation ID (e.g., "episodic/recall") */
  id: string;

  /** Category this operation belongs to */
  category: string;

  /** Human-readable description */
  description: string;

  /** Long-form description with examples */
  longDescription?: string;

  /** Parameters this operation accepts */
  parameters: ToolParameter[];

  /** Return value specification */
  returns: ToolTypeSpec;

  /** Example usage code snippet */
  example?: string;

  /** Example result */
  exampleResult?: unknown;

  /** Whether this operation is deprecated */
  deprecated?: boolean;

  /** If deprecated, which operation to use instead */
  replacedBy?: string;

  /** Related operations */
  related?: string[];

  /** Expected execution time in milliseconds */
  expectedDurationMs?: number;

  /** Timeout for this operation (milliseconds) */
  timeoutMs?: number;

  /** Whether operation requires specific permissions */
  permissions?: string[];

  /** Whether operation modifies state */
  mutating?: boolean;

  /** Whether operation reads sensitive data */
  readsSensitive?: boolean;

  /** Whether operation writes sensitive data */
  writesSensitive?: boolean;

  /** Cost in abstract units (for rate limiting) */
  cost?: number;

  /** Supported since version */
  since?: string;

  /** Tags for categorization */
  tags?: string[];
}

/**
 * Tool Parameter
 *
 * Specification for a single parameter to a tool operation.
 */
export interface ToolParameter {
  /** Parameter name */
  name: string;

  /** Parameter type specification */
  type: ToolTypeSpec;

  /** Whether this parameter is required */
  required: boolean;

  /** Default value if not provided */
  default?: unknown;

  /** Human-readable description */
  description: string;

  /** Validation rules for this parameter */
  validation?: ToolValidationRule[];

  /** Examples of valid values */
  examples?: unknown[];

  /** Position in parameter list (for positional args) */
  position?: number;

  /** Whether this is a rest parameter (variadic) */
  rest?: boolean;

  /** Deprecation notice */
  deprecated?: string;
}

/**
 * Tool Type Specification
 *
 * Specification for a data type used in operations.
 */
export interface ToolTypeSpec {
  /** Base type name */
  name:
    | "string"
    | "number"
    | "integer"
    | "boolean"
    | "object"
    | "array"
    | "any"
    | "null"
    | "undefined"
    | "union"
    | "intersection"
    | "enum";

  /** For arrays: type of elements */
  elementType?: ToolTypeSpec;

  /** For objects: property specifications */
  properties?: Record<string, ToolTypeSpec>;

  /** For enum: allowed values */
  enum?: unknown[];

  /** For union: possible types */
  oneOf?: ToolTypeSpec[];

  /** For intersection: required types */
  allOf?: ToolTypeSpec[];

  /** For optional values: inner type */
  inner?: ToolTypeSpec;

  /** Human-readable type description */
  description?: string;

  /** Example value */
  example?: unknown;

  /** Whether value can be null */
  nullable?: boolean;

  /** Minimum length (for strings/arrays) */
  minLength?: number;

  /** Maximum length (for strings/arrays) */
  maxLength?: number;

  /** Minimum value (for numbers) */
  minimum?: number;

  /** Maximum value (for numbers) */
  maximum?: number;

  /** Regex pattern (for strings) */
  pattern?: string;

  /** Format hint (e.g., "uuid", "email", "iso-date") */
  format?: string;
}

/**
 * Tool Validation Rule
 *
 * A rule for validating a tool parameter value.
 */
export interface ToolValidationRule {
  /** Rule type */
  type:
    | "type"
    | "minLength"
    | "maxLength"
    | "minimum"
    | "maximum"
    | "pattern"
    | "enum"
    | "format"
    | "custom";

  /** Value for the rule (e.g., regex pattern, min value) */
  value?: unknown;

  /** Error message if validation fails */
  message: string;

  /** Custom validation function (if type === "custom") */
  validator?: (value: unknown) => boolean;
}

/**
 * Adapter Status
 *
 * Status information about a tool adapter.
 */
export interface AdapterStatus {
  /** Adapter name */
  name: string;

  /** Whether adapter is healthy */
  healthy: boolean;

  /** Current status message */
  status: "ready" | "initializing" | "degraded" | "error";

  /** Uptime in milliseconds */
  uptimeMs: number;

  /** Number of successful operations */
  successCount: number;

  /** Number of failed operations */
  errorCount: number;

  /** Average operation latency (milliseconds) */
  avgLatencyMs: number;

  /** Last error (if any) */
  lastError?: ExecutionError;

  /** Timestamp of last check */
  lastCheckTime: string;

  /** Custom metrics */
  metrics?: Record<string, unknown>;
}

/**
 * Adapter Factory
 *
 * Factory for creating tool adapter instances.
 */
export interface ToolAdapterFactory {
  /**
   * Create an adapter instance
   *
   * @returns New adapter instance
   */
  create(): Promise<ToolAdapter>;

  /**
   * Get factory metadata
   *
   * @returns Metadata about this factory
   */
  getMetadata(): ToolAdapterFactoryMetadata;
}

/**
 * Adapter Factory Metadata
 */
export interface ToolAdapterFactoryMetadata {
  /** Factory name */
  name: string;

  /** Adapter name this factory creates */
  adapterName: string;

  /** Factory version */
  version: string;

  /** Description */
  description: string;

  /** Whether factory is ready */
  ready: boolean;

  /** Configuration required */
  requiresConfig?: boolean;

  /** Configuration schema */
  configSchema?: Record<string, unknown>;
}

/**
 * Adapter Configuration
 *
 * Configuration options for a tool adapter.
 */
export interface ToolAdapterConfig {
  /** Adapter name */
  name: string;

  /** Whether to enable this adapter */
  enabled?: boolean;

  /** Timeout for operations (milliseconds) */
  timeout?: number;

  /** Maximum result size (bytes) */
  maxResultSize?: number;

  /** Rate limiting configuration */
  rateLimit?: {
    /** Max operations per minute */
    perMinute?: number;

    /** Max operations per hour */
    perHour?: number;
  };

  /** Logging configuration */
  logging?: {
    /** Log level */
    level?: "debug" | "info" | "warn" | "error";

    /** Whether to log parameters */
    logParameters?: boolean;

    /** Whether to log results */
    logResults?: boolean;
  };

  /** Custom options */
  custom?: Record<string, unknown>;
}

/**
 * Adapter Registry
 *
 * Registry for managing tool adapters.
 */
export interface ToolAdapterRegistry {
  /**
   * Register an adapter
   *
   * @param adapter - Adapter to register
   */
  register(adapter: ToolAdapter): void;

  /**
   * Get adapter by name
   *
   * @param name - Adapter name
   * @returns Adapter or undefined
   */
  get(name: string): ToolAdapter | undefined;

  /**
   * Get all adapters
   *
   * @returns Array of all registered adapters
   */
  getAll(): ToolAdapter[];

  /**
   * Check if adapter exists
   *
   * @param name - Adapter name
   * @returns Whether adapter is registered
   */
  has(name: string): boolean;

  /**
   * Unregister an adapter
   *
   * @param name - Adapter name
   * @returns Whether adapter was removed
   */
  unregister(name: string): boolean;

  /**
   * Get operation
   *
   * @param operationId - Full operation ID (e.g., "episodic/recall")
   * @returns Operation metadata or undefined
   */
  getOperation(operationId: string): ToolOperation | undefined;

  /**
   * Find operations by tag
   *
   * @param tag - Tag to search for
   * @returns Array of matching operations
   */
  findByTag(tag: string): ToolOperation[];

  /**
   * Validate operation call
   *
   * @param operationId - Full operation ID
   * @param parameters - Parameters to validate
   * @returns Validation result
   */
  validate(
    operationId: string,
    parameters: Record<string, unknown>
  ): ValidationResult;
}

/**
 * Operation Call
 *
 * Information about a tool operation call.
 */
export interface OperationCall {
  /** Full operation ID */
  operationId: string;

  /** Parameters passed */
  parameters: Record<string, unknown>;

  /** Execution context */
  context: ToolContext;

  /** Start time */
  startTime: number;

  /** Result from operation */
  result?: unknown;

  /** Error if operation failed */
  error?: ExecutionError;

  /** Duration in milliseconds */
  durationMs?: number;

  /** Whether operation succeeded */
  success: boolean;
}

/**
 * Safe Operations Whitelist
 *
 * List of operations approved for sandbox execution.
 * Only operations in this list can be called from within the Deno sandbox.
 */
export const SAFE_OPERATIONS = [
  // Episodic operations
  "episodic/recall",
  "episodic/remember",
  "episodic/forget",
  "episodic/bulk_remember",
  "episodic/query_temporal",
  "episodic/list_events",
  "episodic/get_event",
  "episodic/search_events",

  // Semantic operations
  "semantic/search",
  "semantic/store",
  "semantic/delete",
  "semantic/update",
  "semantic/list_memories",
  "semantic/get_memory",
  "semantic/search_by_embedding",

  // Procedural operations
  "procedural/extract",
  "procedural/execute",
  "procedural/list",
  "procedural/get_effectiveness",
  "procedural/get_procedure",
  "procedural/search_procedures",

  // Prospective operations
  "prospective/create_task",
  "prospective/list_tasks",
  "prospective/complete_task",
  "prospective/update_task",
  "prospective/get_task",
  "prospective/search_tasks",
  "prospective/create_goal",
  "prospective/list_goals",
  "prospective/update_goal",

  // Consolidation operations (read-only)
  "consolidation/get_metrics",
  "consolidation/analyze_patterns",
  "consolidation/get_consolidation_status",

  // Meta operations (read-only)
  "meta/memory_health",
  "meta/get_expertise",
  "meta/get_cognitive_load",
  "meta/get_quality_metrics",
  "meta/get_attention_metrics",

  // Knowledge graph operations (read-mostly)
  "graph/search_entities",
  "graph/get_entity",
  "graph/get_relationships",
  "graph/get_communities",
  "graph/search_relationships",
  "graph/analyze_entity",

  // RAG operations (read-mostly)
  "rag/retrieve",
  "rag/search",
  "rag/hybrid_search",
  "rag/semantic_search",
  "rag/bm25_search",
] as const;

/**
 * Dangerous Operations Blacklist
 *
 * Operations that are forbidden in sandbox execution.
 * These operations can modify system state or access sensitive data.
 */
export const DANGEROUS_OPERATIONS = [
  // Admin operations
  /^admin\/.*/,

  // Configuration changes
  /^config\/.*/,

  // Database operations
  /^database\/truncate$/,
  /^database\/drop$/,
  /^database\/reset$/,

  // System operations
  /^system\/shutdown$/,
  /^system\/restart$/,
  /^system\/reset_database$/,

  // Security operations
  /^security\/.*/,

  // Audit/logging changes
  /^audit\/delete.*$/,
  /^audit\/clear.*$/,

  // User management
  /^user\/.*/,
] as const;

/**
 * Check if operation is whitelisted
 *
 * @param operationId - Full operation ID (e.g., "episodic/recall")
 * @returns Whether operation is safe to execute
 */
export function isOperationWhitelisted(operationId: string): boolean {
  // Check against safe operations list
  if (SAFE_OPERATIONS.includes(operationId as any)) {
    return true;
  }

  // Check against dangerous operations blacklist
  for (const pattern of DANGEROUS_OPERATIONS) {
    if (typeof pattern === "string") {
      if (operationId === pattern) {
        return false;
      }
    } else {
      if (pattern.test(operationId)) {
        return false;
      }
    }
  }

  // Default: deny unknown operations
  return false;
}

export default {
  ToolAdapter,
  ToolOperation,
  ToolParameter,
  ToolTypeSpec,
  ToolValidationRule,
  AdapterStatus,
  ToolAdapterFactory,
  ToolAdapterFactoryMetadata,
  ToolAdapterConfig,
  ToolAdapterRegistry,
  OperationCall,
  SAFE_OPERATIONS,
  DANGEROUS_OPERATIONS,
  isOperationWhitelisted,
};
