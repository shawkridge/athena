import { athenaAPI } from '../../lib/athena-api-client.ts';

export async function semanticSearch(query: string, limit = 10) {
  try {
    const response = await athenaAPI.recall(query, limit);
    return response;
  } catch (error) {
    return { success: false, error: String(error) };
  }
}
