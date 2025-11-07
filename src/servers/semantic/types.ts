/**
 * Semantic Memory Layer Types
 *
 * Interfaces for semantic memory operations (knowledge representation)
 */

/**
 * Semantic memory record
 */
export interface SemanticMemory {
  id: string;
  content: string;
  embedding?: number[]; // Vector embedding
  topics: string[];
  relatedMemories: string[];
  confidence: number;
  lastUpdated: number;
  accessCount: number;
  usefulness: number; // 0-1
}

/**
 * Search options for semantic search
 */
export interface SearchOptions {
  query: string;
  limit?: number;
  minConfidence?: number;
  useVector?: boolean;
  useBM25?: boolean;
  topics?: string[];
}

/**
 * Search result with ranking
 */
export interface SearchResult {
  id: string;
  content: string;
  score: number; // 0-1
  method: 'vector' | 'bm25' | 'hybrid';
  topics: string[];
  confidence: number;
}

/**
 * Hybrid search results
 */
export interface HybridSearchResults {
  results: SearchResult[];
  totalMatches: number;
  executionTimeMs: number;
  vectorScore: number;
  bm25Score: number;
}

/**
 * Memory to store
 */
export interface StoreInput {
  content: string;
  topics?: string[];
  embedding?: number[];
  confidence?: number;
  metadata?: Record<string, unknown>;
}

/**
 * Store operation result
 */
export interface StoreResult {
  id: string;
  stored: boolean;
  timestamp: number;
}

/**
 * Update operation input
 */
export interface UpdateInput {
  id: string;
  content?: string;
  topics?: string[];
  confidence?: number;
  embedding?: number[];
}

/**
 * Delete operation input
 */
export interface DeleteInput {
  id?: string;
  ids?: string[];
  olderThan?: number;
  withTopics?: string[];
}

/**
 * Delete operation result
 */
export interface DeleteResult {
  deleted: number;
  message: string;
}

/**
 * List operation input
 */
export interface ListInput {
  limit?: number;
  offset?: number;
  sortBy?: 'lastUpdated' | 'confidence' | 'usefulness' | 'accessCount';
  order?: 'asc' | 'desc';
  topics?: string[];
}

/**
 * Topic analysis result
 */
export interface TopicAnalysis {
  topics: string[];
  frequency: Record<string, number>;
  relationships: Record<string, string[]>;
  dominantTopics: string[];
}

/**
 * Memory statistics
 */
export interface MemoryStats {
  totalMemories: number;
  averageConfidence: number;
  averageUsefulness: number;
  topTopics: string[];
  lastAccess: number;
}
