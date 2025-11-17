/**
 * Consolidation Operations - Pattern Extraction & Compression
 *
 * These operations manage the consolidation layer (Layer 7).
 * Consolidation extracts patterns, procedures, and insights from episodic memories.
 * Uses dual-process: fast statistical clustering + slow LLM validation.
 *
 * Agents import directly from: athena.consolidation.operations
 */

export interface ConsolidationResult {
  patterns_extracted: number;
  procedures_extracted: number;
  episodic_items_compressed: number;
  consolidation_time_ms: number;
  quality_score: number;
  memory_savings_percent: number;
}

export interface ExtractedPattern {
  id: string;
  pattern_type: string; // e.g., "workflow", "decision_rule", "insight"
  description: string;
  confidence: number; // 0-1
  support_count: number; // How many times pattern observed
  derived_from_memories: string[]; // Memory IDs
  actionable_recommendation: string;
}

export interface ConsolidationMetrics {
  total_consolidations: number;
  avg_consolidation_time_ms: number;
  patterns_extracted_total: number;
  procedures_extracted_total: number;
  compression_ratio: number;
  last_consolidation?: string;
  next_recommended?: string;
}

export interface ConsolidationHistoryEntry {
  timestamp: string;
  strategy: string; // "balanced", "aggressive", "conservative"
  patterns_found: number;
  procedures_found: number;
  memory_reduced: number;
  quality_score: number;
}

/**
 * Consolidate memory
 *
 * Runs full consolidation cycle: cluster episodic events, extract patterns,
 * learn procedures, compress memories, update expertise.
 *
 * Uses dual-process (fast statistical + slow LLM validation).
 * Can be run with different strategies.
 *
 * @param strategy - Consolidation strategy: "balanced" (default), "aggressive", "conservative"
 * @param memory_limit - Maximum episodic events to process (default: 1000)
 * @param confidence_threshold - Minimum pattern confidence 0-1 (default: 0.6)
 * @returns Consolidation results
 *
 * @implementation src/athena/consolidation/operations.py:consolidate
 *
 * @example
 * ```python
 * from athena.consolidation.operations import consolidate
 *
 * result = await consolidate(
 *   strategy="balanced",
 *   memory_limit=500,
 *   confidence_threshold=0.7
 * )
 * print(f"Extracted {result['patterns_extracted']} patterns")
 * ```
 */
export async function consolidate(
  strategy?: string,
  memory_limit?: number,
  confidence_threshold?: number
): Promise<ConsolidationResult>;

/**
 * Extract patterns from episodic memory
 *
 * Analyzes episodic events to find recurring patterns.
 * Returns patterns with confidence scores and supporting memories.
 *
 * @param memory_limit - Max events to analyze (default: 500)
 * @param confidence_threshold - Minimum confidence 0-1 (default: 0.6)
 * @param pattern_types - Filter by pattern types (optional)
 * @returns Extracted patterns
 *
 * @implementation src/athena/consolidation/operations.py:extract_patterns
 */
export async function extract_patterns(
  memory_limit?: number,
  confidence_threshold?: number,
  pattern_types?: string[]
): Promise<ExtractedPattern[]>;

/**
 * Extract procedures from consolidation
 *
 * Learns procedures from consolidated patterns and successful task executions.
 *
 * @param min_confidence - Minimum procedure confidence 0-1 (default: 0.7)
 * @param limit - Maximum procedures to extract (default: 50)
 * @returns Count of newly extracted procedures
 *
 * @implementation src/athena/consolidation/operations.py:extract_procedures
 */
export async function extract_procedures(
  min_confidence?: number,
  limit?: number
): Promise<number>;

/**
 * Get consolidation history
 *
 * Returns log of previous consolidation runs.
 *
 * @param limit - Number of entries (default: 20)
 * @returns Historical consolidation records
 *
 * @implementation src/athena/consolidation/operations.py:get_consolidation_history
 */
export async function get_consolidation_history(
  limit?: number
): Promise<ConsolidationHistoryEntry[]>;

/**
 * Get consolidation metrics
 *
 * Returns aggregate metrics about consolidation operations.
 *
 * @returns Consolidation metrics
 *
 * @implementation src/athena/consolidation/operations.py:get_consolidation_metrics
 */
export async function get_consolidation_metrics(): Promise<ConsolidationMetrics>;

/**
 * Get consolidation statistics
 *
 * @returns Overall statistics about consolidation
 *
 * @implementation src/athena/consolidation/operations.py:get_statistics
 */
export async function get_statistics(): Promise<Record<string, any>>;
