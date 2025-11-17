/**
 * Athena Operations - Filesystem-Based Module Index
 *
 * This index exposes all Athena planning and execution tools.
 * Agents discover tools by exploring ./servers/athena/ directory
 * and importing from these modules.
 *
 * Architecture: Anthropic's filesystem-based operations discovery
 * - Tool definitions stored as TS files (NOT in context)
 * - Agents discover via directory listing
 * - Agents import and use functions
 * - Data stays in execution environment
 * - Only summaries returned to context
 */

// Layer 1: Episodic Memory
export * from './episodic';

// Layer 2: Semantic Memory
export * from './semantic';

// Layer 3: Procedural Memory
export * from './procedural';

// Layer 4: Prospective Memory
export * from './prospective';

// Layer 5: Knowledge Graph
export * from './graph';

// Layer 6: Meta-Memory
export * from './meta';

// Layer 7: Consolidation
export * from './consolidation';

// Layer 8: Planning
export * from './planning';

// Specialized server tools
export * from './planning_recommendations';
export * from './execution_feedback';
export * from './deviation_monitor';
export * from './effort_prediction';
export * from './trigger_management';

/**
 * Operations Registry
 *
 * Maps layer operations to their modules for agent discovery.
 * Agents can use this to find which operations are available.
 *
 * Usage in agent code:
 * ```typescript
 * import { layerOperations } from './servers/athena/index.ts';
 *
 * // Find all operations in episodic layer
 * const episodicOps = layerOperations['episodic'];
 * console.log(`Episodic has ${episodicOps.functions.length} operations`);
 * ```
 */
export const layerOperations = {
  episodic: {
    description: 'Event storage and temporal retrieval',
    module: 'athena.episodic.operations',
    functions: [
      'remember',
      'recall',
      'recall_recent',
      'get_by_session',
      'get_by_tags',
      'get_by_time_range',
      'get_statistics'
    ]
  },
  semantic: {
    description: 'Facts and knowledge storage with hybrid search',
    module: 'athena.memory.operations',
    functions: ['store', 'search']
  },
  procedural: {
    description: 'Reusable workflows and procedures',
    module: 'athena.procedural.operations',
    functions: [
      'extract_procedure',
      'list_procedures',
      'get_procedure',
      'search_procedures',
      'get_procedures_by_tags',
      'update_procedure_success',
      'get_statistics'
    ]
  },
  prospective: {
    description: 'Tasks, goals, and reminders',
    module: 'athena.prospective.operations',
    functions: [
      'create_task',
      'list_tasks',
      'get_task',
      'update_task_status',
      'get_active_tasks',
      'get_overdue_tasks',
      'get_statistics'
    ]
  },
  graph: {
    description: 'Knowledge graph with entities and relationships',
    module: 'athena.graph.operations',
    functions: [
      'add_entity',
      'add_relationship',
      'find_entity',
      'search_entities',
      'find_related',
      'get_communities',
      'update_entity_importance',
      'get_statistics'
    ]
  },
  meta: {
    description: 'Quality tracking, expertise, and cognitive load',
    module: 'athena.meta.operations',
    functions: [
      'rate_memory',
      'get_expertise',
      'get_memory_quality',
      'get_cognitive_load',
      'update_cognitive_load',
      'get_statistics'
    ]
  },
  consolidation: {
    description: 'Pattern extraction and memory compression',
    module: 'athena.consolidation.operations',
    functions: [
      'consolidate',
      'extract_patterns',
      'extract_procedures',
      'get_consolidation_history',
      'get_consolidation_metrics',
      'get_statistics'
    ]
  },
  planning: {
    description: 'Task decomposition and execution strategy',
    module: 'athena.planning.operations',
    functions: [
      'create_plan',
      'validate_plan',
      'get_plan',
      'list_plans',
      'estimate_effort',
      'update_plan_status',
      'get_statistics'
    ]
  }
};

/**
 * Specialized Server Tools
 *
 * These are composite operations that combine multiple layer operations.
 */
export const serverTools = {
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
