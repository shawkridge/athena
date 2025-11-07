/**
 * Semantic Memory: Search Operations
 *
 * Query semantic memory using vector search, BM25, or hybrid approaches
 */

import type { SearchOptions, SearchResult, HybridSearchResults } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Search semantic memory with smart method selection
 *
 * Automatically selects best search method (vector, BM25, or hybrid)
 * based on query characteristics and available data.
 *
 * @param query - Search query string
 * @param limit - Maximum results (default: 10)
 * @param minConfidence - Minimum confidence threshold (0-1)
 * @returns Array of search results ranked by relevance
 *
 * @example
 * const results = await search('database performance optimization');
 * console.log(`Found ${results.length} matching memories`);
 */
export async function search(
  query: string,
  limit: number = 10,
  minConfidence: number = 0.5
): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/search', {
    query,
    limit,
    minConfidence,
  })) as HybridSearchResults;

  return results.results;
}

/**
 * Vector-based semantic search
 *
 * Uses embedding vectors for semantic similarity matching.
 * Best for fuzzy/conceptual queries.
 *
 * @param query - Natural language query
 * @param limit - Maximum results
 * @param minConfidence - Minimum confidence
 * @returns Semantically similar memories
 *
 * @example
 * const results = await semanticSearch('How do we handle authentication?');
 */
export async function semanticSearch(
  query: string,
  limit: number = 10,
  minConfidence: number = 0.5
): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/search', {
    query,
    limit,
    minConfidence,
    useVector: true,
    useBM25: false,
  })) as HybridSearchResults;

  return results.results;
}

/**
 * BM25-based keyword search
 *
 * Uses BM25 algorithm for exact keyword matching.
 * Best for precise queries with specific terms.
 *
 * @param query - Keyword query (supports: AND, OR, NOT, exact phrases with quotes)
 * @param limit - Maximum results
 * @returns Exact keyword matches
 *
 * @example
 * const results = await keywordSearch('authentication "API key" OR "bearer token"');
 */
export async function keywordSearch(query: string, limit: number = 10): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/search', {
    query,
    limit,
    useVector: false,
    useBM25: true,
  })) as HybridSearchResults;

  return results.results;
}

/**
 * Hybrid search combining vector and keyword
 *
 * Uses both vector similarity and keyword matching for best of both.
 *
 * @param query - Search query
 * @param limit - Maximum results
 * @param vectorWeight - Weight for vector search (0-1, default: 0.5)
 * @returns Combined ranked results
 *
 * @example
 * const results = await hybridSearch('database indexes', 20, 0.6);
 */
export async function hybridSearch(
  query: string,
  limit: number = 10,
  vectorWeight: number = 0.5
): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/search', {
    query,
    limit,
    useVector: true,
    useBM25: true,
    vectorWeight,
  })) as HybridSearchResults;

  return results.results;
}

/**
 * Search by topic
 *
 * Find memories associated with specific topics.
 *
 * @param topics - Topics to search for
 * @param limit - Maximum results
 * @returns Memories with matching topics
 *
 * @example
 * const results = await searchByTopic(['security', 'encryption']);
 */
export async function searchByTopic(topics: string[], limit: number = 20): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/search', {
    query: `topics:(${topics.join(' OR ')})`,
    limit,
    useBM25: true,
  })) as HybridSearchResults;

  return results.results;
}

/**
 * Related memories search
 *
 * Find memories similar to a given memory ID.
 *
 * @param memoryId - Reference memory ID
 * @param limit - Maximum results
 * @returns Similar memories
 *
 * @example
 * const similar = await searchRelated('memory_123', 10);
 */
export async function searchRelated(memoryId: string, limit: number = 10): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/searchRelated', {
    memoryId,
    limit,
  })) as HybridSearchResults;

  return results.results;
}

/**
 * Full-text search with advanced features
 *
 * Supports Boolean operators and phrase search.
 *
 * @param query - Query with operators: AND, OR, NOT, "exact phrase", -exclude
 * @param limit - Maximum results
 * @returns Matching memories
 *
 * @example
 * const results = await fullTextSearch('("machine learning" OR "deep learning") AND -deprecated');
 */
export async function fullTextSearch(query: string, limit: number = 20): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/search', {
    query,
    limit,
    useBM25: true,
  })) as HybridSearchResults;

  return results.results;
}

/**
 * Search with result details
 *
 * Returns full hybrid search results with metrics.
 *
 * @param options - Full search options
 * @returns Detailed search results with timing
 */
export async function searchWithMetrics(options: SearchOptions): Promise<HybridSearchResults> {
  return (await callMCPTool('semantic/search', {
    query: options.query,
    limit: options.limit ?? 10,
    minConfidence: options.minConfidence ?? 0.5,
    useVector: options.useVector ?? true,
    useBM25: options.useBM25 ?? true,
    topics: options.topics,
  })) as HybridSearchResults;
}

/**
 * Instant search with autocomplete
 *
 * Fast search for real-time UI autocomplete.
 *
 * @param prefix - Query prefix
 * @param limit - Maximum results (typically 5-10)
 * @returns Quick search results
 */
export async function instantSearch(prefix: string, limit: number = 5): Promise<SearchResult[]> {
  const results = (await callMCPTool('semantic/instantSearch', {
    prefix,
    limit,
  })) as HybridSearchResults;

  return results.results;
}
