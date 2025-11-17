/**
 * Trigger Management Tool Wrapper
 *
 * Agents use this to create and manage task triggers.
 * Filesystem-based MCP paradigm.
 */

export interface TriggerDef {
  taskId: number;
  triggerType: 'time' | 'event' | 'dependency' | 'file' | 'context';
  condition: string;
  metadata?: Record<string, any>;
}

/**
 * Create a trigger for a task
 *
 * Triggers automatically activate tasks when conditions are met (time, event, dependency, file, or context).
 *
 * @param input - Trigger definition including type and condition
 * @returns Success status and trigger identifier
 *
 * @implementation src/athena/prospective/operations.py:create_task
 *
 * @example
 * ```python
 * from athena.prospective.operations import create_task
 *
 * task = await create_task(
 *   title="Review PR",
 *   priority=8,
 *   tags=["code-review"]
 * )
 * ```
 */
export async function createTrigger(input: TriggerDef): Promise<{ success: boolean; triggerId: number }>;

/**
 * Get all triggers for a task
 *
 * @param taskId - Task identifier
 * @returns List of all triggers configured for the task
 *
 * @implementation src/athena/prospective/operations.py:get_task
 */
export async function getTriggers(taskId: number): Promise<TriggerDef[]>;
