/**
 * Procedural Memory Operations
 *
 * Functions for storing, retrieving, and executing reusable procedures/workflows.
 *
 * @packageDocumentation
 */

export interface Procedure {
  id: string;
  name: string;
  description: string;
  steps: string[];
  inputs: Record<string, string>;
  outputs: Record<string, string>;
  successRate: number;
  lastUsed: number;
  useCount: number;
}

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Extract procedures from past events/episodes
 *
 * Analyzes episodic memories to identify reusable patterns and workflows.
 */
export async function extract(
  minOccurrences: number = 3,
  minSuccessRate: number = 0.7
): Promise<string[]> {
  const result = (await callMCPTool('procedural/extract', {
    minOccurrences,
    minSuccessRate,
  })) as { procedureIds: string[] };

  return result.procedureIds;
}

/**
 * List all procedures
 */
export async function list(limit: number = 50, offset: number = 0): Promise<Procedure[]> {
  return (await callMCPTool('procedural/list', {
    limit,
    offset,
  })) as Procedure[];
}

/**
 * Get a procedure by ID
 */
export async function get(id: string): Promise<Procedure | null> {
  return (await callMCPTool('procedural/get', {
    id,
  })) as Procedure | null;
}

/**
 * Execute a procedure with inputs
 */
export async function execute(
  id: string,
  inputs?: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return (await callMCPTool('procedural/execute', {
    id,
    inputs: inputs ?? {},
  })) as Record<string, unknown>;
}

/**
 * Get procedure effectiveness metrics
 */
export async function getEffectiveness(id: string): Promise<{
  successRate: number;
  useCount: number;
  avgExecutionTime: number;
}> {
  return (await callMCPTool('procedural/effectiveness', {
    id,
  })) as { successRate: number; useCount: number; avgExecutionTime: number };
}

/**
 * Search procedures
 */
export async function search(query: string, limit: number = 10): Promise<Procedure[]> {
  return (await callMCPTool('procedural/search', {
    query,
    limit,
  })) as Procedure[];
}

export const operations = {
  extract: { name: 'extract', description: 'Extract procedures from episodes', category: 'write' },
  list: { name: 'list', description: 'List all procedures', category: 'read' },
  get: { name: 'get', description: 'Get procedure by ID', category: 'read' },
  execute: { name: 'execute', description: 'Execute a procedure', category: 'write' },
  getEffectiveness: {
    name: 'getEffectiveness',
    description: 'Get effectiveness metrics',
    category: 'read',
  },
  search: { name: 'search', description: 'Search procedures', category: 'read' },
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
