/**
 * Episodic Memory: Forget Operation
 *
 * Delete or remove memories from episodic memory layer
 */

import type { ForgetInput, ForgetResult } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Forget (delete) memories by IDs
 *
 * Permanently removes specific memories from episodic storage.
 *
 * @param ids - Array of memory IDs to delete
 * @returns Number of deleted memories
 *
 * @example
 * const deleted = await forget(['mem_123', 'mem_456']);
 * console.log(`Deleted ${deleted} memories`);
 */
export async function forget(ids: string[]): Promise<number> {
  const result = (await callMCPTool('episodic/forget', {
    ids,
  })) as ForgetResult;

  return result.deleted;
}

/**
 * Forget memories older than a timestamp
 *
 * Removes all memories created before the specified time.
 * Useful for cleanup and maintaining memory recency.
 *
 * @param olderThan - Timestamp (milliseconds since epoch)
 * @param limit - Optional limit on number of deletions per call
 * @returns Number of deleted memories
 *
 * @example
 * // Delete memories older than 1 year
 * const oneYearAgo = Date.now() - 365 * 24 * 60 * 60 * 1000;
 * const deleted = await forgetOlderThan(oneYearAgo);
 * console.log(`Cleaned up ${deleted} old memories`);
 */
export async function forgetOlderThan(olderThan: number, limit?: number): Promise<number> {
  const result = (await callMCPTool('episodic/forget', {
    olderThan,
    limit,
  })) as ForgetResult;

  return result.deleted;
}

/**
 * Forget memories with specific tags
 *
 * Removes all memories that have ALL specified tags.
 *
 * @param tags - Tags to match (memory must have all)
 * @param limit - Optional limit on number of deletions
 * @returns Number of deleted memories
 *
 * @example
 * // Remove all test/temporary memories
 * const deleted = await forgetWithTags(['test', 'temporary']);
 * console.log(`Removed ${deleted} test memories`);
 */
export async function forgetWithTags(tags: string[], limit?: number): Promise<number> {
  const result = (await callMCPTool('episodic/forget', {
    withTags: tags,
    limit,
  })) as ForgetResult;

  return result.deleted;
}

/**
 * Forget (delete) memories with full options
 *
 * Provides access to all forget parameters as an options object.
 *
 * @param options - Forget options
 * @returns Number of deleted memories
 */
export async function forgetWithOptions(options: ForgetInput): Promise<number> {
  const result = (await callMCPTool('episodic/forget', {
    ids: options.ids,
    olderThan: options.olderThan,
    withTags: options.withTags,
    limit: options.limit,
  })) as ForgetResult;

  return result.deleted;
}

/**
 * Clear all memories matching a pattern
 *
 * Batch delete memories without requiring individual IDs.
 *
 * @param pattern - Pattern to match (tag, time range, or source)
 * @param type - Type of pattern ('tag', 'timeRange', 'source')
 * @param value - Value to match against
 * @returns Number of deleted memories
 */
export async function forgetByPattern(
  pattern: string,
  type: 'tag' | 'timeRange' | 'source' = 'tag',
  value?: unknown
): Promise<number> {
  const result = (await callMCPTool('episodic/forget', {
    pattern,
    patternType: type,
    value,
  })) as ForgetResult;

  return result.deleted;
}

/**
 * Forget memories with low confidence
 *
 * Removes memories below a confidence threshold.
 * Useful for cleaning up uncertain or unreliable memories.
 *
 * @param threshold - Confidence threshold (0-1)
 * @param maxAge - Optional maximum age (won't delete recent memories)
 * @returns Number of deleted memories
 *
 * @example
 * // Clean up memories with <30% confidence
 * const deleted = await forgetLowConfidence(0.3);
 * console.log(`Removed ${deleted} low-confidence memories`);
 */
export async function forgetLowConfidence(threshold: number, maxAge?: number): Promise<number> {
  const result = (await callMCPTool('episodic/forget', {
    lowConfidenceThreshold: threshold,
    maxAge,
  })) as ForgetResult;

  return result.deleted;
}
