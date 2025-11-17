/**
 * Prospective Memory Operations - Tasks & Goals Management
 *
 * These operations manage the prospective memory layer (Layer 4).
 * Prospective memory stores active goals, tasks, and reminders with triggers.
 * Tasks can be activated by time, events, dependencies, files, or context conditions.
 *
 * Agents import directly from: athena.prospective.operations
 */

export interface ProspectiveTask {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'blocked';
  priority: number; // 1-10
  due_date?: string;
  created_at: string;
  updated_at: string;
  tags?: string[];
  estimated_effort_minutes?: number;
  actual_effort_minutes?: number;
  blockers?: string[];
  depends_on?: string[]; // Task IDs
  metadata?: Record<string, any>;
}

export interface TaskStatistics {
  total_tasks: number;
  by_status: Record<string, number>;
  overdue_count: number;
  avg_priority: number;
  completion_rate: number;
}

/**
 * Create a new task
 *
 * Creates a new task in prospective memory with optional priority, due date, and triggers.
 * Tasks start in 'pending' status and can be moved through the workflow.
 *
 * @param title - Task title
 * @param description - Task description (optional)
 * @param priority - Priority 1-10 (default: 5)
 * @param due_date - Due date ISO format (optional)
 * @param tags - Tags for categorization (optional)
 * @param estimated_effort_minutes - Effort estimate (optional)
 * @param metadata - Additional metadata (optional)
 * @returns Task ID
 *
 * @implementation src/athena/prospective/operations.py:create_task
 *
 * @example
 * ```python
 * from athena.prospective.operations import create_task
 *
 * task_id = await create_task(
 *   title="Implement authentication",
 *   description="Add OAuth2 support",
 *   priority=9,
 *   estimated_effort_minutes=480,
 *   tags=["backend", "security"]
 * )
 * ```
 */
export async function create_task(
  title: string,
  description?: string,
  priority?: number,
  due_date?: string,
  tags?: string[],
  estimated_effort_minutes?: number,
  metadata?: Record<string, any>
): Promise<string>;

/**
 * List all tasks
 *
 * @param limit - Maximum tasks to return (default: 20)
 * @param status - Filter by status (optional)
 * @param sort_by - Sort order: "priority", "due_date", "created_at" (default: "priority")
 * @returns List of tasks
 *
 * @implementation src/athena/prospective/operations.py:list_tasks
 */
export async function list_tasks(
  limit?: number,
  status?: string,
  sort_by?: string
): Promise<ProspectiveTask[]>;

/**
 * Get a specific task by ID
 *
 * @param task_id - Task identifier
 * @returns Task object or null if not found
 *
 * @implementation src/athena/prospective/operations.py:get_task
 */
export async function get_task(task_id: string): Promise<ProspectiveTask | null>;

/**
 * Update task status
 *
 * Moves a task through the workflow: pending → in_progress → completed (or blocked)
 *
 * @param task_id - Task identifier
 * @param status - New status: "pending", "in_progress", "completed", "blocked"
 * @param actual_effort_minutes - Actual effort if completing (optional)
 * @param blockers - Blockers if blocking (optional)
 * @returns True if update successful
 *
 * @implementation src/athena/prospective/operations.py:update_task_status
 */
export async function update_task_status(
  task_id: string,
  status: string,
  actual_effort_minutes?: number,
  blockers?: string[]
): Promise<boolean>;

/**
 * Get all active (non-completed) tasks
 *
 * @param limit - Maximum tasks (default: 10)
 * @param sort_by - Sort order: "priority", "due_date" (default: "priority")
 * @returns List of active tasks
 *
 * @implementation src/athena/prospective/operations.py:get_active_tasks
 */
export async function get_active_tasks(
  limit?: number,
  sort_by?: string
): Promise<ProspectiveTask[]>;

/**
 * Get overdue tasks
 *
 * Returns tasks with due dates in the past that are not completed.
 *
 * @param limit - Maximum tasks (default: 10)
 * @returns List of overdue tasks
 *
 * @implementation src/athena/prospective/operations.py:get_overdue_tasks
 */
export async function get_overdue_tasks(limit?: number): Promise<ProspectiveTask[]>;

/**
 * Get task statistics
 *
 * @returns Statistics about all tasks
 *
 * @implementation src/athena/prospective/operations.py:get_statistics
 */
export async function get_statistics(): Promise<TaskStatistics>;
