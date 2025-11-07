/**
 * Output Filtering & Privacy Interfaces
 *
 * This file defines the contracts for filtering sensitive data and privacy
 * transformations applied to code execution results before they're returned
 * to the model context.
 *
 * @see docs/SECURITY_MODEL.md for privacy strategy details
 * @see src/runtime/deno_config.ts for filtering configuration
 */

/**
 * Data Filter
 *
 * Filters data to remove sensitive information and enforce size limits.
 */
export interface DataFilter {
  /**
   * Apply filtering to data
   *
   * @param data - Data to filter
   * @param context - Filtering context
   * @returns Filtered data
   */
  filter(data: unknown, context: FilterContext): FilterResult;

  /**
   * Get filter metadata
   *
   * @returns Filter metadata
   */
  getMetadata(): FilterMetadata;

  /**
   * Check if data needs filtering
   *
   * @param data - Data to check
   * @returns Whether data needs filtering
   */
  needsFiltering(data: unknown): boolean;
}

/**
 * Filter Context
 *
 * Context for filtering operations.
 */
export interface FilterContext {
  /** Session ID */
  sessionId: string;

  /** User ID (if available) */
  userId?: string;

  /** Maximum result size in bytes */
  maxResultSize: number;

  /** Whether sensitive fields should be redacted */
  redactSensitive: boolean;

  /** Whether sensitive values should be tokenized */
  tokenizeSensitive: boolean;

  /** Whether to enable compression for large results */
  enableCompression: boolean;

  /** Compression threshold in bytes */
  compressionThreshold: number;

  /** Custom filters to apply */
  customFilters?: CustomFilter[];

  /** Metadata about the operation */
  metadata?: Record<string, unknown>;
}

/**
 * Custom Filter
 *
 * Custom filtering logic applied to results.
 */
export interface CustomFilter {
  /** Filter name */
  name: string;

  /** Filter type */
  type: "field" | "value" | "pattern" | "custom";

  /** Target field path (for field filters) */
  path?: string;

  /** Pattern to match (for pattern filters) */
  pattern?: string | RegExp;

  /** Transformation to apply */
  transform: (value: unknown) => unknown;

  /** Whether filter is enabled */
  enabled: boolean;

  /** Priority (higher = applies first) */
  priority?: number;
}

/**
 * Filter Result
 *
 * Result of applying filters to data.
 */
export interface FilterResult {
  /** Filtered data */
  data: unknown;

  /** Original data size in bytes */
  originalSize: number;

  /** Filtered data size in bytes */
  filteredSize: number;

  /** Size reduction percentage */
  reductionPercent: number;

  /** Whether data was compressed */
  compressed: boolean;

  /** Whether sensitive fields were removed */
  sensitiveFieldsRemoved: string[];

  /** Whether sensitive values were tokenized */
  sensitiveValuesTokenized: number;

  /** Filters applied */
  filtersApplied: string[];

  /** Warnings (if any) */
  warnings: FilterWarning[];

  /** Metadata about filtering */
  metadata?: Record<string, unknown>;
}

/**
 * Filter Warning
 *
 * Warning about filtering operations.
 */
export interface FilterWarning {
  /** Warning type */
  type: "truncated" | "compression_failed" | "size_limit_exceeded" | "other";

  /** Warning message */
  message: string;

  /** Affected data path */
  path?: string;

  /** Severity level */
  severity: "info" | "warning" | "error";
}

/**
 * Filter Metadata
 *
 * Metadata about a filter.
 */
export interface FilterMetadata {
  /** Filter name */
  name: string;

  /** Filter type */
  type: string;

  /** Filter version */
  version: string;

  /** Description */
  description: string;

  /** Configuration schema */
  configSchema?: Record<string, unknown>;
}

/**
 * Sensitive Field Detector
 *
 * Detects sensitive fields in data.
 */
export interface SensitiveFieldDetector {
  /**
   * Detect sensitive fields
   *
   * @param data - Data to analyze
   * @returns Detected sensitive fields
   */
  detect(data: unknown): SensitiveField[];

  /**
   * Check if field name is sensitive
   *
   * @param fieldName - Field name to check
   * @returns Whether field is considered sensitive
   */
  isSensitiveField(fieldName: string): boolean;

