/**
 * Meta-Memory Operations - Quality & Expertise Tracking
 *
 * These operations manage the meta-memory layer (Layer 6).
 * Meta-memory tracks the quality, confidence, and reliability of memories.
 * Also tracks expertise areas and cognitive load.
 *
 * Agents import directly from: athena.meta.operations
 */

export interface MemoryQuality {
  memory_id: string;
  quality_score: number; // 0-1
  confidence: number; // 0-1
  accuracy: number; // 0-1
  utility: number; // 0-1, how useful is this memory
  last_used?: string;
  usefulness_count: number;
}

export interface Expertise {
  topic: string;
  confidence: number; // 0-1
  knowledge_depth: number; // 0-1
  references_count: number;
  last_updated: string;
  reliability: number; // 0-1
}

export interface CognitiveLoad {
  current_load: number; // 0-100
  capacity: number; // 0-100
  working_memory_items: number;
  max_working_memory: number;
  consolidation_recommended: boolean;
  stress_level: number; // 0-1
}

export interface MetaStatistics {
  avg_memory_quality: number;
  avg_confidence: number;
  expertise_areas: Record<string, number>;
  total_memories_rated: number;
  high_quality_memories: number;
}

/**
 * Rate a memory's quality
 *
 * Updates the quality metrics for a specific memory based on usefulness and accuracy.
 * Higher quality memories are prioritized in retrieval.
 *
 * @param memory_id - Memory to rate
 * @param quality - Quality score 0-1
 * @param confidence - Confidence 0-1
 * @param accuracy - Accuracy 0-1 (optional)
 * @param utility - Utility 0-1 (optional)
 * @returns Updated quality metrics
 *
 * @implementation src/athena/meta/operations.py:rate_memory
 *
 * @example
 * ```python
 * from athena.meta.operations import rate_memory
 *
 * await rate_memory(
 *   memory_id="evt-123",
 *   quality=0.92,
 *   confidence=0.95,
 *   accuracy=0.90
 * )
 * ```
 */
export async function rate_memory(
  memory_id: string,
  quality: number,
  confidence: number,
  accuracy?: number,
  utility?: number
): Promise<MemoryQuality>;

/**
 * Get expertise in a topic
 *
 * Returns expertise metrics for a given topic.
 * Expertise grows through successful use of knowledge in that area.
 *
 * @param topic - Topic to get expertise for
 * @returns Expertise metrics or null if topic unknown
 *
 * @implementation src/athena/meta/operations.py:get_expertise
 */
export async function get_expertise(topic: string): Promise<Expertise | null>;

/**
 * Get overall memory quality metrics
 *
 * Returns aggregate quality scores across all memories.
 *
 * @param min_quality - Filter by minimum quality score (default: 0.0)
 * @param limit - Maximum memories to analyze (default: 1000)
 * @returns Quality metrics
 *
 * @implementation src/athena/meta/operations.py:get_memory_quality
 */
export async function get_memory_quality(
  min_quality?: number,
  limit?: number
): Promise<MemoryQuality[]>;

/**
 * Get current cognitive load
 *
 * Returns assessment of mental load and available capacity.
 * High load triggers consolidation and compression.
 *
 * @returns Cognitive load metrics
 *
 * @implementation src/athena/meta/operations.py:get_cognitive_load
 */
export async function get_cognitive_load(): Promise<CognitiveLoad>;

/**
 * Update cognitive load
 *
 * Manually adjust cognitive load assessment.
 * Used after consolidation or major memory operations.
 *
 * @param current_load - New current load 0-100
 * @param stress_level - Stress level 0-1 (optional)
 * @returns Updated cognitive load
 *
 * @implementation src/athena/meta/operations.py:update_cognitive_load
 */
export async function update_cognitive_load(
  current_load: number,
  stress_level?: number
): Promise<CognitiveLoad>;

/**
 * Get meta-memory statistics
 *
 * @returns Aggregate statistics about memory quality and expertise
 *
 * @implementation src/athena/meta/operations.py:get_statistics
 */
export async function get_statistics(): Promise<MetaStatistics>;
