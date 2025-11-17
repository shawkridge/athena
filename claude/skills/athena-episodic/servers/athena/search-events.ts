import { athenaAPI } from '../../lib/athena-api-client.ts';

export async function searchEvents(query: string, limit = 10) {
  try {
    const response = await athenaAPI.searchEpisodicEvents(query, limit);
    if (!response.success) return { found: 0, summary: 'Search failed', results: [] };
    const data = response.data || [];
    return { found: data.length, summary: `Found ${data.length} matching events`, results: data.slice(0, 5) };
  } catch (error) {
    return { found: 0, summary: `Error: ${String(error)}`, results: [] };
  }
}
