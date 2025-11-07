/**
 * Semantic Memory: Utility Operations
 *
 * List, retrieve, analyze, and get statistics on semantic memories
 */

import type { SemanticMemory, TopicAnalysis, MemoryStats, ListInput } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Get a semantic memory by ID
 *
 * @param id - Memory ID
 * @returns Memory object or null
 *
 * @example
 * const memory = await get('mem_123');
 */
export async function get(id: string): Promise<SemanticMemory | null> {
  return (await callMCPTool('semantic/get', {
    id,
  })) as SemanticMemory | null;
}

/**
 * List semantic memories with pagination
 *
 * @param limit - Number of results
 * @param offset - Offset from start
 * @param sortBy - Sort field
 * @param order - Sort direction
 * @returns Array of memories
 *
 * @example
 * const page1 = await list(20, 0);
 */
export async function list(
  limit: number = 20,
  offset: number = 0,
  sortBy: 'lastUpdated' | 'confidence' | 'usefulness' | 'accessCount' = 'lastUpdated',
  order: 'asc' | 'desc' = 'desc'
): Promise<SemanticMemory[]> {
  return (await callMCPTool('semantic/list', {
    limit,
    offset,
    sortBy,
    order,
  })) as SemanticMemory[];
}

/**
 * List all memories
 *
 * @param batchSize - Batch size for retrieval
 * @returns All memories
 */
export async function listAll(batchSize: number = 500): Promise<SemanticMemory[]> {
  const allMemories: SemanticMemory[] = [];
  let offset = 0;

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const batch = await list(batchSize, offset);
    if (batch.length === 0) break;
    allMemories.push(...batch);
    offset += batch.length;
  }

  return allMemories;
}

/**
 * Get most confident memories
 *
 * @param limit - Maximum results
 * @returns High-confidence memories
 */
export async function getMostConfident(limit: number = 20): Promise<SemanticMemory[]> {
  return await list(limit, 0, 'confidence', 'desc');
}

/**
 * Get most useful memories
 *
 * @param limit - Maximum results
 * @returns Most useful memories
 */
export async function getMostUseful(limit: number = 20): Promise<SemanticMemory[]> {
  return await list(limit, 0, 'usefulness', 'desc');
}

/**
 * Get most recently updated
 *
 * @param limit - Maximum results
 * @returns Recently updated memories
 */
export async function getRecent(limit: number = 20): Promise<SemanticMemory[]> {
  return await list(limit, 0, 'lastUpdated', 'desc');
}

/**
 * Get memories by topic
 *
 * @param topics - Topics to filter
 * @param limit - Maximum results
 * @returns Memories with matching topics
 */
export async function getByTopics(topics: string[], limit: number = 20): Promise<SemanticMemory[]> {
  return (await callMCPTool('semantic/listByTopics', {
    topics,
    limit,
  })) as SemanticMemory[];
}

/**
 * Count total memories
 *
 * @returns Total count
 */
export async function count(): Promise<number> {
  const result = (await callMCPTool('semantic/count', {})) as { total: number };
  return result.total;
}

/**
 * Analyze topic distribution
 *
 * @returns Topic analysis
 *
 * @example
 * const analysis = await analyzeTopics();
 * console.log('Dominant topics:', analysis.dominantTopics);
 */
export async function analyzeTopics(): Promise<TopicAnalysis> {
  return (await callMCPTool('semantic/analyzeTopics', {})) as TopicAnalysis;
}

/**
 * Get memory statistics
 *
 * @returns Statistics about semantic memory
 *
 * @example
 * const stats = await getStats();
 * console.log(`Total memories: ${stats.totalMemories}`);
 */
export async function getStats(): Promise<MemoryStats> {
  return (await callMCPTool('semantic/stats', {})) as MemoryStats;
}

/**
 * Record memory access (for usage tracking)
 *
 * @param id - Memory ID
 * @param incrementBy - Amount to increment (default: 1)
 */
export async function recordAccess(id: string, incrementBy: number = 1): Promise<void> {
  await callMCPTool('semantic/recordAccess', {
    id,
    incrementBy,
  });
}

/**
 * Update memory usefulness score
 *
 * @param id - Memory ID
 * @param usefulness - Usefulness score (0-1)
 */
export async function setUsefulness(id: string, usefulness: number): Promise<void> {
  await callMCPTool('semantic/setUsefulness', {
    id,
    usefulness: Math.max(0, Math.min(1, usefulness)), // Clamp to 0-1
  });
}

/**
 * Get related memories
 *
 * @param id - Reference memory ID
 * @param limit - Maximum results
 * @returns Related memories
 */
export async function getRelated(id: string, limit: number = 10): Promise<SemanticMemory[]> {
  return (await callMCPTool('semantic/getRelated', {
    id,
    limit,
  })) as SemanticMemory[];
}

/**
 * Export all memories
 *
 * @returns All memories for backup
 */
export async function exportAll(): Promise<SemanticMemory[]> {
  return await listAll(1000);
}

/**
 * Create a memory index for faster searches
 *
 * @param topics - Topics to index (optional, default: all)
 */
export async function indexTopics(topics?: string[]): Promise<void> {
  await callMCPTool('semantic/indexTopics', {
    topics,
  });
}

/**
 * Rebuild all indexes
 *
 * Useful for performance optimization after bulk operations.
 */
export async function rebuildIndexes(): Promise<void> {
  await callMCPTool('semantic/rebuildIndexes', {});
}
