/**
 * Meta-Memory Operations (Layer 6)
 *
 * Functions for quality metrics, expertise tracking, and cognitive load monitoring.
 * All operations are available as direct Python async functions via:
 *   from athena.meta.operations import rate_memory, get_expertise, etc.
 *
 * @packageDocumentation
 * @implementation src/athena/meta/operations.py
 */

/**
 * Quality scores for a memory
 */
export interface MemoryQuality {
  usefulness_score: number; // 0-1
  confidence: number; // 0-1
  relevance_decay: number; // 0-1
  access_count?: number;
}

/**
 * Expertise information for a topic
 */
export interface Expertise {
  topic?: string;
  level: "beginner" | "intermediate" | "advanced" | "expert";
  memories: number;
  confidence: number;
}

/**
 * Cognitive load metrics
 */
export interface CognitiveLoad {
  episodic_load: number;
  semantic_load: number;
  total_memories: number;
  load_percentage: number;
}

/**
 * Meta-memory statistics
 */
export interface MetaStatistics {
  total_memories_rated: number;
  avg_quality: number;
  expertise_domains: number;
  avg_expertise: number;
}

// ============================================================================
// Direct Operation Functions
// These follow Athena's direct Python import pattern
// @implementation src/athena/meta/operations.py
// ============================================================================

/**
 * Rate a memory on quality, confidence, and usefulness.
 *
 * @param memory_id - Memory ID to rate
 * @param quality - Quality score (0.0-1.0)
 * @param confidence - Confidence score (0.0-1.0)
 * @param usefulness - Usefulness score (0.0-1.0)
 * @returns True if rating was stored
 * @implementation src/athena/meta/operations.py:rate_memory
 */
export async function rate_memory(
  memory_id: string,
  quality?: number,
  confidence?: number,
  usefulness?: number
): Promise<boolean> {
  // In production: from athena.meta.operations import rate_memory
  // return await rate_memory(memory_id, quality, confidence, usefulness)
  throw new Error("Not implemented in TypeScript stub. Use Python directly.");
}

/**
 * Get expertise scores for a topic or all topics.
 *
 * @param topic - Optional topic filter
 * @param limit - Maximum results, default 10
 * @returns Expertise scores
 * @implementation src/athena/meta/operations.py:get_expertise
 */
export async function get_expertise(topic?: string, limit?: number): Promise<Expertise | Record<string, any>> {
  throw new Error("Not implemented in TypeScript stub. Use Python directly.");
}

/**
 * Get quality metrics for a memory.
 *
 * @param memory_id - Memory ID
 * @returns Quality scores or null if not found
 * @implementation src/athena/meta/operations.py:get_memory_quality
 */
export async function get_memory_quality(memory_id: string): Promise<MemoryQuality | null> {
  throw new Error("Not implemented in TypeScript stub. Use Python directly.");
}

/**
 * Get current cognitive load metrics.
 *
 * @returns Cognitive load information
 * @implementation src/athena/meta/operations.py:get_cognitive_load
 */
export async function get_cognitive_load(): Promise<CognitiveLoad> {
  throw new Error("Not implemented in TypeScript stub. Use Python directly.");
}

/**
 * Update cognitive load metrics.
 *
 * @param working_memory_items - Number of items in working memory
 * @param active_tasks - Number of active tasks
 * @param recent_accuracy - Recent accuracy score (0.0-1.0)
 * @returns True if updated successfully
 * @implementation src/athena/meta/operations.py:update_cognitive_load
 */
export async function update_cognitive_load(
  working_memory_items: number,
  active_tasks: number,
  recent_accuracy: number
): Promise<boolean> {
  throw new Error("Not implemented in TypeScript stub. Use Python directly.");
}

/**
 * Get meta-memory statistics.
 *
 * @returns Dictionary with meta-statistics
 * @implementation src/athena/meta/operations.py:get_statistics
 */
export async function get_statistics(): Promise<MetaStatistics> {
  throw new Error("Not implemented in TypeScript stub. Use Python directly.");
}

// ============================================================================
// Operation Metadata (for discovery)
// ============================================================================

export const operations = {
  rate_memory: {
    name: "rate_memory",
    description: "Rate a memory on quality, confidence, and usefulness",
    category: "write" as const,
    parameters: ["memory_id", "quality", "confidence", "usefulness"],
  },
  get_expertise: {
    name: "get_expertise",
    description: "Get expertise scores for a topic or all topics",
    category: "read" as const,
    parameters: ["topic", "limit"],
  },
  get_memory_quality: {
    name: "get_memory_quality",
    description: "Get quality metrics for a memory",
    category: "read" as const,
    parameters: ["memory_id"],
  },
  get_cognitive_load: {
    name: "get_cognitive_load",
    description: "Get current cognitive load metrics",
    category: "read" as const,
    parameters: [],
  },
  update_cognitive_load: {
    name: "update_cognitive_load",
    description: "Update cognitive load metrics",
    category: "write" as const,
    parameters: ["working_memory_items", "active_tasks", "recent_accuracy"],
  },
  get_statistics: {
    name: "get_statistics",
    description: "Get meta-memory statistics",
    category: "read" as const,
    parameters: [],
  },
} as const;

/**
 * Get all available operations
 */
export function getOperations() {
  return Object.values(operations);
}

/**
 * Get a specific operation by name
 */
export function getOperation(name: string) {
  return operations[name as keyof typeof operations];
}

/**
 * Check if operation exists
 */
export function hasOperation(name: string): boolean {
  return name in operations;
}

/**
 * Get all read operations
 */
export function getReadOperations() {
  return getOperations().filter((op) => op.category === "read");
}

/**
 * Get all write operations
 */
export function getWriteOperations() {
  return getOperations().filter((op) => op.category === "write");
}

/**
 * Quick reference for using Athena meta-memory operations:
 *
 * ```python
 * from athena.meta.operations import (
 *   rate_memory, get_expertise, get_memory_quality,
 *   get_cognitive_load, update_cognitive_load, get_statistics
 * )
 *
 * # Rate memories
 * await rate_memory("memory_1", quality=0.8, confidence=0.9)
 *
 * # Track expertise
 * expertise = await get_expertise(topic="Python")
 *
 * # Get quality metrics
 * quality = await get_memory_quality("memory_1")
 *
 * # Monitor cognitive load
 * load = await get_cognitive_load()
 * await update_cognitive_load(5, 2, 0.85)
 *
 * # Get statistics
 * stats = await get_statistics()
 * ```
 *
 * Expertise levels: beginner, intermediate, advanced, expert
 *
 * Quality scores are 0.0-1.0 for:
 * - usefulness_score: How useful the memory is
 * - confidence: How confident we are in the information
 * - relevance_decay: How relevant it remains over time
 */
