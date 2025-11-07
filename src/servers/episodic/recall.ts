/**
 * Episodic Memory: Recall Operation
 *
 * Retrieve memories matching a query from episodic memory layer
 */

import type { Memory, RecallOptions, RecallResult } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Recall memories matching a query
 *
 * Searches the episodic memory layer for events matching the provided query.
 * Returns memories with confidence scores and related context.
 *
 * @param query - Search query string (supports boolean operators: AND, OR, NOT)
 * @param limit - Maximum results to return (default: 10)
 * @param minConfidence - Minimum confidence threshold (0-1, default: 0.5)
 * @param timeRange - Optional time range filter {start: timestamp, end: timestamp}
 * @param tags - Optional tag filters
 * @returns Matching memories with scores
 *
 * @example
 * // Simple recall
 * const memories = await recall('important meetings', 5);
 * console.log(memories);
 *
 * @example
 * // Advanced recall with filters
 * const results = await recall('decision AND budget', 10, 0.7, {
 *   start: Date.now() - 7 * 24 * 60 * 60 * 1000, // Last 7 days
 *   end: Date.now()
 * }, ['work', 'finance']);
 * console.log(results);
 */
export async function recall(
  query: string,
  limit: number = 10,
  minConfidence: number = 0.5,
  timeRange?: { start: number; end: number },
  tags?: string[]
): Promise<Memory[]> {
  const result = (await callMCPTool('episodic/recall', {
    query,
    limit,
    minConfidence,
    timeRange,
    tags,
  })) as RecallResult;

  return result.memories;
}

/**
 * Get recent memories (simplified version for quick access)
 *
 * Retrieves the most recent memories without complex querying.
 * Useful for quick context gathering.
 *
 * @param limit - Number of recent memories to retrieve (default: 5)
 * @returns Recent memories ordered by timestamp (newest first)
 *
 * @example
 * const recentMemories = await getRecent(10);
 * console.log('Last 10 memories:', recentMemories);
 */
export async function getRecent(limit: number = 5): Promise<Memory[]> {
  const result = (await callMCPTool('episodic/recall', {
    query: '*', // Special: get recent
    limit,
    sort: 'timestamp',
    order: 'desc',
  })) as RecallResult;

  return result.memories;
}

/**
 * Advanced recall with full options
 *
 * Provides detailed recall results including metadata and execution metrics.
 *
 * @param options - Full recall options
 * @returns Full recall result with metadata
 */
export async function recallWithMetrics(options: RecallOptions): Promise<RecallResult> {
  return (await callMCPTool('episodic/recall', {
    query: options.query,
    limit: options.limit ?? 10,
    minConfidence: options.minConfidence ?? 0.5,
    timeRange: options.timeRange,
    tags: options.tags,
  })) as RecallResult;
}

/**
 * Search for memories by tags
 *
 * Find all memories associated with specific tags.
 *
 * @param tags - Array of tags to search for
 * @param limit - Maximum results (default: 20)
 * @returns Memories matching the tags
 */
export async function recallByTags(tags: string[], limit: number = 20): Promise<Memory[]> {
  const result = (await callMCPTool('episodic/recall', {
    query: `tags:(${tags.join(' OR ')})`,
    limit,
  })) as RecallResult;

  return result.memories;
}
