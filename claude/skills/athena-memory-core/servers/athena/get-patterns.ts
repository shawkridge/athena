/**
 * Get learned patterns
 */

import { athenaAPI } from '../../lib/athena-api-client.ts';
import { formatPatterns } from '../../lib/formatters.ts';

export async function getPatterns(limit = 10) {
  try {
    const response = await athenaAPI.getPatterns(limit);

    if (!response.success || !response.data) {
      return {
        found: 0,
        summary: 'No patterns found yet',
        patterns: [],
      };
    }

    const patterns = response.data || [];
    const formatted = formatPatterns(patterns, 5);

    return {
      found: patterns.length,
      summary: formatted.summary,
      patterns: formatted.details,
    };
  } catch (error) {
    return {
      found: 0,
      summary: `Error: ${String(error).substring(0, 100)}`,
      patterns: [],
    };
  }
}
