/**
 * Deno Security Configuration for Athena MCP Code Execution
 *
 * This file defines the security permissions and resource limits for the Deno sandbox
 * that executes untrusted agent code.
 *
 * Principle: Whitelist-only permissions (deny by default)
 *
 * @see docs/SECURITY_MODEL.md for detailed security model
 */

/**
 * Deno Permission Model
 *
 * These are the ONLY permissions allowed in the sandbox.
 * All other permissions are denied by default.
 */
export const DenoPermissions = {
  // Read access: ONLY to /tmp/athena/tools (tool definitions)
  read: ["/tmp/athena/tools"],

  // Write access: ONLY to /tmp/athena/sandbox/<session_id> (temp files)
  write: ["/tmp/athena/sandbox"],

  // Environment variables: ONLY ATHENA_SESSION_ID
  env: ["ATHENA_SESSION_ID"],

  // High-resolution time (needed for performance monitoring)
  hrtime: true,

  // Network: DISABLED (no network access)
  net: false,

  // Subprocess: DISABLED (no child processes)
  run: false,

  // FFI: DISABLED (no native code execution)
  ffi: false,

  // System: DISABLED (no system access)
  sys: false,

  // File locking: DISABLED (no file locks)
  flock: false,
} as const;

/**
 * V8 Resource Limits
 *
 * These flags limit the V8 JavaScript engine's resource usage.
 */
export const V8Flags = [
  // Heap size limit: 100MB max
  "--max-old-space-size=100",

  // Semi-space size: 16MB each
  "--max-semi-space-size=16",

  // Enable GC (garbage collection)
  "--expose-gc",

  // Disable experimental features
  "--no-experimental-worker-threads",

  // Stack size (in KB): 8MB
  "--stack-size=8192",
] as const;

/**
 * Runtime Resource Limits
 *
 * Hard limits enforced at the runtime level.
 */
export const RuntimeLimits = {
  // Maximum execution time: 5 seconds
  executionTimeoutMs: 5000,

  // Maximum heap size: 100MB (enforced by V8)
  heapSizeMb: 100,

  // Maximum stack size: 8MB (enforced by V8)
  stackSizeMb: 8,

  // Maximum temporary disk usage: 10MB
  diskQuotaMb: 10,

  // Maximum number of open files: 10
  maxOpenFiles: 10,

  // Maximum string size: 1MB
  maxStringSize: 1_000_000,

  // Maximum array length: 100,000 items
  maxArrayLength: 100_000,

  // Maximum object properties: 10,000
  maxObjectProperties: 10_000,

  // Maximum JSON depth: 50 levels
  maxJsonDepth: 50,
} as const;

/**
 * Tool Adapter Security Configuration
 */
export const ToolAdapterConfig = {
  // Safe operations (whitelist - can be called from sandbox)
  safeOperations: [
    // Episodic operations
    "episodic/recall",
    "episodic/remember",
    "episodic/forget",
    "episodic/bulk_remember",
    "episodic/query_temporal",

    // Semantic operations
    "semantic/search",
    "semantic/store",
    "semantic/delete",
    "semantic/update",

    // Procedural operations
    "procedural/extract",
    "procedural/execute",
    "procedural/list",
    "procedural/get_effectiveness",

    // Prospective operations
    "prospective/create_task",
    "prospective/list_tasks",
    "prospective/complete_task",

    // Consolidation operations (read-only)
    "consolidation/get_metrics",
    "consolidation/analyze_patterns",

    // Meta operations (read-only)
    "meta/memory_health",
    "meta/get_expertise",
    "meta/get_cognitive_load",

    // Knowledge graph operations (read-mostly)
    "graph/search_entities",
    "graph/get_relationships",
    "graph/get_communities",

    // RAG operations (read-mostly)
    "rag/retrieve",
    "rag/search",
  ],

  // Dangerous operations (blacklist - cannot be called)
  dangerousOperations: [
    "admin/*",              // All admin operations
    "config/*",             // Configuration changes
    "system/reset_database",
    "system/shutdown",
    "security/*",           // Security settings
    "database/truncate",    // Data deletion
    "database/drop",        // Data deletion
  ],

  // Maximum timeout for tool adapters: 30 seconds
  toolTimeoutMs: 30000,

  // Maximum result size from tool: 10MB
  maxResultSizeMb: 10,

  // Maximum request size to tool: 1MB
  maxRequestSizeMb: 1,
} as const;

/**
 * Output Filtering Configuration
 */
export const OutputFilteringConfig = {
  // Sensitive fields to redact
  sensitiveFields: [
    "api_key",
    "apiKey",
    "API_KEY",
    "token",
    "TOKEN",
    "secret",
    "SECRET",
    "password",
    "PASSWORD",
    "auth",
    "AUTH",
    "credential",
    "CREDENTIAL",
    "bearer",
    "BEARER",
    "authorization",
    "AUTHORIZATION",
    "x-api-key",
    "X-API-KEY",
    "private_key",
    "PRIVATE_KEY",
    "access_token",
    "ACCESS_TOKEN",
    "refresh_token",
    "REFRESH_TOKEN",
    "aws_secret",
    "AWS_SECRET",
    "gcp_key",
    "GCP_KEY",
    "azure_key",
    "AZURE_KEY",
  ],

  // Patterns that indicate sensitive values
  sensitivePatterns: [
    /sk_[\w]{20,}/,              // Stripe key pattern
    /ghp_[\w]{36}/,              // GitHub token pattern
    /^[A-Za-z0-9+/]{40,}=*$/,   // Generic base64 secret pattern
    /-----BEGIN RSA PRIVATE KEY-----/,  // RSA key header
    /-----BEGIN PRIVATE KEY-----/,      // Private key header
  ],

  // Maximum output size: 10MB
  maxOutputSizeMb: 10,

  // Compression enabled for large results
  compressionEnabled: true,

  // Compression threshold: 1MB
  compressionThresholdMb: 1,
} as const;

