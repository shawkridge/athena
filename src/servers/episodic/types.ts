/**
 * Episodic Memory Layer Types
 *
 * Interfaces for episodic memory operations (events with timestamps and context)
 */

/**
 * Memory record from episodic layer
 */
export interface Memory {
  id: string;
  timestamp: number;
  content: string;
  context: Record<string, unknown>;
  confidence: number;
  source: string;
  tags: string[];
  relatedMemories: string[];
  expiresAt?: number;
}

/**
 * Options for recall operation
 */
export interface RecallOptions {
  query: string;
  limit?: number;
  minConfidence?: number;
  timeRange?: {
    start: number;
    end: number;
  };
  tags?: string[];
}

/**
 * Result from recall operation
 */
export interface RecallResult {
  memories: Memory[];
  totalMatches: number;
  executionTimeMs: number;
  confidence: number;
}

/**
 * Memory input for remember operation
 */
export interface RememberInput {
  content: string;
  context?: Record<string, unknown>;
  tags?: string[];
  source?: string;
  expiresAt?: number;
}

/**
 * Result from remember operation
 */
export interface RememberResult {
  id: string;
  stored: boolean;
  timestamp: number;
  message: string;
}

/**
 * Forget operation input
 */
export interface ForgetInput {
  ids?: string[];
  olderThan?: number;
  withTags?: string[];
  limit?: number;
}

/**
 * Result from forget operation
 */
export interface ForgetResult {
  deleted: number;
  message: string;
}

/**
 * Bulk remember input
 */
export interface BulkRememberInput {
  memories: RememberInput[];
  parallel?: boolean;
}

/**
 * Result from bulk remember
 */
export interface BulkRememberResult {
  stored: number;
  failed: number;
  ids: string[];
}

/**
 * Temporal query input
 */
export interface TemporalQueryInput {
  startTime?: number;
  endTime?: number;
  limit?: number;
  sortBy?: 'timestamp' | 'confidence';
}

/**
 * List events input
 */
export interface ListEventsInput {
  limit?: number;
  offset?: number;
  sortBy?: 'timestamp' | 'confidence';
  order?: 'asc' | 'desc';
}

/**
 * Operation metadata
 */
export interface OperationMetadata {
  name: string;
  description: string;
  parameters: Record<string, ParameterSchema>;
}

/**
 * Parameter schema for operation metadata
 */
export interface ParameterSchema {
  type: string;
  required?: boolean;
  default?: unknown;
  description?: string;
}
