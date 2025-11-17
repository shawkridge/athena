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
 * Compares actual elapsed time to estimated duration and returns alert if exceeding threshold.
 *
 * @param taskId - Task identifier to check
 * @returns Deviation alert if task exceeds estimate, null otherwise
 *
 * @implementation src/athena/prospective/operations.py:get_task
 *
 * @example
 * ```python
 * from athena.prospective.operations import get_task
 *
 * task = await get_task(task_id="task-123")
 * if task and task['status'] == 'in_progress':
 *   print(f"Task: {task['title']}")
 * ```
 */
export async function checkDeviation(taskId: number): Promise<DeviationAlert | null>;

/**
 * Get all currently deviating tasks
 *
 * @returns List of all tasks currently exceeding their time estimates
 *
 * @implementation src/athena/prospective/operations.py:get_active_tasks
 */
export async function getActiveDeviations(): Promise<DeviationAlert[]>;

/**
 * Trigger replanning for an off-track task
 *
 * Initiates a replanning cycle for a task that has deviated significantly from estimates.
 *
 * @param taskId - Task identifier to replan
 * @returns Success status and message
 *
 * @implementation src/athena/planning/operations.py:create_plan
 */
export async function triggerReplanning(taskId: number): Promise<{ success: boolean; message: string }>;
