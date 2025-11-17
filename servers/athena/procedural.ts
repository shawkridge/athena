/**
 * Procedural Memory Operations - Reusable Workflows
 *
 * These operations manage the procedural memory layer (Layer 3).
 * Procedural memory stores learned workflows and procedures that consistently succeed.
 * Procedures track execution count, success rate, and can be refined over time.
 *
 * Agents import directly from: athena.procedural.operations
 */

export interface Procedure {
  id: string;
  name: string;
  description: string;
  steps: string[];
  tags?: string[];
  success_count: number;
  failure_count: number;
  success_rate: number;
  execution_count: number;
  last_used?: string;
  metadata?: Record<string, any>;
}

export interface ProcedureStatistics {
  total_procedures: number;
  by_success_rate: Record<string, number>;
  most_used: Procedure[];
  avg_success_rate: number;
}

/**
 * Extract a procedure from a task or sequence of operations
 *
 * Learns and stores a new procedure based on a successful task completion.
 * Procedures can be retrieved and reused for similar tasks.
 *
 * @param name - Procedure name
 * @param description - What the procedure does
 * @param steps - List of steps in the procedure
 * @param tags - Optional tags for categorization
 * @param metadata - Optional additional metadata
 * @returns Procedure ID
 *
 * @implementation src/athena/procedural/operations.py:extract_procedure
 *
 * @example
 * ```python
 * from athena.procedural.operations import extract_procedure
 *
 * proc_id = await extract_procedure(
 *   name="Code Review Process",
 *   description="Standard process for reviewing pull requests",
 *   steps=[
 *     "Read PR description and context",
 *     "Check for tests",
 *     "Review code quality and logic",
 *     "Verify no security issues",
 *     "Approve or request changes"
 *   ],
 *   tags=["engineering", "review"]
 * )
 * ```
 */
export async function extract_procedure(
  name: string,
  description: string,
  steps: string[],
  tags?: string[],
  metadata?: Record<string, any>
): Promise<string>;

/**
 * List procedures
 *
 * Returns all stored procedures, optionally filtered and sorted.
 *
 * @param limit - Maximum procedures to return (default: 20)
 * @param min_success_rate - Filter by minimum success rate (default: 0.0)
 * @param sort_by - Sort order: "success_rate", "execution_count", "last_used" (default: "success_rate")
 * @returns List of procedures
 *
 * @implementation src/athena/procedural/operations.py:list_procedures
 */
export async function list_procedures(
  limit?: number,
  min_success_rate?: number,
  sort_by?: string
): Promise<Procedure[]>;

/**
 * Get a specific procedure by ID
 *
 * @param procedure_id - Procedure identifier
 * @returns Procedure object or null if not found
 *
 * @implementation src/athena/procedural/operations.py:get_procedure
 */
export async function get_procedure(procedure_id: string): Promise<Procedure | null>;

/**
 * Search procedures
 *
 * Searches for procedures matching query in name, description, or tags.
 *
 * @param query - Search query
 * @param limit - Maximum results (default: 10)
 * @returns List of matching procedures
 *
 * @implementation src/athena/procedural/operations.py:search_procedures
 */
export async function search_procedures(
  query: string,
  limit?: number
): Promise<Procedure[]>;

/**
 * Get procedures by tags
 *
 * @param tags - Tags to filter by
 * @param limit - Maximum results (default: 20)
 * @returns List of procedures with matching tags
 *
 * @implementation src/athena/procedural/operations.py:get_procedures_by_tags
 */
export async function get_procedures_by_tags(
  tags: string[],
  limit?: number
): Promise<Procedure[]>;

/**
 * Update procedure success
 *
 * Records a successful execution of a procedure, updating success metrics.
 *
 * @param procedure_id - Procedure identifier
 * @param success - Whether execution was successful
 * @param feedback - Optional execution feedback
 * @returns Updated success rate
 *
 * @implementation src/athena/procedural/operations.py:update_procedure_success
 */
export async function update_procedure_success(
  procedure_id: string,
  success: boolean,
  feedback?: string
): Promise<number>;

/**
 * Get procedural memory statistics
 *
 * @returns Statistics about stored procedures
 *
 * @implementation src/athena/procedural/operations.py:get_statistics
 */
export async function get_statistics(): Promise<ProcedureStatistics>;
