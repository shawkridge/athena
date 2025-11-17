import { athenaAPI } from '../../lib/athena-api-client.ts';
import { formatQualityScores } from '../../lib/formatters.ts';

export async function getQualityScores(layer?: string) {
  try {
    const response = await athenaAPI.getQualityScores({ layer });
    if (!response.success || !response.data) {
      return { summary: 'No quality data available', scores: {} };
    }
    const formatted = formatQualityScores(response.data);
    return { summary: formatted.summary, scores: formatted.details };
  } catch (error) {
    return { summary: `Error: ${String(error)}`, scores: {} };
  }
}
