/**
 * Episodic Memory: List Events
 *
 * Browse and paginate through episodic memories
 */

import type { Memory, ListEventsInput } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * List all events with pagination
 *
 * Retrieves episodic memories with pagination support for browsing.
 *
 * @param limit - Number of events per page (default: 20)
 * @param offset - Number of events to skip (default: 0)
 * @param sortBy - Sort by 'timestamp' or 'confidence'
 * @param order - Sort order 'asc' or 'desc'
 * @returns Array of memories
 *
 * @example
 * // First page
 * const page1 = await listEvents(20, 0);
 *
 * // Second page
 * const page2 = await listEvents(20, 20);
 */
export async function listEvents(
  limit: number = 20,
  offset: number = 0,
  sortBy: 'timestamp' | 'confidence' = 'timestamp',
  order: 'asc' | 'desc' = 'desc'
): Promise<Memory[]> {
  return (await callMCPTool('episodic/listEvents', {
    limit,
    offset,
    sortBy,
    order,
  })) as Memory[];
}

/**
 * Get all memories (with streaming for large datasets)
 *
 * Retrieves all episodic memories, useful for analysis or export.
 *
 * @param batchSize - Number of events to fetch per batch
 * @returns All memories
 *
 * @example
 * const allMemories = await getAllEvents(500);
 * console.log(`Total memories: ${allMemories.length}`);
 */
export async function getAllEvents(batchSize: number = 500): Promise<Memory[]> {
  const allMemories: Memory[] = [];
  let offset = 0;

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const batch = await listEvents(batchSize, offset);
    if (batch.length === 0) break;
    allMemories.push(...batch);
    offset += batch.length;
  }

  return allMemories;
}

/**
 * Count total number of memories
 *
 * Returns the total count of episodic memories.
 *
 * @returns Total memory count
 *
 * @example
 * const count = await countEvents();
 * console.log(`Total memories: ${count}`);
 */
export async function countEvents(): Promise<number> {
  const result = (await callMCPTool('episodic/countEvents', {})) as {
    total: number;
  };

  return result.total;
}

/**
 * Browse memories by page
 *
 * Pagination helper for sequential browsing.
 *
 * @param pageNumber - Page number (1-indexed)
 * @param pageSize - Items per page
 * @returns Events on that page
 *
 * @example
 * const page3 = await getPage(3, 20);
 */
export async function getPage(pageNumber: number, pageSize: number = 20): Promise<Memory[]> {
  const offset = (pageNumber - 1) * pageSize;
  return await listEvents(pageSize, offset);
}

/**
 * Get most recent N events
 *
 * Retrieves the N most recent memories quickly.
 *
 * @param count - Number of recent events
 * @returns Recent events
 *
 * @example
 * const recent = await getRecent(10);
 */
export async function getRecent(count: number): Promise<Memory[]> {
  return await listEvents(count, 0, 'timestamp', 'desc');
}

/**
 * Get oldest N events
 *
 * Retrieves the N oldest memories (in forward chronological order).
 *
 * @param count - Number of oldest events
 * @returns Oldest events
 *
 * @example
 * const oldest = await getOldest(10);
 */
export async function getOldest(count: number): Promise<Memory[]> {
  return await listEvents(count, 0, 'timestamp', 'asc');
}

/**
 * Get highest confidence events
 *
 * Retrieves memories sorted by confidence score.
 *
 * @param limit - Maximum events
 * @returns High-confidence events
 *
 * @example
 * const trusted = await getMostConfident(20);
 */
export async function getMostConfident(limit: number): Promise<Memory[]> {
  return await listEvents(limit, 0, 'confidence', 'desc');
}

/**
 * Get lowest confidence events
 *
 * Useful for finding uncertain memories to review or remove.
 *
 * @param limit - Maximum events
 * @returns Low-confidence events
 */
export async function getLeastConfident(limit: number): Promise<Memory[]> {
  return await listEvents(limit, 0, 'confidence', 'asc');
}

/**
 * Search for events with pagination
 *
 * Combines search with pagination for large result sets.
 *
 * @param query - Search query
 * @param page - Page number (1-indexed)
 * @param pageSize - Items per page
 * @returns Matching memories
 */
export async function searchPage(
  query: string,
  page: number = 1,
  pageSize: number = 20
): Promise<Memory[]> {
  return (await callMCPTool('episodic/searchPage', {
    query,
    page,
    pageSize,
  })) as Memory[];
}

/**
 * Export all memories for backup or analysis
 *
 * Returns all memories in a standard format suitable for export.
 *
 * @returns Array of all memories
 */
export async function exportAll(): Promise<Memory[]> {
  return await getAllEvents(1000); // Use larger batch for export
}
