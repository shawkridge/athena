/**
 * Semantic Memory: Store, Update, and Delete Operations
 *
 * Manage semantic memories (knowledge representation)
 */

import type { StoreInput, StoreResult, UpdateInput, DeleteInput, DeleteResult } from './types';

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Store a new semantic memory
 *
 * Adds knowledge/facts to semantic memory with topics and embeddings.
 * Semantic memory is for general knowledge, not time-bound events.
 *
 * @param content - Knowledge content to store
 * @param topics - Topics for categorization
 * @param confidence - Confidence in correctness (0-1)
 * @returns Memory ID
 *
 * @example
 * const id = await store(
 *   'PostgreSQL VACUUM must be run regularly to prevent table bloat',
 *   ['database', 'postgresql', 'maintenance'],
 *   0.95
 * );
 */
export async function store(
  content: string,
  topics?: string[],
  confidence?: number
): Promise<string> {
  const result = (await callMCPTool('semantic/store', {
    content,
    topics: topics ?? [],
    confidence: confidence ?? 0.8,
  })) as StoreResult;

  return result.id;
}

/**
 * Store with full options
 *
 * Provides access to all store parameters.
 *
 * @param options - Store input options
 * @returns Memory ID
 */
export async function storeWithOptions(options: StoreInput): Promise<string> {
  const result = (await callMCPTool('semantic/store', {
    content: options.content,
    topics: options.topics ?? [],
    embedding: options.embedding,
    confidence: options.confidence ?? 0.8,
    metadata: options.metadata,
  })) as StoreResult;

  return result.id;
}

/**
 * Store a fact
 *
 * Specialized version for storing factual knowledge.
 *
 * @param fact - Factual statement
 * @param source - Source of the fact
 * @param confidence - Confidence in accuracy (0-1)
 * @returns Memory ID
 *
 * @example
 * const id = await storeFact(
 *   'The Earth orbits the Sun',
 *   'scientific consensus',
 *   0.99
 * );
 */
export async function storeFact(
  fact: string,
  source: string,
  confidence: number = 0.9
): Promise<string> {
  return await store(fact, ['fact', 'verified'], confidence);
}

/**
 * Store a principle or rule
 *
 * Store general principles, rules, or best practices.
 *
 * @param principle - The principle/rule
 * @param domain - Domain it applies to
 * @param examples - Example applications
 * @returns Memory ID
 *
 * @example
 * const id = await storePrinciple(
 *   'Always validate user input before processing',
 *   'security',
 *   ['SQL injection prevention', 'XSS prevention']
 * );
 */
export async function storePrinciple(
  principle: string,
  domain: string,
  examples?: string[]
): Promise<string> {
  return await store(principle, ['principle', domain], 0.95);
}

/**
 * Store a concept with definition
 *
 * Store conceptual knowledge with structured definition.
 *
 * @param concept - Concept name
 * @param definition - What it means
 * @param relatedConcepts - Related concepts
 * @returns Memory ID
 */
export async function storeConcept(
  concept: string,
  definition: string,
  relatedConcepts?: string[]
): Promise<string> {
  return await store(
    `${concept}: ${definition}`,
    ['concept', concept.toLowerCase(), ...(relatedConcepts ?? [])],
    0.85
  );
}

/**
 * Update an existing semantic memory
 *
 * Modifies content, topics, or confidence of existing memory.
 *
 * @param id - Memory ID
 * @param content - New content (optional)
 * @param topics - New topics (optional)
 * @param confidence - New confidence (optional)
 * @returns Success indicator
 *
 * @example
 * await update('mem_123', 'Updated fact', ['updated-topic']);
 */
export async function update(
  id: string,
  content?: string,
  topics?: string[],
  confidence?: number
): Promise<boolean> {
  const result = (await callMCPTool('semantic/update', {
    id,
    content,
    topics,
    confidence,
  })) as { success: boolean };

  return result.success;
}

/**
 * Update with full options
 *
 * @param options - Update input options
 * @returns Success indicator
 */
export async function updateWithOptions(options: UpdateInput): Promise<boolean> {
  const result = (await callMCPTool('semantic/update', {
    id: options.id,
    content: options.content,
    topics: options.topics,
    confidence: options.confidence,
    embedding: options.embedding,
  })) as { success: boolean };

  return result.success;
}

/**
 * Delete a semantic memory
 *
 * Removes a memory from semantic storage.
 *
 * @param id - Memory ID
 * @returns Success indicator
 *
 * @example
 * await delete_memory('mem_123');
 */
export async function delete_memory(id: string): Promise<number> {
  const result = (await callMCPTool('semantic/delete', {
    id,
  })) as DeleteResult;

  return result.deleted;
}

/**
 * Delete multiple memories
 *
 * @param ids - Memory IDs to delete
 * @returns Count of deleted memories
 */
export async function deleteMultiple(ids: string[]): Promise<number> {
  const result = (await callMCPTool('semantic/delete', {
    ids,
  })) as DeleteResult;

  return result.deleted;
}

/**
 * Delete memories with specific topics
 *
 * @param topics - Topics to match
 * @returns Count of deleted memories
 */
export async function deleteByTopics(topics: string[]): Promise<number> {
  const result = (await callMCPTool('semantic/delete', {
    withTopics: topics,
  })) as DeleteResult;

  return result.deleted;
}

/**
 * Delete old memories
 *
 * @param olderThan - Timestamp cutoff
 * @returns Count of deleted memories
 */
export async function deleteOlderThan(olderThan: number): Promise<number> {
  const result = (await callMCPTool('semantic/delete', {
    olderThan,
  })) as DeleteResult;

  return result.deleted;
}

/**
 * Delete with full options
 *
 * @param options - Delete options
 * @returns Count of deleted memories
 */
export async function deleteWithOptions(options: DeleteInput): Promise<number> {
  const result = (await callMCPTool('semantic/delete', {
    id: options.id,
    ids: options.ids,
    olderThan: options.olderThan,
    withTopics: options.withTopic,
  })) as DeleteResult;

  return result.deleted;
}

/**
 * Clear all low-confidence memories
 *
 * Removes memories below confidence threshold.
 *
 * @param threshold - Confidence threshold (0-1)
 * @returns Count of deleted memories
 */
export async function purgeLowConfidence(threshold: number = 0.3): Promise<number> {
  const result = (await callMCPTool('semantic/delete', {
    lowConfidenceThreshold: threshold,
  })) as DeleteResult;

  return result.deleted;
}

/**
 * Consolidate memories (deduplicate and merge)
 *
 * Finds and merges similar memories.
 *
 * @param similarityThreshold - Threshold for considering memories similar
 * @returns Count of consolidated memories
 */
export async function consolidate(similarityThreshold: number = 0.85): Promise<number> {
  const result = (await callMCPTool('semantic/consolidate', {
    similarityThreshold,
  })) as { consolidated: number };

  return result.consolidated;
}
