/**
 * Consolidation Operations
 *
 * Functions for sleep-like consolidation, pattern extraction, and learning.
 *
 * @packageDocumentation
 */

export interface ConsolidationMetrics {
  processedEvents: number;
  extractedPatterns: number;
  validatedPatterns: number;
  executionTimeMs: number;
}

export interface ConsolidationStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress: number; // 0-1
  currentPhase: string;
  estimatedRemaining: number; // ms
}

export interface PatternAnalysis {
  patterns: string[];
  frequency: Record<string, number>;
  confidence: Record<string, number>;
  relatedPatterns: Record<string, string[]>;
}

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Run consolidation cycle
 *
 * Triggers sleep-like consolidation converting episodic to semantic memories.
 */
export async function consolidate(strategy?: string): Promise<ConsolidationMetrics> {
  return (await callMCPTool('consolidation/consolidate', {
    strategy: strategy ?? 'balanced',
  })) as ConsolidationMetrics;
}

/**
 * Get consolidation metrics
 */
export async function getMetrics(): Promise<ConsolidationMetrics> {
  return (await callMCPTool('consolidation/getMetrics', {})) as ConsolidationMetrics;
}

/**
 * Analyze patterns in consolidation
 */
export async function analyzePatterns(
  limit?: number,
  minConfidence?: number
): Promise<PatternAnalysis> {
  return (await callMCPTool('consolidation/analyzePatterns', {
    limit,
    minConfidence,
  })) as PatternAnalysis;
}

/**
 * Get consolidation status
 */
export async function getStatus(): Promise<ConsolidationStatus> {
  return (await callMCPTool('consolidation/getStatus', {})) as ConsolidationStatus;
}

/**
 * Get consolidation history
 */
export async function getHistory(limit: number = 10): Promise<Array<{
  timestamp: number;
  metrics: ConsolidationMetrics;
  patterns: number;
}>> {
  return (await callMCPTool('consolidation/getHistory', {
    limit,
  })) as Array<{ timestamp: number; metrics: ConsolidationMetrics; patterns: number }>;
}

/**
 * Configure consolidation strategy
 */
export async function configureStrategy(
  strategy: 'balanced' | 'speed' | 'quality' | 'minimal',
  options?: Record<string, unknown>
): Promise<void> {
  await callMCPTool('consolidation/configureStrategy', {
    strategy,
    options,
  });
}

/**
 * Get consolidation recommendations
 */
export async function getRecommendations(): Promise<string[]> {
  const result = (await callMCPTool('consolidation/getRecommendations', {})) as {
    recommendations: string[];
  };
  return result.recommendations;
}

export const operations = {
  consolidate: {
    name: 'consolidate',
    description: 'Run consolidation cycle',
    category: 'write',
  },
  getMetrics: { name: 'getMetrics', description: 'Get consolidation metrics', category: 'read' },
  analyzePatterns: {
    name: 'analyzePatterns',
    description: 'Analyze patterns',
    category: 'read',
  },
  getStatus: { name: 'getStatus', description: 'Get consolidation status', category: 'read' },
  getHistory: { name: 'getHistory', description: 'Get consolidation history', category: 'read' },
  configureStrategy: {
    name: 'configureStrategy',
    description: 'Configure strategy',
    category: 'write',
  },
  getRecommendations: {
    name: 'getRecommendations',
    description: 'Get recommendations',
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