/**
 * Execution Monitoring & Alerting Configuration
 */
export const MonitoringConfig = {
  // Alert on timeout execution
  timeoutAlert: {
    enabled: true,
    threshold: 1,
    window: 300_000, // 5 minutes
    action: "rate_limit_user",
  },

  // Alert on out-of-memory
  oomAlert: {
    enabled: true,
    threshold: 1,
    action: "kill_worker",
  },

  // Alert on high error rate
  errorRateAlert: {
    enabled: true,
    threshold: 0.5, // 50% error rate
    window: 300_000, // 5 minutes
    action: "circuit_break",
  },

  // Alert on sensitive data leak
  sensitiveDataAlert: {
    enabled: true,
    threshold: 1,
    action: "redact_and_alert",
  },

  // Rate limiting
  rateLimiting: {
    enabled: true,
    maxExecutionsPerMinute: 100,
    maxExecutionsPerHour: 10_000,
  },

  // Metrics retention
  metricsRetentionDays: 30,
  auditLogRetentionDays: 90,
} as const;

/**
 * Security Testing Configuration
 *
 * Used for validating sandbox security.
 */
export const SecurityTestingConfig = {
  // Number of attack scenarios to test
  attackScenarios: 100,

  // Test timeout: 10 seconds
  testTimeoutMs: 10_000,

  // Coverage requirement: 100%
  coverageTarget: 1.0,

  // Attack categories to test
  categories: [
    "spoofing",      // STRIDE: Spoofing identity
    "tampering",     // STRIDE: Tampering with data
    "repudiation",   // STRIDE: Denying actions
    "information",   // STRIDE: Information disclosure
    "denial",        // STRIDE: Denial of service
    "elevation",     // STRIDE: Elevation of privilege
  ],
} as const;

/**
 * Deno Command Line Arguments
 *
 * Generate the complete deno run command with proper security settings.
 */
export function generateDenoCommand(): string[] {
  const args = ["deno", "run"];

  // Add V8 flags
  for (const flag of V8Flags) {
    args.push(`--v8-flags=${flag}`);
  }

  // Add permissions
  if (DenoPermissions.read.length > 0) {
    args.push(`--allow-read=${DenoPermissions.read.join(",")}`);
  }
  if (DenoPermissions.write.length > 0) {
    args.push(`--allow-write=${DenoPermissions.write.join(",")}`);
  }
  if (DenoPermissions.env !== false && Array.isArray(DenoPermissions.env)) {
    args.push(`--allow-env=${DenoPermissions.env.join(",")}`);
  }
  if (DenoPermissions.hrtime) {
    args.push("--allow-hrtime");
  }

  // Note: net, run, ffi, sys, flock are disabled (not added)

  return args;
}

/**
 * Security Configuration Summary
 *
 * This is printed on startup to confirm security settings.
 */
export const SecuritySummary = {
  title: "Athena MCP Code Execution - Security Configuration",
  timestamp: new Date().toISOString(),
  version: "1.0",

  permissions: {
    allowed: [
      "✅ Read: /tmp/athena/tools (tool definitions only)",
      "✅ Write: /tmp/athena/sandbox (temp files only)",
      "✅ Env: ATHENA_SESSION_ID only",
      "✅ HRTime: enabled (for performance monitoring)",
    ],
    denied: [
      "❌ Network access (disabled)",
      "❌ Subprocess execution (disabled)",
      "❌ FFI/native code (disabled)",
      "❌ System access (disabled)",
      "❌ File locking (disabled)",
    ],
  },

  limits: {
    execution: `${RuntimeLimits.executionTimeoutMs}ms timeout`,
    memory: `${RuntimeLimits.heapSizeMb}MB heap limit`,
    disk: `${RuntimeLimits.diskQuotaMb}MB temp storage`,
    strings: `${RuntimeLimits.maxStringSize.toLocaleString()} bytes max`,
    files: `${RuntimeLimits.maxOpenFiles} open files max`,
  },

  safeguards: [
    "Whitelist-only permission model",
    "Hard execution timeout enforcement",
    "V8 heap size limits",
    "Stack size limits",
    "Output filtering (sensitive field removal)",
    "Tool adapter whitelist validation",
    "Parameter type checking",
    "Resource monitoring & alerts",
    "Audit logging of all executions",
  ],
} as const;

export default {
  permissions: DenoPermissions,
  v8Flags: V8Flags,
  limits: RuntimeLimits,
  toolAdapter: ToolAdapterConfig,
  outputFiltering: OutputFilteringConfig,
  monitoring: MonitoringConfig,
  testing: SecurityTestingConfig,
  generateCommand: generateDenoCommand,
  summary: SecuritySummary,
};
