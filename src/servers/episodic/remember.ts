/**
 * Episodic Memory: Remember Operation
 *
 * Store new memories in the episodic memory layer
 */

import type { RememberInput, RememberResult } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Store a new memory in episodic layer
 *
 * Adds a new event/experience to episodic memory with timestamp,
 * context, tags, and optional expiration.
 *
 * @param content - Memory content (text description of the event)
 * @param context - Additional context (metadata about the event)
 * @param tags - Tags for categorization and discovery
 * @param source - Source identifier (where this memory came from)
 * @param expiresAt - Optional timestamp when memory expires (TTL)
 * @returns Result with memory ID and confirmation
 *
 * @example
 * // Simple memory
 * const result = await remember('User asked about project timeline');
 * console.log('Stored memory:', result.id);
 *
 * @example
 * // Rich memory with context
 * const result = await remember(
 *   'Quarterly planning meeting concluded with Q2 goals',
 *   {
 *     participants: ['Alice', 'Bob', 'Charlie'],
 *     duration: 90,
 *     decisions: ['increase budget', 'hire 2 engineers'],
 *     location: 'Conference Room A'
 *   },
 *   ['meeting', 'planning', 'q2'],
 *   'user-interaction',
 *   Date.now() + 90 * 24 * 60 * 60 * 1000 // Expires in 90 days
 * );
 * console.log('Meeting recorded:', result.id);
 */
export async function remember(
  content: string,
  context?: Record<string, unknown>,
  tags?: string[],
  source?: string,
  expiresAt?: number
): Promise<string> {
  const result = (await callMCPTool('episodic/remember', {
    content,
    context: context ?? {},
    tags: tags ?? [],
    source: source ?? 'agent',
    expiresAt,
  })) as RememberResult;

  return result.id;
}

/**
 * Store memory with full options
 *
 * Provides access to all remember parameters as an options object.
 *
 * @param options - Memory input options
 * @returns Memory ID
 */
export async function rememberWithOptions(options: RememberInput): Promise<string> {
  const result = (await callMCPTool('episodic/remember', {
    content: options.content,
    context: options.context ?? {},
    tags: options.tags ?? [],
    source: options.source ?? 'agent',
    expiresAt: options.expiresAt,
  })) as RememberResult;

  return result.id;
}

/**
 * Store a decision with explicit context
 *
 * Specialized version for recording decisions with reasoning.
 *
 * @param decision - What was decided
 * @param reasoning - Why the decision was made
 * @param options - Optional details
 * @returns Memory ID
 *
 * @example
 * const id = await rememberDecision(
 *   'Chose solution approach B over A',
 *   'Better performance and maintainability',
 *   {
 *     alternatives: ['A', 'C'],
 *     confidence: 0.95,
 *     reviewedBy: ['alice@example.com']
 *   }
 * );
 */
export async function rememberDecision(
  decision: string,
  reasoning: string,
  options?: Record<string, unknown>
): Promise<string> {
  return await remember(
    `Decision: ${decision}. Reasoning: ${reasoning}`,
    {
      type: 'decision',
      reasoning,
      ...options,
    },
    ['decision', 'important'],
    'agent'
  );
}

/**
 * Store an insight or discovery
 *
 * Specialized version for recording insights and learnings.
 *
 * @param insight - The insight or learning
 * @param category - Category of insight (technical, process, domain, etc.)
 * @param confidence - Confidence level (0-1)
 * @returns Memory ID
 *
 * @example
 * const id = await rememberInsight(
 *   'Database queries are N+1 problem in list view',
 *   'performance',
 *   0.9
 * );
 */
export async function rememberInsight(
  insight: string,
  category: string = 'general',
  confidence: number = 0.8
): Promise<string> {
  return await remember(
    `Insight: ${insight}`,
    {
      type: 'insight',
      category,
      confidence,
    },
    ['insight', category],
    'agent'
  );
}

/**
 * Store an error or failure for learning
 *
 * Specialized version for recording errors with context.
 *
 * @param error - Error description
 * @param context - Error context (stack trace, input, etc.)
 * @param solution - Optional solution applied
 * @returns Memory ID
 */
export async function rememberError(
  error: string,
  context?: Record<string, unknown>,
  solution?: string
): Promise<string> {
  return await remember(
    `Error: ${error}${solution ? `. Solution: ${solution}` : ''}`,
    {
      type: 'error',
      ...context,
    },
    ['error', 'learning'],
    'agent'
  );
}
