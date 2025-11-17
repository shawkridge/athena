/**
 * Remember a new fact or learning
 */

import { athenaAPI } from '../../lib/athena-api-client.ts';

export async function remember(content: string, tags: string[] = []) {
  try {
    // For now, we just log - actual remember would POST to API
    console.log(`Remembering: ${content.substring(0, 100)}`);
    console.log(`Tags: ${tags.join(', ') || 'none'}`);

    return {
      success: true,
      message: `Remembered: "${content.substring(0, 60)}..."`,
      tags: tags,
    };
  } catch (error) {
    return {
      success: false,
      message: `Error: ${String(error).substring(0, 100)}`,
    };
  }
}
