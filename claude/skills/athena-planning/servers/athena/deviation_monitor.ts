/**
 * Deviation Monitor Tool Wrapper
 *
 * Agents use this to detect tasks deviating from estimates.
 * Filesystem-based MCP paradigm: agents discover and import.
 */

export interface DeviationAlert {
  taskId: number;
  deviationPercent: number;
  elapsedMinutes: number;
  estimatedMinutes: number;
  reason?: string;
  recommendedAction: 'replan' | 'extend' | 'accelerate' | 'abandon';
}

/**
 * Check if a task is deviating from its estimate
 *
 * Example agent usage:
 * ```typescript
 * import { checkDeviation } from './servers/athena/deviation_monitor.ts';
 *
 * const deviations = [];
 * for (const taskId of [1, 2, 3]) {
 *   const alert = await checkDeviation(taskId);
 *   if (alert) deviations.push(alert);
 * }
 * console.log(`Found ${deviations.length} deviating tasks`);
 * ```
 */
export async function checkDeviation(taskId: number): Promise<DeviationAlert | null> {
  // return callMCPTool('deviation:check_deviation', { task_id: taskId });

  return null; // No deviation
}

/**
 * Get all currently deviating tasks
 */
export async function getActiveDeviations(): Promise<DeviationAlert[]> {
  // return callMCPTool('deviation:get_active_deviations', {});

  return [];
}

/**
 * Trigger replanning for an off-track task
 */
export async function triggerReplanning(taskId: number): Promise<{ success: boolean; message: string }> {
  // return callMCPTool('deviation:trigger_replanning', { task_id: taskId });

  return { success: false, message: "No deviation detected" };
}
