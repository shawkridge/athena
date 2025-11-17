/**
 * Semantic Memory Operations - Facts & Knowledge Storage
 *
 * These operations manage the semantic memory layer (Layer 2).
 * Semantic memory stores learned facts and knowledge with vector embeddings.
 * Uses hybrid search: vector similarity + BM25 keyword matching.
 *
 * Agents import directly from: athena.memory.operations
 */

export interface SemanticMemory {
  id: string;
  content: string;
  topics?: string[];
  confidence?: number;
  source?: string;
  timestamp: string;
  usage_count?: number;
}

export interface SearchResult {
  memories: SemanticMemory[];
  query: string;
  total_count: number;
  search_time_ms: number;
}

/**
 * Store a fact in semantic memory
 *
 * Stores learned facts, insights, or knowledge that should be retained.
 * Facts are embedded and indexed for semantic search.
 * Confidence score indicates how certain we are about the fact.
 *
 * @param content - Fact or knowledge to store
 * @param topics - Optional topic keywords for categorization
 * @param confidence - Confidence in the fact 0-1 (default: 0.8)
 * @param source - Source of the knowledge (optional)
 * @returns Fact ID
 *
 * @implementation src/athena/memory/operations.py:store
 *
 * @example
 * ```python
 * from athena.memory.operations import store
 *
 * fact_id = await store(
 *   content="Python's GIL limits true multithreading",
 *   topics=["python", "concurrency"],
 *   confidence=0.95
 * )
 * print(f"Stored fact: {fact_id}")
 * ```
 */
export async function store(
  content: string,
  topics?: string[],
  confidence?: number,
  source?: string
): Promise<string>;

/**
 * Search semantic memory
 *
 * Performs hybrid search combining semantic similarity and keyword matching.
 * Returns most relevant facts ordered by relevance and confidence.
 *
 * @param query - Search query (semantic or keyword)
 * @param limit - Maximum results to return (default: 10)
 * @param min_confidence - Minimum confidence threshold (default: 0.0)
 * @param topics - Optional topic filter
 * @returns Search results with matching facts
 *
 * @implementation src/athena/memory/operations.py:search
 *
 * @example
 * ```python
 * from athena.memory.operations import search
 *
 * results = await search(
 *   query="How does Python handle concurrency?",
 *   limit=5,
 *   min_confidence=0.8
 * )
 * for memory in results.memories:
 *   print(f"{memory['confidence']}: {memory['content']}")
 * ```
 */
export async function search(
  query: string,
  limit?: number,
  min_confidence?: number,
  topics?: string[]
): Promise<SearchResult>;
