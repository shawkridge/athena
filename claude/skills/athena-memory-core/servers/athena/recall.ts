/**
 * Recall memories by query
 *
 * Search across all memory layers for matching memories.
 * Filters locally, returns summary only.
 */

import { athenaAPI } from '../../lib/athena-api-client.ts';
import { extractKeyInsights } from '../../lib/formatters.ts';

export interface RecallResult {
  query: string;
  found: number;
  summary: string;
  memories: Array<{
    content: string;
    relevance: string;
    source: string;
  }>;
}

/**
 * Recall memories by query
 */
export async function recall(
  query: string,
  limit = 10
): Promise<RecallResult> {
  try {
    // Call real Athena API
    const response = await athenaAPI.recall(query, limit);

    if (!response.success || !response.data) {
      return {
        query,
        found: 0,
        summary: 'No memories found',
        memories: [],
      };
    }

    const memories = response.data || [];
    const filtered = memories.slice(0, 5); // Keep only top 5 locally

    // Format results
    const formatted = filtered.map((m: any) => ({
      content: m.content?.substring(0, 100) || '',
      relevance: Math.round((m.relevance_score || 0.5) * 100) + '%',
      source: m.source || 'memory',
    }));

    const insights = extractKeyInsights(formatted, 3);

    return {
      query,
      found: memories.length,
      summary: `Found ${memories.length} memories. Top matches: ${insights.slice(1).join(', ')}`,
      memories: formatted,
    };
  } catch (error) {
    return {
      query,
      found: 0,
      summary: `Error recalling memories: ${String(error).substring(0, 100)}`,
      memories: [],
    };
  }
}
