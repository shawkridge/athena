/**
 * Meta-Memory Operations
 *
 * Functions for quality metrics, expertise tracking, and cognitive load.
 *
 * @packageDocumentation
 */

export interface QualityMetrics {
  compression: number; // 0-1, ratio of condensed vs original
  recall: number; // 0-1, ability to retrieve when needed
  consistency: number; // 0-1, consistency with other memories
  expertise: Record<string, number>; // domain -> level
}

export interface MemoryHealth {
  totalMemories: number;
  averageConfidence: number;
  averageUsefulness: number;
  staleness: number; // 0-1, how outdated memories are
  issues: string[];
}

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Get overall memory health
 */
export async function memoryHealth(): Promise<MemoryHealth> {
  return (await callMCPTool('meta/memoryHealth', {})) as MemoryHealth;
}

/**
 * Get expertise in a domain
 */
export async function getExpertise(domain?: string): Promise<Record<string, number>> {
  return (await callMCPTool('meta/getExpertise', {
    domain,
  })) as Record<string, number>;
}

/**
 * Get cognitive load metrics
 */
export async function getCognitiveLoad(): Promise<{
  workingMemory: number; // 0-1, working memory utilization
  capacity: number; // 7±2 items
  stress: number; // 0-1, cognitive stress level
}> {
  return (await callMCPTool('meta/getCognitiveLoad', {})) as {
    workingMemory: number;
    capacity: number;
    stress: number;
  };
}

/**
 * Get quality metrics
 */
export async function getQualityMetrics(): Promise<QualityMetrics> {
  return (await callMCPTool('meta/getQualityMetrics', {})) as QualityMetrics;
}

/**
 * Get attention metrics
 */
export async function getAttentionMetrics(): Promise<{
  focusArea: string;
  salience: Record<string, number>;
  suppressedMemories: number;
  activeThreads: number;
}> {
  return (await callMCPTool('meta/getAttentionMetrics', {})) as {
    focusArea: string;
    salience: Record<string, number>;
    suppressedMemories: number;
    activeThreads: number;
  };
}

/**
 * Get memory usage statistics
 */
export async function getMemoryStats(): Promise<{
  episodicCount: number;
  semanticCount: number;
  graphEntityCount: number;
  procedureCount: number;
  databaseSize: number; // bytes
}> {
  return (await callMCPTool('meta/getMemoryStats', {})) as {
    episodicCount: number;
    semanticCount: number;
    graphEntityCount: number;
    procedureCount: number;
    databaseSize: number;
  };
}

/**
 * Identify knowledge gaps
 */
export async function findGaps(): Promise<string[]> {
  const result = (await callMCPTool('meta/findGaps', {})) as { gaps: string[] };
  return result.gaps;
}

/**
 * Get memory recommendations
 */
export async function getRecommendations(): Promise<string[]> {
  const result = (await callMCPTool('meta/getRecommendations', {})) as {
    recommendations: string[];
  };
  return result.recommendations;
}

/**
 * Track memory improvement over time
 */
export async function getProgressMetrics(): Promise<{
  totalMemoriesStored: number;
  memoryRetentionRate: number;
  learningVelocity: number;
}> {
  return (await callMCPTool('meta/getProgressMetrics', {})) as {
    totalMemoriesStored: number;
    memoryRetentionRate: number;
    learningVelocity: number;
  };
}

export const operations = {
  memoryHealth: {
    name: 'memoryHealth',
    description: 'Get memory health status',
    category: 'read',
  },
  getExpertise: { name: 'getExpertise', description: 'Get expertise metrics', category: 'read' },
  getCognitiveLoad: {
    name: 'getCognitiveLoad',
    description: 'Get cognitive load',
    category: 'read',
  },
  getQualityMetrics: {
    name: 'getQualityMetrics',
    description: 'Get quality metrics',
    category: 'read',
  },
  getAttentionMetrics: {
    name: 'getAttentionMetrics',
    description: 'Get attention metrics',
    category: 'read',
  },
  getMemoryStats: {
    name: 'getMemoryStats',
    description: 'Get memory statistics',
    category: 'read',
  },
  findGaps: { name: 'findGaps', description: 'Find knowledge gaps', category: 'read' },
  getRecommendations: {
    name: 'getRecommendations',
    description: 'Get recommendations',
    category: 'read',
  },
  getProgressMetrics: {
    name: 'getProgressMetrics',
    description: 'Get progress metrics',
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
