/**
 * Planning Operations - Task Decomposition & Strategy
 *
 * These operations manage the planning layer (Layer 8).
 * Planning handles task decomposition, effort estimation, and execution strategy.
 * Supports formal verification, scenario simulation, and risk assessment.
 *
 * Agents import directly from: athena.planning.operations
 */

export interface Plan {
  id: string;
  goal: string;
  description?: string;
  depth: number;
  status: 'draft' | 'active' | 'completed' | 'failed';
  tags?: string[];
  steps: PlanStep[];
  assumptions: string[];
  risks: Risk[];
  created_at: string;
  updated_at: string;
  estimated_effort_minutes: number;
  actual_effort_minutes?: number;
}

export interface PlanStep {
  id: string;
  title: string;
  description?: string;
  order: number;
  estimated_minutes: number;
  dependencies: string[]; // Other step IDs
  success_criteria: string[];
}

export interface Risk {
  id: string;
  description: string;
  probability: number; // 0-1
  impact: number; // 0-1
  mitigation_strategy: string;
  severity: number; // Probability * Impact
}

export interface ValidationResult {
  plan_id: string;
  is_valid: boolean;
  issues: string[];
  warnings: string[];
  estimated_success_rate: number;
  feasibility_score: number; // 0-1
}

export interface PlanStatistics {
  total_plans: number;
  by_status: Record<string, number>;
  avg_success_rate: number;
  avg_estimation_accuracy: number;
  most_common_risks: string[];
}

/**
 * Create a plan for a goal
 *
 * Decomposes a goal into hierarchical steps with effort estimates.
 * Plan includes assumptions, risks, and success criteria.
 *
 * @param goal - Goal to plan for
 * @param description - Goal description (optional)
 * @param depth - Planning depth 1-5 (default: 3)
 * @param tags - Tags for categorization (optional)
 * @returns Plan object with hierarchy
 *
 * @implementation src/athena/planning/operations.py:create_plan
 *
 * @example
 * ```python
 * from athena.planning.operations import create_plan
 *
 * plan = await create_plan(
 *   goal="Launch API v2.0",
 *   description="Complete redesign with GraphQL support",
 *   depth=3,
 *   tags=["api", "major-release"]
 * )
 * print(f"Created plan with {len(plan['steps'])} steps")
 * ```
 */
export async function create_plan(
  goal: string,
  description?: string,
  depth?: number,
  tags?: string[]
): Promise<Plan>;

/**
 * Validate a plan
 *
 * Uses formal verification to check plan feasibility.
 * Detects missing dependencies, circular references, unrealistic estimates.
 * Returns issue list and success probability estimate.
 *
 * @param plan_id - Plan to validate
 * @returns Validation result with issues and feasibility score
 *
 * @implementation src/athena/planning/operations.py:validate_plan
 */
export async function validate_plan(plan_id: string): Promise<ValidationResult>;

/**
 * Get a specific plan
 *
 * @param plan_id - Plan identifier
 * @returns Plan object or null if not found
 *
 * @implementation src/athena/planning/operations.py:get_plan
 */
export async function get_plan(plan_id: string): Promise<Plan | null>;

/**
 * List plans
 *
 * @param limit - Maximum plans (default: 20)
 * @param status - Filter by status (optional)
 * @param sort_by - Sort order: "created_at", "estimated_effort" (default: "created_at")
 * @returns List of plans
 *
 * @implementation src/athena/planning/operations.py:list_plans
 */
export async function list_plans(
  limit?: number,
  status?: string,
  sort_by?: string
): Promise<Plan[]>;

/**
 * Estimate effort for a plan
 *
 * Predicts total effort by analyzing task characteristics and historical data.
 * Returns estimate with confidence bounds and bias factors.
 *
 * @param plan_id - Plan to estimate
 * @returns Effort estimate with ranges and confidence
 *
 * @implementation src/athena/planning/operations.py:estimate_effort
 */
export async function estimate_effort(
  plan_id: string
): Promise<{
  estimated_minutes: number;
  min_minutes: number;
  max_minutes: number;
  confidence: number;
  bias_factor: number;
}>;

/**
 * Update plan status
 *
 * Moves a plan through lifecycle: draft → active → completed (or failed)
 *
 * @param plan_id - Plan identifier
 * @param status - New status: "draft", "active", "completed", "failed"
 * @param actual_effort_minutes - Actual effort if completing (optional)
 * @returns True if update successful
 *
 * @implementation src/athena/planning/operations.py:update_plan_status
 */
export async function update_plan_status(
  plan_id: string,
  status: string,
  actual_effort_minutes?: number
): Promise<boolean>;

/**
 * Get planning statistics
 *
 * @returns Statistics about plans and execution
 *
 * @implementation src/athena/planning/operations.py:get_statistics
 */
export async function get_statistics(): Promise<PlanStatistics>;
