import { athenaAPI } from '../../lib/athena-api-client.ts';
import { formatTasks } from '../../lib/formatters.ts';

export async function listTasks(status?: string, limit = 20) {
  try {
    const response = await athenaAPI.getGoals({ status, limit });
    if (!response.success || !response.data) {
      return { found: 0, summary: 'No tasks found', tasks: [] };
    }
    const formatted = formatTasks(response.data, 10);
    return { found: response.data.length, summary: formatted.summary, tasks: formatted.details };
  } catch (error) {
    return { found: 0, summary: `Error: ${String(error)}`, tasks: [] };
  }
}
