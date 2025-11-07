/**
 * Prospective Memory Operations
 *
 * Functions for task management, goals, and event-based triggers.
 *
 * @packageDocumentation
 */

export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority: number;
  dueDate?: number;
  createdAt: number;
  completedAt?: number;
}

export interface Goal {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'completed' | 'abandoned';
  target?: unknown;
  progress: number;
  deadline?: number;
  relatedTasks: string[];
}

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Create a task
 */
export async function createTask(
  title: string,
  description?: string,
  priority?: number,
  dueDate?: number
): Promise<string> {
  const result = (await callMCPTool('prospective/createTask', {
    title,
    description,
    priority: priority ?? 5,
    dueDate,
  })) as { id: string };

  return result.id;
}

/**
 * List tasks
 */
export async function listTasks(
  status?: string,
  limit: number = 20,
  offset: number = 0
): Promise<Task[]> {
  return (await callMCPTool('prospective/listTasks', {
    status,
    limit,
    offset,
  })) as Task[];
}

/**
 * Get task by ID
 */
export async function getTask(id: string): Promise<Task | null> {
  return (await callMCPTool('prospective/getTask', {
    id,
  })) as Task | null;
}

/**
 * Update task
 */
export async function updateTask(
  id: string,
  updates: Partial<Task>
): Promise<boolean> {
  const result = (await callMCPTool('prospective/updateTask', {
    id,
    updates,
  })) as { success: boolean };

  return result.success;
}

/**
 * Complete task
 */
export async function completeTask(id: string): Promise<boolean> {
  return await updateTask(id, { status: 'completed', completedAt: Date.now() });
}

/**
 * Create goal
 */
export async function createGoal(
  name: string,
  description?: string,
  deadline?: number
): Promise<string> {
  const result = (await callMCPTool('prospective/createGoal', {
    name,
    description,
    deadline,
  })) as { id: string };

  return result.id;
}

/**
 * List goals
 */
export async function listGoals(status?: string, limit: number = 20): Promise<Goal[]> {
  return (await callMCPTool('prospective/listGoals', {
    status,
    limit,
  })) as Goal[];
}

/**
 * Get goal by ID
 */
export async function getGoal(id: string): Promise<Goal | null> {
  return (await callMCPTool('prospective/getGoal', {
    id,
  })) as Goal | null;
}

/**
 * Update goal progress
 */
export async function updateGoal(
  id: string,
  progress: number
): Promise<boolean> {
  const result = (await callMCPTool('prospective/updateGoal', {
    id,
    progress: Math.min(100, Math.max(0, progress)),
  })) as { success: boolean };

  return result.success;
}

/**
 * Register an event trigger
 */
export async function registerTrigger(
  event: string,
  action: string,
  condition?: Record<string, unknown>
): Promise<string> {
  const result = (await callMCPTool('prospective/registerTrigger', {
    event,
    action,
    condition,
  })) as { id: string };

  return result.id;
}

/**
 * Get pending tasks (overdue or due soon)
 */
export async function getPendingTasks(): Promise<Task[]> {
  return (await callMCPTool('prospective/getPendingTasks', {})) as Task[];
}

export const operations = {
  createTask: { name: 'createTask', description: 'Create a task', category: 'write' },
  listTasks: { name: 'listTasks', description: 'List tasks', category: 'read' },
  getTask: { name: 'getTask', description: 'Get task by ID', category: 'read' },
  updateTask: { name: 'updateTask', description: 'Update task', category: 'write' },
  completeTask: { name: 'completeTask', description: 'Mark task complete', category: 'write' },
  createGoal: { name: 'createGoal', description: 'Create goal', category: 'write' },
  listGoals: { name: 'listGoals', description: 'List goals', category: 'read' },
  getGoal: { name: 'getGoal', description: 'Get goal by ID', category: 'read' },
  updateGoal: { name: 'updateGoal', description: 'Update goal', category: 'write' },
  registerTrigger: {
    name: 'registerTrigger',
    description: 'Register event trigger',
    category: 'write',
  },
  getPendingTasks: {
    name: 'getPendingTasks',
    description: 'Get pending tasks',
    category: 'read',
  },
} as const;

export function getOperations() {
  return Object.values(operations);
}

export function getOperation(name: string) {
  return operations[name as keyof typeof operations];
}

export function hasOperation(name: string): boolean {
  return name in operations;
}

export function getReadOperations() {
  return getOperations().filter((op) => op.category === 'read');
}

export function getWriteOperations() {
  return getOperations().filter((op) => op.category === 'write');
}
