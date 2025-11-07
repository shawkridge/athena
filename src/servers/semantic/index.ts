/**
 * Semantic Memory Operations
 *
 * Functions for storing, searching, and managing semantic knowledge.
 * Semantic memory is for general knowledge and facts, not time-bound events.
 *
 * @packageDocumentation
 */

// Re-export search operations
export {
  search,
  semanticSearch,
  keywordSearch,
  hybridSearch,
  searchByTopic,
  searchRelated,
  fullTextSearch,
  searchWithMetrics,
  instantSearch,
} from './search';

// Re-export store operations
export {
  store,
  storeWithOptions,
  storeFact,
  storePrinciple,
  storeConcept,
  update,
  updateWithOptions,
  delete_memory,
  deleteMultiple,
  deleteByTopics,
  deleteOlderThan,
  deleteWithOptions,
  purgeLowConfidence,
  consolidate,
} from './store';

// Re-export utility operations
export {
  get,
  list,
  listAll,
  getMostConfident,
  getMostUseful,
  getRecent,
  getByTopics,
  count,
  analyzeTopics,
  getStats,
  recordAccess,
  setUsefulness,
  getRelated,
  exportAll,
  indexTopics,
  rebuildIndexes,
} from './utilities';

// Re-export types
export type {
  SemanticMemory,
  SearchOptions,
  SearchResult,
  HybridSearchResults,
  StoreInput,
  StoreResult,
  UpdateInput,
  DeleteInput,
  DeleteResult,
  ListInput,
  TopicAnalysis,
  MemoryStats,
} from './types';

/**
 * Semantic memory operations metadata
 */
export const operations = {
  search: {
    name: 'search',
    description: 'Search semantic memories',
    category: 'read',
    parameters: {
      query: { type: 'string', required: true, description: 'Search query' },
      limit: { type: 'number', required: false, default: 10, description: 'Max results' },
      minConfidence: {
        type: 'number',
        required: false,
        default: 0.5,
        description: 'Confidence threshold',
      },
    },
    returnType: 'SearchResult[]',
  },

  semanticSearch: {
    name: 'semanticSearch',
    description: 'Vector-based semantic search',
    category: 'read',
    parameters: {
      query: { type: 'string', required: true },
      limit: { type: 'number', required: false, default: 10 },
    },
    returnType: 'SearchResult[]',
  },

  keywordSearch: {
    name: 'keywordSearch',
    description: 'Keyword-based search (BM25)',
    category: 'read',
    parameters: {
      query: { type: 'string', required: true },
      limit: { type: 'number', required: false, default: 10 },
    },
    returnType: 'SearchResult[]',
  },

  store: {
    name: 'store',
    description: 'Store semantic memory',
    category: 'write',
    parameters: {
      content: { type: 'string', required: true, description: 'Memory content' },
      topics: { type: 'array', required: false, description: 'Topics' },
      confidence: { type: 'number', required: false, default: 0.8, description: 'Confidence' },
    },
    returnType: 'string',
  },

  update: {
    name: 'update',
    description: 'Update semantic memory',
    category: 'write',
    parameters: {
      id: { type: 'string', required: true },
      content: { type: 'string', required: false },
      topics: { type: 'array', required: false },
      confidence: { type: 'number', required: false },
    },
    returnType: 'boolean',
  },

  delete_memory: {
    name: 'delete_memory',
    description: 'Delete semantic memory',
    category: 'write',
    parameters: {
      id: { type: 'string', required: true },
    },
    returnType: 'number',
  },

  list: {
    name: 'list',
    description: 'List semantic memories',
    category: 'read',
    parameters: {
      limit: { type: 'number', required: false, default: 20 },
      offset: { type: 'number', required: false, default: 0 },
      sortBy: { type: 'string', required: false, default: 'lastUpdated' },
      order: { type: 'string', required: false, default: 'desc' },
    },
    returnType: 'SemanticMemory[]',
  },

  analyzeTopics: {
    name: 'analyzeTopics',
    description: 'Analyze topic distribution',
    category: 'read',
    returnType: 'TopicAnalysis',
  },

  getStats: {
    name: 'getStats',
    description: 'Get semantic memory statistics',
    category: 'read',
    returnType: 'MemoryStats',
  },
} as const;

/**
 * Get operation metadata
 */
export function getOperations() {
  return Object.values(operations);
}

/**
 * Get operation by name
 */
export function getOperation(name: string) {
  return operations[name as keyof typeof operations];
}

/**
 * Check if operation exists
 */
export function hasOperation(name: string): boolean {
  return name in operations;
}

/**
 * Get all read operations
 */
export function getReadOperations() {
  return getOperations().filter((op) => op.category === 'read');
}

/**
 * Get all write operations
 */
export function getWriteOperations() {
  return getOperations().filter((op) => op.category === 'write');
}
