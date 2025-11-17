/**
 * Athena MCP Tools - Filesystem-Based Module Index
 *
 * This index exposes all Athena planning and execution tools.
 * Agents discover tools by exploring ./servers/athena/ directory
 * and importing from these modules.
 *
 * Architecture: Anthropic's filesystem-based MCP paradigm
 * - Tool definitions stored as TS files (NOT in context)
 * - Agents discover via directory listing
 * - Agents import and use functions
 * - Data stays in execution environment
 * - Only summaries returned to context
 */

export * from './planning_recommendations';
export * from './execution_feedback';
export * from './deviation_monitor';
export * from './effort_prediction';
export * from './trigger_management';

/**
 * Tool discovery helper
 *
 * Agents can use this to understand available tools and their parameters.
 * This helps agents decide which tools to use for their task.
 */
export const availableTools = {
  planningRecommendations: {
    description: 'Get planning strategy recommendations for tasks',
    functions: ['recommend', 'getStrategyDetails'],
    useCase: 'Recommend proven strategies based on task characteristics'
  },
  executionFeedback: {
    description: 'Record task completion and capture lessons learned',
    functions: ['recordCompletion', 'getFeedback'],
    useCase: 'Record execution outcomes to improve future estimates'
  },
  deviationMonitor: {
    description: 'Detect tasks deviating from estimates',
    functions: ['checkDeviation', 'getActiveDeviations', 'triggerReplanning'],
    useCase: 'Monitor executing tasks and trigger replanning if needed'
  },
  effortPrediction: {
    description: 'Predict effort for new tasks',
    functions: ['predictEffort'],
    useCase: 'Estimate how long a task will take'
  },
  triggerManagement: {
    description: 'Create and manage task activation triggers',
    functions: ['createTrigger', 'getTriggers'],
    useCase: 'Set up conditions for automatic task activation'
  }
};

/**
 * Example agent code pattern
 *
 * Shows how agents discover and use these tools following the paradigm:
 *
 * ```typescript
 * // 1. Agent discovers tools via filesystem
 * ls ./servers/athena/
 *
 * // 2. Agent reads tool file to understand parameters
 * cat ./servers/athena/planning_recommendations.ts
 *
 * // 3. Agent imports and uses in code
 * import { recommend } from './servers/athena/planning_recommendations.ts';
 *
 * const recommendations = await recommend({
 *   taskId: 1,
 *   taskDescription: "Implement API",
 *   taskType: "feature",
 *   complexity: 7
 * });
 *
 * // 4. Agent filters locally (data stays in execution env)
 * const topRec = recommendations[0];
 *
 * // 5. Agent returns only summary to context
 * console.log(`Recommended: ${topRec.patternName}`);
 * // Output: "Recommended: Hierarchical Decomposition"
 *
 * // Result in context: One line of text
 * // Without this paradigm: Full recommendation list (50K+ tokens)
 * ```
 */
