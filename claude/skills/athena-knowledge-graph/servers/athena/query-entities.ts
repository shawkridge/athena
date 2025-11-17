import { athenaAPI } from '../../lib/athena-api-client.ts';
import { formatEntities } from '../../lib/formatters.ts';

export async function queryEntities(search?: string, limit = 20) {
  try {
    const response = await athenaAPI.queryEntities({ search, limit });
    if (!response.success || !response.data) {
      return { found: 0, summary: 'No entities found', entities: [] };
    }
    const formatted = formatEntities(response.data, 5);
    return { found: response.data.length, summary: formatted.summary, entities: formatted.details };
  } catch (error) {
    return { found: 0, summary: `Error: ${String(error)}`, entities: [] };
  }
}
