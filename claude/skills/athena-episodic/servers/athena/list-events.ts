import { athenaAPI } from '../../lib/athena-api-client.ts';
import { formatEpisodicEvents } from '../../lib/formatters.ts';

export async function listEvents(limit = 50) {
  try {
    const response = await athenaAPI.getEpisodicEvents({ limit });
    if (!response.success || !response.data) {
      return { found: 0, summary: 'No events found', events: [] };
    }
    const formatted = formatEpisodicEvents(response.data, 10);
    return { found: response.data.length, summary: formatted.summary, events: formatted.details };
  } catch (error) {
    return { found: 0, summary: `Error: ${String(error)}`, events: [] };
  }
}
