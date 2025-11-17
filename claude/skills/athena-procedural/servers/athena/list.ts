import { athenaAPI } from '../../lib/athena-api-client.ts';
import { formatProcedures } from '../../lib/formatters.ts';

export async function listProcedures(limit = 20) {
  try {
    const response = await athenaAPI.getProcedures({ limit });
    if (!response.success || !response.data) {
      return { found: 0, summary: 'No procedures found', procedures: [] };
    }
    const formatted = formatProcedures(response.data, 5);
    return { found: response.data.length, summary: formatted.summary, procedures: formatted.details };
  } catch (error) {
    return { found: 0, summary: `Error: ${String(error)}`, procedures: [] };
  }
}
