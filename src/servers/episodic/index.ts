/**
 * Episodic Memory Operations
 *
 * Functions for storing, retrieving, and managing episodic memories
 * (events and experiences with timestamps).
 *
 * @packageDocumentation
 */

// Re-export all operations
export { recall, getRecent, recallWithMetrics, recallByTags } from './recall';
export {
  remember,
  rememberWithOptions,
  rememberDecision,
  rememberInsight,
  rememberError,
} from './remember';
export { forget, forgetOlderThan, forgetWithTags, forgetWithOptions, forgetByPattern, forgetLowConfidence } from './forget';
export { bulkRemember, bulkRememberSession, bulkRememberBatched, bulkRememberAtomic, bulkRememberDedup } from './bulk_remember';
export {
  queryTemporal,
  queryLastDays,
  queryDate,
  queryAround,
  queryOverlap,
  queryByInterval,
  getTemporalStats,
} from './query_temporal';
export {
  listEvents,
  getAllEvents,
  countEvents,
  getPage,
  getRecent,
  getOldest,
  getMostConfident,
  getLeastConfident,
  searchPage,
  exportAll,
} from './list_events';

// Re-export types
export type {
  Memory,
  RecallOptions,
  RecallResult,
  RememberInput,
  RememberResult,
  ForgetInput,
  ForgetResult,
  BulkRememberInput,
  BulkRememberResult,
  TemporalQueryInput,
  ListEventsInput,
  OperationMetadata,
  ParameterSchema,
} from './types';

/**
 * Episodic memory operations metadata
 *
 * Describes all available operations in this layer with their parameters,
 * return types, and usage information.
 */
export const operations = {
  recall: {
    name: 'recall',
    description: 'Recall memories matching a query',
    category: 'read',
    parameters: {
      query: { type: 'string', required: true, description: 'Search query string' },
      limit: { type: 'number', required: false, default: 10, description: 'Maximum results' },
      minConfidence: {
        type: 'number',
        required: false,
        default: 0.5,
        description: 'Minimum confidence threshold (0-1)',
      },
      timeRange: {
        type: 'object',
        required: false,
        description: 'Time range filter {start, end}',
      },
      tags: { type: 'array', required: false, description: 'Tag filters' },
    },
    returnType: 'Memory[]',
  },

  getRecent: {
    name: 'getRecent',
    description: 'Get most recent memories',
    category: 'read',
    parameters: {
      limit: { type: 'number', required: false, default: 5, description: 'Number to retrieve' },
    },
    returnType: 'Memory[]',
  },

  remember: {
    name: 'remember',
    description: 'Store a new memory',
    category: 'write',
    parameters: {
      content: { type: 'string', required: true, description: 'Memory content' },
      context: { type: 'object', required: false, description: 'Additional context' },
      tags: { type: 'array', required: false, description: 'Tags for categorization' },
      source: { type: 'string', required: false, default: 'agent', description: 'Memory source' },
      expiresAt: { type: 'number', required: false, description: 'Expiration timestamp' },
    },
    returnType: 'string',
  },

  forget: {
    name: 'forget',
    description: 'Delete memories',
    category: 'write',
    parameters: {
      ids: { type: 'array', required: true, description: 'Memory IDs to delete' },
    },
    returnType: 'number',
  },

  bulkRemember: {
    name: 'bulkRemember',
    description: 'Store multiple memories',
    category: 'write',
    parameters: {
      memories: {
        type: 'array',
        required: true,
        description: 'Array of memory inputs',
      },
      parallel: {
        type: 'boolean',
        required: false,
        default: true,
        description: 'Execute in parallel',
      },
    },
    returnType: 'string[]',
  },

  queryTemporal: {
    name: 'queryTemporal',
    description: 'Query memories by time range',
    category: 'read',
    parameters: {
      startTime: {
        type: 'number',
        required: true,
        description: 'Start timestamp (ms)',
      },
      endTime: { type: 'number', required: true, description: 'End timestamp (ms)' },
      limit: { type: 'number', required: false, description: 'Maximum results' },
      sortBy: {
        type: 'string',
        required: false,
        default: 'timestamp',
        description: 'Sort by timestamp or confidence',
      },
    },
    returnType: 'Memory[]',
  },

  listEvents: {
    name: 'listEvents',
    description: 'List all memories with pagination',
    category: 'read',
    parameters: {
      limit: { type: 'number', required: false, default: 20, description: 'Items per page' },
      offset: { type: 'number', required: false, default: 0, description: 'Skip count' },
      sortBy: { type: 'string', required: false, default: 'timestamp', description: 'Sort field' },
      order: { type: 'string', required: false, default: 'desc', description: 'Sort direction' },
    },
    returnType: 'Memory[]',
  },
} as const;

/**
 * Get operation metadata
 *
 * Returns metadata for all operations in this layer.
 *
 * @returns Array of operation metadata
 */
export function getOperations() {
  return Object.values(operations);
}

/**
 * Get operation by name
 *
 * @param name - Operation name
 * @returns Operation metadata or undefined
 */
export function getOperation(name: string) {
  return operations[name as keyof typeof operations];
}

/**
 * Check if operation exists
 *
 * @param name - Operation name
 * @returns True if operation exists
 */
export function hasOperation(name: string): boolean {
  return name in operations;
}

/**
 * Get all read operations
 *
 * @returns Array of read operations
 */
export function getReadOperations() {
  return getOperations().filter((op) => op.category === 'read');
}

/**
 * Get all write operations
 *
 * @returns Array of write operations
 */
export function getWriteOperations() {
  return getOperations().filter((op) => op.category === 'write');
}
