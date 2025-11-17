import { athenaAPI } from '../../lib/athena-api-client.ts';
import { formatPatterns } from '../../lib/formatters.ts';

export async function extractPatterns(limit = 10) {
  try {
    const response = await athenaAPI.getPatterns(limit);
    if (!response.success || !response.data) {
      return { found: 0, summary: 'No patterns extracted', patterns: [] };
    }
    const formatted = formatPatterns(response.data, 5);
    return { found: response.data.length, summary: formatted.summary, patterns: formatted.details };
  } catch (error) {
    return { found: 0, summary: `Error: ${String(error)}`, patterns: [] };
  }
}
