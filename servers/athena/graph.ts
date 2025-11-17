/**
 * Knowledge Graph Operations - Entities & Relations
 *
 * These operations manage the knowledge graph layer (Layer 5).
 * Knowledge graph stores entities (concepts, people, systems) and relationships between them.
 * Supports community detection and relationship path finding.
 *
 * Agents import directly from: athena.graph.operations
 */

export interface Entity {
  id: string;
  name: string;
  entity_type: string; // e.g., "person", "concept", "system"
  description?: string;
  importance: number; // 0-1
  first_mentioned?: string;
  last_mentioned?: string;
  mention_count: number;
  metadata?: Record<string, any>;
}

export interface Relationship {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string; // e.g., "related_to", "depends_on", "is_similar_to"
  strength: number; // 0-1
  description?: string;
  discovered_at: string;
}

export interface Community {
  id: string;
  entities: Entity[];
  internal_density: number;
  size: number;
  description?: string;
}

export interface GraphStatistics {
  total_entities: number;
  total_relationships: number;
  total_communities: number;
  avg_entity_importance: number;
  avg_relationship_strength: number;
  by_entity_type: Record<string, number>;
  by_relation_type: Record<string, number>;
}

/**
 * Add an entity to the knowledge graph
 *
 * Creates a new entity or updates existing one. Entities represent concepts, people,
 * systems, or anything that can be related to other entities.
 *
 * @param name - Entity name
 * @param entity_type - Entity type (e.g., "concept", "person", "system")
 * @param description - Entity description (optional)
 * @param importance - Initial importance 0-1 (default: 0.5)
 * @param metadata - Additional metadata (optional)
 * @returns Entity ID
 *
 * @implementation src/athena/graph/operations.py:add_entity
 *
 * @example
 * ```python
 * from athena.graph.operations import add_entity
 *
 * entity_id = await add_entity(
 *   name="PostgreSQL",
 *   entity_type="database_system",
 *   description="Relational database management system",
 *   importance=0.9
 * )
 * ```
 */
export async function add_entity(
  name: string,
  entity_type: string,
  description?: string,
  importance?: number,
  metadata?: Record<string, any>
): Promise<string>;

/**
 * Add a relationship between two entities
 *
 * Creates a relationship between source and target entities.
 * Relationships are typed and can have strength/weight.
 *
 * @param source_id - Source entity ID
 * @param target_id - Target entity ID
 * @param relation_type - Type of relationship (e.g., "depends_on", "related_to")
 * @param strength - Relationship strength 0-1 (default: 0.5)
 * @param description - Relationship description (optional)
 * @returns Relationship ID
 *
 * @implementation src/athena/graph/operations.py:add_relationship
 */
export async function add_relationship(
  source_id: string,
  target_id: string,
  relation_type: string,
  strength?: number,
  description?: string
): Promise<string>;

/**
 * Find an entity by name
 *
 * @param name - Entity name to search for
 * @returns Entity object or null if not found
 *
 * @implementation src/athena/graph/operations.py:find_entity
 */
export async function find_entity(name: string): Promise<Entity | null>;

/**
 * Search for entities
 *
 * Searches entities by name, description, or type.
 *
 * @param query - Search query
 * @param entity_type - Filter by type (optional)
 * @param limit - Maximum results (default: 20)
 * @returns List of matching entities
 *
 * @implementation src/athena/graph/operations.py:search_entities
 */
export async function search_entities(
  query: string,
  entity_type?: string,
  limit?: number
): Promise<Entity[]>;

/**
 * Find related entities
 *
 * Returns entities directly related to a given entity.
 * Can optionally filter by relationship type.
 *
 * @param entity_id - Starting entity ID
 * @param relation_type - Filter by relationship type (optional)
 * @param limit - Maximum results (default: 20)
 * @returns List of related entities
 *
 * @implementation src/athena/graph/operations.py:find_related
 */
export async function find_related(
  entity_id: string,
  relation_type?: string,
  limit?: number
): Promise<Entity[]>;

/**
 * Get community detections
 *
 * Returns detected communities of closely-related entities.
 *
 * @param min_internal_density - Minimum density threshold 0-1 (default: 0.3)
 * @param limit - Maximum communities (default: 10)
 * @returns List of detected communities
 *
 * @implementation src/athena/graph/operations.py:get_communities
 */
export async function get_communities(
  min_internal_density?: number,
  limit?: number
): Promise<Community[]>;

/**
 * Update entity importance
 *
 * Updates the importance score of an entity based on new information.
 *
 * @param entity_id - Entity identifier
 * @param importance - New importance 0-1
 * @returns Updated entity
 *
 * @implementation src/athena/graph/operations.py:update_entity_importance
 */
export async function update_entity_importance(
  entity_id: string,
  importance: number
): Promise<Entity>;

/**
 * Get knowledge graph statistics
 *
 * @returns Graph-wide statistics
 *
 * @implementation src/athena/graph/operations.py:get_statistics
 */
export async function get_statistics(): Promise<GraphStatistics>;
