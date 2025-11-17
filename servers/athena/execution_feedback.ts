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
 * Stores completion feedback for effort prediction and pattern refinement.
 * Calculates variance from estimate and triggers consolidation if useful.
 *
 * @param input - Completion feedback including actual duration and outcomes
 * @returns Feedback result with variance analysis
 *
 * @implementation src/athena/prospective/operations.py:update_task_status
 *
 * @example
 * ```python
 * from athena.prospective.operations import update_task_status
 *
 * success = await update_task_status(
 *   task_id="task-123",
 *   status="completed"
 * )
 * ```
 */
export async function recordCompletion(input: CompletionFeedback): Promise<FeedbackResult>;

/**
 * Get feedback summary for a task
 *
 * @param taskId - Task identifier
 * @returns Feedback summary with outcomes and lessons learned
 *
 * @implementation src/athena/prospective/operations.py:get_task
 */
export async function getFeedback(taskId: number): Promise<Record<string, any>>;
