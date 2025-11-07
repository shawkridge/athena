/**
 * Episodic Memory: Bulk Remember Operation
 *
 * Store multiple memories efficiently in a single operation
 */

import type { RememberInput, BulkRememberInput, BulkRememberResult } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Store multiple memories in bulk
 *
 * Efficiently stores multiple memories in a single operation.
 * Can execute serially or in parallel depending on options.
 *
 * @param memories - Array of memory inputs
 * @param parallel - Execute in parallel (default: true)
 * @returns Result with count and IDs of stored memories
 *
 * @example
 * const result = await bulkRemember([
 *   { content: 'First event', tags: ['meeting'] },
 *   { content: 'Second event', tags: ['decision'] },
 *   { content: 'Third event', tags: ['learning'] }
 * ]);
 * console.log(`Stored ${result.stored} memories`);
 */
export async function bulkRemember(
  memories: RememberInput[],
  parallel: boolean = true
): Promise<string[]> {
  const result = (await callMCPTool('episodic/bulkRemember', {
    memories,
    parallel,
  })) as BulkRememberResult;

  return result.ids;
}

/**
 * Store memories from a session or conversation
 *
 * Batch-stores multiple related memories from a conversation or session.
 * Automatically adds session context and timestamps.
 *
 * @param sessionId - Session identifier
 * @param messages - Messages/events from session
 * @param sessionContext - Additional context about the session
 * @returns Memory IDs
 *
 * @example
 * const ids = await bulkRememberSession('session_123', [
 *   'User asked about deadline',
 *   'Provided project timeline',
 *   'Discussed resource constraints'
 * ], {
 *   duration: 3600,
 *   participants: ['user', 'agent']
 * });
 */
export async function bulkRememberSession(
  sessionId: string,
  messages: string[],
  sessionContext?: Record<string, unknown>
): Promise<string[]> {
  const memories = messages.map((msg) => ({
    content: msg,
    context: {
      sessionId,
      ...sessionContext,
    },
    tags: ['session', sessionId],
    source: 'session',
  }));

  return await bulkRemember(memories, true);
}

/**
 * Store memories from a list with batch grouping
 *
 * Stores memories with configurable batch size for large datasets.
 *
 * @param memories - Array of memories to store
 * @param batchSize - Number of memories per batch (default: 100)
 * @returns All stored memory IDs
 */
export async function bulkRememberBatched(
  memories: RememberInput[],
  batchSize: number = 100
): Promise<string[]> {
  const allIds: string[] = [];

  for (let i = 0; i < memories.length; i += batchSize) {
    const batch = memories.slice(i, i + batchSize);
    const ids = await bulkRemember(batch, true);
    allIds.push(...ids);
  }

  return allIds;
}

/**
 * Store memories with transaction semantics
 *
 * All memories are stored together or none at all (atomic operation).
 *
 * @param memories - Array of memories
 * @returns Memory IDs if successful
 * @throws Error if any memory fails validation
 */
export async function bulkRememberAtomic(memories: RememberInput[]): Promise<string[]> {
  const result = (await callMCPTool('episodic/bulkRemember', {
    memories,
    parallel: false, // Serial for atomic semantics
    atomic: true,
  })) as BulkRememberResult;

  if (result.failed > 0) {
    throw new Error(`Failed to store ${result.failed} memories atomically`);
  }

  return result.ids;
}

/**
 * Store memories with automatic deduplication
 *
 * Checks for similar/duplicate content before storing.
 *
 * @param memories - Memories to store
 * @param deduplicationThreshold - Similarity threshold (0-1)
 * @returns Stored memory IDs (duplicates skipped)
 */
export async function bulkRememberDedup(
  memories: RememberInput[],
  deduplicationThreshold: number = 0.9
): Promise<string[]> {
  const result = (await callMCPTool('episodic/bulkRemember', {
    memories,
    parallel: true,
    deduplication: true,
    deduplicationThreshold,
  })) as BulkRememberResult;

  return result.ids;
}
