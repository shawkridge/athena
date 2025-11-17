/**
 * Run consolidation to extract patterns
 */

import { athenaAPI } from '../../lib/athena-api-client.ts';

export async function consolidate() {
  try {
    const response = await athenaAPI.consolidate();

    if (!response.success) {
      return {
        success: false,
        message: 'Consolidation failed',
      };
    }

    return {
      success: true,
      message: 'Consolidation triggered successfully',
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      message: `Error: ${String(error).substring(0, 100)}`,
    };
  }
}