  /**
   * Check if value matches sensitive pattern
   *
   * @param value - Value to check
   * @returns Whether value matches sensitive pattern
   */
  isSensitiveValue(value: string): boolean;
}

/**
 * Sensitive Field
 *
 * Information about a sensitive field found in data.
 */
export interface SensitiveField {
  /** Field path (dot notation) */
  path: string;

  /** Field name */
  fieldName: string;

  /** Field value */
  value: unknown;

  /** Reason field is sensitive */
  reason: string;

  /** Confidence level (0-1) */
  confidence: number;

  /** Suggested action */
  suggestedAction: "redact" | "tokenize" | "mask" | "remove";
}

/**
 * Data Tokenizer
 *
 * Tokenizes sensitive values to prevent data leakage.
 */
export interface DataTokenizer {
  /**
   * Tokenize a sensitive value
   *
   * @param value - Value to tokenize
   * @param context - Tokenization context
   * @returns Tokenized value
   */
  tokenize(value: string, context: TokenizationContext): string;

  /**
   * Check if value is tokenized
   *
   * @param value - Value to check
   * @returns Whether value is tokenized
   */
  isTokenized(value: string): boolean;

  /**
   * Get token metadata
   *
   * @param token - Token to analyze
   * @returns Token metadata
   */
  getTokenMetadata(token: string): TokenMetadata | null;
}

/**
 * Tokenization Context
 *
 * Context for tokenization operations.
 */
export interface TokenizationContext {
  /** Session ID (for context) */
  sessionId: string;

  /** Type of sensitive data */
  dataType:
    | "api_key"
    | "password"
    | "token"
    | "secret"
    | "pii"
    | "credit_card"
    | "ssn"
    | "other";

  /** Whether to include hash */
  includeHash: boolean;

  /** Hash algorithm to use */
  hashAlgorithm?: "sha256" | "sha1" | "md5";

  /** Custom prefix for token */
  prefix?: string;
}

/**
 * Token Metadata
 *
 * Metadata about a tokenized value.
 */
export interface TokenMetadata {
  /** Original value hash */
  hash: string;

  /** Data type that was tokenized */
  dataType: string;

  /** Tokenization timestamp */
  timestamp: string;

  /** Session ID */
  sessionId: string;

  /** Whether token is still valid */
  valid: boolean;

  /** Token expiration time (if applicable) */
  expiresAt?: string;
}

/**
 * Result Compressor
 *
 * Compresses large results for transmission.
 */
export interface ResultCompressor {
  /**
   * Compress data
   *
   * @param data - Data to compress
   * @param context - Compression context
   * @returns Compressed result
   */
  compress(data: unknown, context: CompressionContext): CompressionResult;

  /**
   * Decompress data
   *
   * @param data - Compressed data
   * @returns Decompressed data
   */
  decompress(data: string): unknown;

  /**
   * Estimate compressed size
   *
   * @param data - Data to estimate
   * @returns Estimated size in bytes
   */
  estimateSize(data: unknown): number;

  /**
   * Get compressor metadata
   *
   * @returns Compressor metadata
   */
  getMetadata(): CompressorMetadata;
}

/**
 * Compression Context
 *
 * Context for compression operations.
 */
export interface CompressionContext {
  /** Maximum output size in bytes */
  maxSize: number;

  /** Compression level (1-9, higher = more compression) */
  level?: number;

  /** Compression algorithm */
  algorithm?: "gzip" | "brotli" | "deflate";

  /** Whether to preserve structure */
  preserveStructure?: boolean;

  /** Custom compression options */
  custom?: Record<string, unknown>;
}

/**
 * Compression Result
 *
 * Result of compression operation.
 */
export interface CompressionResult {
  /** Compressed data (as base64 string) */
  compressed: string;

  /** Original size in bytes */
  originalSize: number;

  /** Compressed size in bytes */
  compressedSize: number;

  /** Compression ratio */
  ratio: number;

  /** Compression algorithm used */
  algorithm: string;

  /** Whether compression was successful */
  success: boolean;

  /** Error message (if compression failed) */
  error?: string;
}

