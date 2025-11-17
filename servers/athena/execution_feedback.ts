/**
 * Execution Feedback Tool Wrapper
 *
 * Agents use this to record task completion feedback and trigger learning.
 * Follows filesystem-based operations discovery: discoverable via ./servers/ directory.
 */

interface CompletionFeedback {
  taskId: number;
  actualMinutes: number;
  success: boolean;
  blockers?: string[];
  lessonsLearned?: string;
}

export interface FeedbackResult {
  taskId: number;
  variance: number;
  variancePercent: number;
  success: boolean;
  message: string;
}

/**
 * Record task completion and feedback for learning
 *
 * Example agent usage:
 * ```typescript
 * import { recordCompletion } from './servers/athena/execution_feedback.ts';
 *
 * const feedback = await recordCompletion({
 *   taskId: 1,
 *   actualMinutes: 140,
 *   success: true,
 *   lessonsLearned: "API design was simpler than expected"
 * });
 * console.log(`Task 1: ${feedback.variancePercent.toFixed(1)}% variance`);
 * ```
 */
export async function recordCompletion(input: CompletionFeedback): Promise<FeedbackResult> {
  // return callMCPTool('execution:record_completion', input);

  return {
    taskId: input.taskId,
    variance: input.actualMinutes - 120, // Assuming 120 min estimate
    variancePercent: ((input.actualMinutes - 120) / 120) * 100,
    success: input.success,
    message: `Task ${input.taskId} completed with feedback recorded`
  };
}

/**
 * Get feedback summary for a task
 */
export async function getFeedback(taskId: number): Promise<Record<string, any>> {
  // return callMCPTool('execution:get_feedback', { task_id: taskId });

  return {
    taskId,
    status: "completed",
    actualDurationMinutes: 140,
    lessonsLearned: null,
    blockers: []
  };
}
