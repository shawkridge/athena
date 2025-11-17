/**
 * Planning Recommendations Tool Wrapper
 *
 * This module wraps the PlanningRecommendationService as an operations tool.
 * Agents discover this via filesystem and import it to use planning strategies.
 *
 * Architecture: Follows Anthropic's filesystem-based operations discovery
 * - Tool definitions NOT in context (stored in this file)
 * - Agents import this module and call functions
 * - Data stays in execution environment, only summaries return
 */

interface RecommendationInput {
  taskId: number;
  taskDescription: string;
  taskType: string;
  complexity: number;
  domain?: string;
  minSuccessRate?: number;
}

interface PatternRecommendation {
  patternName: string;
  patternType: string;
  successRate: number;
  executionCount: number;
  confidence: 'low' | 'medium' | 'high';
  rationale: string;
  alternatives?: string[];
}

/**
 * Get planning strategy recommendations for a task
 *
 * Retrieves recommended planning patterns based on task characteristics and historical success rates.
 * Patterns are ranked by effectiveness for similar task types.
 *
 * @param input - Task characteristics and filtering parameters
 * @returns List of recommended patterns ranked by effectiveness
 *
 * @implementation src/athena/planning/operations.py:create_plan
 *
 * @example
 * ```python
 * from athena.planning.operations import create_plan
 *
 * plan = await create_plan(
 *   goal="Implement user authentication",
 *   description="Add OAuth + JWT to API",
 *   depth=3
 * )
 * ```
 */
export async function recommend(input: RecommendationInput): Promise<PatternRecommendation[]>;

/**
 * Get strategy details for implementing a specific pattern
 *
 * @param patternType - Type of pattern to get details for
 * @returns Detailed strategy information
 *
 * @implementation src/athena/planning/operations.py:validate_plan
 */
export async function getStrategyDetails(patternType: string): Promise<Record<string, any>>;