/**
 * Compressor Metadata
 *
 * Metadata about a compressor.
 */
export interface CompressorMetadata {
  /** Compressor name */
  name: string;

  /** Supported algorithms */
  algorithms: string[];

  /** Supported formats */
  formats: string[];

  /** Maximum compression level */
  maxLevel: number;

  /** Default compression level */
  defaultLevel: number;
}

/**
 * Size Limiter
 *
 * Enforces size limits on data.
 */
export interface SizeLimiter {
  /**
   * Apply size limits to data
   *
   * @param data - Data to limit
   * @param maxSize - Maximum size in bytes
   * @returns Limited data
   */
  limit(data: unknown, maxSize: number): SizeLimitResult;

  /**
   * Check if data exceeds limit
   *
   * @param data - Data to check
   * @param maxSize - Maximum size in bytes
   * @returns Whether data exceeds limit
   */
  exceeds(data: unknown, maxSize: number): boolean;

  /**
   * Get data size
   *
   * @param data - Data to measure
   * @returns Size in bytes
   */
  getSize(data: unknown): number;
}

/**
 * Size Limit Result
 *
 * Result of applying size limits.
 */
export interface SizeLimitResult {
  /** Limited data */
  data: unknown;

  /** Original size in bytes */
  originalSize: number;

  /** Limited data size in bytes */
  limitedSize: number;

  /** Whether data was truncated */
  truncated: boolean;

  /** How many bytes were removed */
  bytesRemoved: number;

  /** Truncation strategy used */
  strategy?: "trim" | "sample" | "summarize" | "compress";
}

/**
 * Privacy Policy
 *
 * Policy for privacy transformations.
 */
export interface PrivacyPolicy {
  /** Policy name */
  name: string;

  /** Policy version */
  version: string;

  /** Sensitive fields to redact */
  sensitiveFields: string[];

  /** Sensitive value patterns */
  sensitivePatterns: (string | RegExp)[];

  /** Whether to tokenize sensitive values */
  tokenize: boolean;

  /** Tokenization configuration */
  tokenizationConfig?: TokenizationContext;

  /** Whether to redact sensitive fields */
  redact: boolean;

  /** Custom filters */
  customFilters?: CustomFilter[];

  /** Whether policy is enforced */
  enforced: boolean;

  /** Policy metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Filter Pipeline
 *
 * Pipeline of filters applied in sequence.
 */
export interface FilterPipeline {
  /**
   * Add a filter to the pipeline
   *
   * @param filter - Filter to add
   * @param position - Position in pipeline (optional)
   */
  addFilter(filter: DataFilter, position?: number): void;

  /**
   * Remove a filter from the pipeline
   *
   * @param filterName - Name of filter to remove
   * @returns Whether filter was removed
   */
  removeFilter(filterName: string): boolean;

  /**
   * Apply all filters in pipeline
   *
   * @param data - Data to filter
   * @param context - Filtering context
   * @returns Filtered data
   */
  apply(data: unknown, context: FilterContext): FilterResult;

  /**
   * Get all filters in pipeline
   *
   * @returns Array of filters
   */
  getFilters(): DataFilter[];

  /**
   * Get pipeline metadata
   *
   * @returns Pipeline metadata
   */
  getMetadata(): PipelineMetadata;
}

/**
 * Pipeline Metadata
 *
 * Metadata about a filter pipeline.
 */
export interface PipelineMetadata {
  /** Pipeline name */
  name: string;

  /** Number of filters in pipeline */
  filterCount: number;

  /** Filters in order */
  filters: string[];

  /** Estimated overhead in milliseconds */
  estimatedOverheadMs: number;

  /** Custom metadata */
  custom?: Record<string, unknown>;
}

export default {
  DataFilter,
  FilterContext,
  CustomFilter,
  FilterResult,
  FilterWarning,
  FilterMetadata,
  SensitiveFieldDetector,
  SensitiveField,
  DataTokenizer,
  TokenizationContext,
  TokenMetadata,
  ResultCompressor,
  CompressionContext,
  CompressionResult,
  CompressorMetadata,
  SizeLimiter,
  SizeLimitResult,
  PrivacyPolicy,
  FilterPipeline,
  PipelineMetadata,
};
