/**
 * Knowledge Graph Operations (Layer 5)
 *
 * Functions for managing entities, relationships, and community detection.
 * All operations are available as direct Python async functions via:
 *   from athena.graph.operations import add_entity, find_related, etc.
 *
 * @packageDocumentation
 * @implementation src/athena/graph/operations.py
 */

/**
 * Entity in the knowledge graph
 */
export interface Entity {
  id: number;
  name: string;
  entity_type: 'Project' | 'Phase' | 'Task' | 'File' | 'Function' | 'Concept' | 'Component' | 'Process' | 'Person' | 'Decision' | 'Pattern' | 'Agent' | 'Skill';
  description?: string;
  created_at?: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
  source?: string;
  source_id?: number;
}

/**
 * Relationship between entities
 */
export interface Relation {
  id: number;
  from_entity_id: number;
  to_entity_id: number;
  relation_type: 'contains' | 'depends_on' | 'implements' | 'tests' | 'caused_by' | 'resulted_in' | 'relates_to' | 'active_in' | 'assigned_to' | 'has_skill';
  strength: number;
  confidence: number;
  created_at?: string;
  valid_from?: string;
  valid_until?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Community in the graph (cluster of related entities)
 */
export interface Community {
  id: number;
  members: number[];
  size: number;
  strength: number;
}

/**
 * Graph statistics
 */
export interface GraphStatistics {
  total_entities: number;
  total_relationships: number;
  entity_types: Record<string, number>;
  relationship_types: Record<string, number>;
  avg_importance: number;
}

// ============================================================================
// Direct Operation Functions
// These follow Athena's direct Python import pattern
// @implementation src/athena/graph/operations.py
// ============================================================================

/**
 * Add an entity to the knowledge graph.
 *
 * @param name - Entity name
 * @param entity_type - Type of entity (Project, Phase, Task, File, Function, Concept, Component, Process, Person, Decision, Pattern, Agent, Skill)
 * @param description - Optional description
 * @param metadata - Optional metadata dictionary
 * @returns Entity ID
 * @implementation src/athena/graph/operations.py:add_entity
 */
export async function add_entity(
  name: string,
  entity_type: string,
  description?: string,
  metadata?: Record<string, unknown>
): Promise<number> {
  // In production: from athena.graph.operations import add_entity
  // entity_id = await add_entity(name, entity_type, description, metadata)
  // return entity_id
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

/**
 * Add a relationship between two entities.
 *
 * @param source_id - Source entity ID
 * @param target_id - Target entity ID
 * @param relationship_type - Type of relationship (contains, depends_on, implements, etc.)
 * @param strength - Relationship strength (0.0-1.0), default 0.5
 * @param metadata - Optional metadata dictionary
 * @returns Relationship ID
 * @implementation src/athena/graph/operations.py:add_relationship
 */
export async function add_relationship(
  source_id: string | number,
  target_id: string | number,
  relationship_type: string,
  strength?: number,
  metadata?: Record<string, unknown>
): Promise<number> {
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

/**
 * Find an entity by ID.
 *
 * @param entity_id - Entity ID
 * @returns Entity object or null if not found
 * @implementation src/athena/graph/operations.py:find_entity
 */
export async function find_entity(entity_id: string | number): Promise<Entity | null> {
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

/**
 * Search entities by name or description.
 *
 * @param query - Search query
 * @param entity_type - Optional entity type filter
 * @param limit - Maximum results, default 10
 * @returns List of matching entities
 * @implementation src/athena/graph/operations.py:search_entities
 */
export async function search_entities(
  query: string,
  entity_type?: string,
  limit?: number
): Promise<Entity[]> {
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

/**
 * Find entities related to a given entity.
 *
 * @param entity_id - Source entity ID
 * @param relationship_type - Optional filter by relationship type
 * @param limit - Maximum results, default 10
 * @param depth - Search depth (1 = direct only, 2 = 2 hops, etc.), default 1
 * @returns List of related entities
 * @implementation src/athena/graph/operations.py:find_related
 */
export async function find_related(
  entity_id: string | number,
  relationship_type?: string,
  limit?: number,
  depth?: number
): Promise<Entity[]> {
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

/**
 * Get detected entity communities (clusters).
 *
 * @param limit - Maximum communities to return, default 10
 * @returns List of community summaries
 * @implementation src/athena/graph/operations.py:get_communities
 */
export async function get_communities(limit?: number): Promise<Community[]> {
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

/**
 * Update entity importance score.
 *
 * @param entity_id - Entity ID
 * @param importance - New importance score (0.0-1.0)
 * @returns True if updated successfully
 * @implementation src/athena/graph/operations.py:update_entity_importance
 */
export async function update_entity_importance(
  entity_id: string | number,
  importance: number
): Promise<boolean> {
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

/**
 * Get knowledge graph statistics.
 *
 * @returns Dictionary with graph statistics
 * @implementation src/athena/graph/operations.py:get_statistics
 */
export async function get_statistics(): Promise<GraphStatistics> {
  throw new Error('Not implemented in TypeScript stub. Use Python directly.');
}

// ============================================================================
// Operation Metadata (for discovery)
// ============================================================================

export const operations = {
  add_entity: {
    name: 'add_entity',
    description: 'Add an entity to the knowledge graph',
    category: 'write' as const,
    parameters: ['name', 'entity_type', 'description', 'metadata'],
  },
  add_relationship: {
    name: 'add_relationship',
    description: 'Add a relationship between two entities',
    category: 'write' as const,
    parameters: ['source_id', 'target_id', 'relationship_type', 'strength', 'metadata'],
  },
  find_entity: {
    name: 'find_entity',
    description: 'Find an entity by ID',
    category: 'read' as const,
    parameters: ['entity_id'],
  },
  search_entities: {
    name: 'search_entities',
    description: 'Search entities by name or description',
    category: 'read' as const,
    parameters: ['query', 'entity_type', 'limit'],
  },
  find_related: {
    name: 'find_related',
    description: 'Find entities related to a given entity',
    category: 'read' as const,
    parameters: ['entity_id', 'relationship_type', 'limit', 'depth'],
  },
  get_communities: {
    name: 'get_communities',
    description: 'Get detected entity communities (clusters)',
    category: 'read' as const,
    parameters: ['limit'],
  },
  update_entity_importance: {
    name: 'update_entity_importance',
    description: 'Update entity importance score',
    category: 'write' as const,
    parameters: ['entity_id', 'importance'],
  },
  get_statistics: {
    name: 'get_statistics',
    description: 'Get knowledge graph statistics',
    category: 'read' as const,
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
  return getOperations().filter((op) => op.category === 'read');
}

/**
 * Get all write operations
 */
export function getWriteOperations() {
  return getOperations().filter((op) => op.category === 'write');
}

/**
 * Quick reference for using Athena graph operations:
 *
 * ```python
 * from athena.graph.operations import add_entity, find_related, search_entities
 *
 * # Create entities
 * python_id = await add_entity("Python", "Concept")
 * programming_id = await add_entity("Programming", "Concept")
 *
 * # Create relationships
 * rel_id = await add_relationship(python_id, programming_id, "relates_to")
 *
 * # Search and navigate
 * results = await search_entities("Python")
 * related = await find_related(python_id, limit=10)
 * communities = await get_communities(limit=5)
 *
 * # Statistics
 * stats = await get_statistics()
 * ```
 *
 * Valid entity types:
 *   Project, Phase, Task, File, Function, Concept, Component,
 *   Process, Person, Decision, Pattern, Agent, Skill
 *
 * Valid relationship types:
 *   contains, depends_on, implements, tests, caused_by, resulted_in,
 *   relates_to, active_in, assigned_to, has_skill
 */
