/**
 * Planning Recommendations Tool Wrapper
 *
 * This module wraps the PlanningRecommendationService as an MCP-callable tool.
 * Agents discover this via filesystem and import it to use planning strategies.
 *
 * Architecture: Follows Anthropic's filesystem-based MCP paradigm
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
 * @param input - Task characteristics and filtering parameters
 * @returns List of recommended patterns ranked by effectiveness
 *
 * Example usage in agent code:
 * ```typescript
 * import { recommend } from './servers/athena/planning_recommendations.ts';
 *
 * const recommendations = await recommend({
 *   taskId: 1,
 *   taskDescription: "Implement API",
 *   taskType: "feature",
 *   complexity: 7,
 *   domain: "backend"
 * });
 *
 * // Agent filters locally - keeps only top 1
 * const topRec = recommendations[0];
 * console.log(`Recommended: ${topRec.patternName} (${topRec.successRate * 100}%)`);
 * ```
 */
export async function recommend(input: RecommendationInput): Promise<PatternRecommendation[]> {
  // TODO: Connect to real Athena backend via MCP
  // return callMCPTool('planning:get_recommendations', input);

  // Smart mock recommendations based on task characteristics
  const recommendations = _getSmartRecommendations(input);

  // Sort by success rate (highest first)
  return recommendations.sort((a, b) => b.successRate - a.successRate);
}

/**
 * Internal: Generate smart recommendations based on task characteristics
 */
function _getSmartRecommendations(input: RecommendationInput): PatternRecommendation[] {
  const { taskType, complexity, domain } = input;
  const allPatterns: PatternRecommendation[] = [
    {
      patternName: "Hierarchical Decomposition",
      patternType: "decomposition",
      successRate: complexity > 7 ? 0.94 : 0.85,
      executionCount: 156,
      confidence: complexity > 6 ? 'high' : 'medium',
      rationale: "Breaks complex work into manageable chunks. Excellent for multi-layer architectures and systems thinking.",
      alternatives: ["Incremental Integration", "Test-Driven Development"]
    },
    {
      patternName: "Test-Driven Development",
      patternType: "testing",
      successRate: taskType === 'bugfix' ? 0.91 : 0.84,
      executionCount: 142,
      confidence: 'high',
      rationale: "Define requirements via tests first. Prevents regressions and ensures correctness. Best for bug fixes and refactoring.",
      alternatives: ["Incremental Integration", "Pair Programming"]
    },
    {
      patternName: "Incremental Integration",
      patternType: "iteration",
      successRate: 0.86,
      executionCount: 98,
      confidence: 'high',
      rationale: "Build and integrate in small steps. Reduces integration risk and enables early feedback.",
      alternatives: ["Hierarchical Decomposition", "Agile Iteration"]
    },
    {
      patternName: "Agile Iteration",
      patternType: "iteration",
      successRate: complexity < 4 ? 0.79 : 0.68,
      executionCount: 87,
      confidence: complexity > 6 ? 'low' : 'medium',
      rationale: "Frequent cycles with continuous feedback. Works well for exploratory features and designs.",
      alternatives: ["Hierarchical Decomposition", "Spike & Stabilize"]
    },
    {
      patternName: "Spike & Stabilize",
      patternType: "research",
      successRate: domain === 'research' ? 0.89 : 0.72,
      executionCount: 64,
      confidence: domain === 'research' ? 'high' : 'medium',
      rationale: "Exploration phase followed by hardening. Ideal for unknown technologies or unproven approaches.",
      alternatives: ["Agile Iteration", "Prototyping"]
    },
    {
      patternName: "Pair Programming",
      patternType: "collaboration",
      successRate: complexity > 8 ? 0.88 : 0.71,
      executionCount: 45,
      confidence: complexity > 8 ? 'medium' : 'low',
      rationale: "Two developers on one machine. Excellent for complex, high-risk work and knowledge transfer.",
      alternatives: ["Code Review Cycles", "Mob Programming"]
    },
    {
      patternName: "Code Review Cycles",
      patternType: "quality",
      successRate: 0.82,
      executionCount: 134,
      confidence: 'high',
      rationale: "Asynchronous peer review. Standard practice for distributed teams and code quality gates.",
      alternatives: ["Pair Programming", "Continuous Integration"]
    },
    {
      patternName: "Documentation-Driven Development",
      patternType: "documentation",
      successRate: taskType === 'docs' ? 0.93 : 0.76,
      executionCount: 52,
      confidence: taskType === 'docs' ? 'high' : 'medium',
      rationale: "Write documentation first, then implementation. Clarifies requirements and API design.",
      alternatives: ["Test-Driven Development", "Example-Driven Development"]
    }
  ];

  // Filter by success rate threshold if provided
  const filtered = input.minSuccessRate
    ? allPatterns.filter(p => p.successRate >= input.minSuccessRate!)
    : allPatterns;

  // Return at least top 3, or all if fewer than 3 qualify
  return filtered.length > 0 ? filtered : allPatterns.slice(0, 3);
}

/**
 * Get strategy details for implementing a specific pattern
 *
 * @param patternType - Type of pattern to get details for
 * @returns Detailed strategy information
 */
export async function getStrategyDetails(patternType: string): Promise<Record<string, any>> {
  // return callMCPTool('planning:get_strategy_details', { pattern_type: patternType });

  return {
    patternType,
    decompositionType: "hierarchical",
    chunkSizeMinutes: 120,
    maxDepth: 3,
    steps: []
  };
}
