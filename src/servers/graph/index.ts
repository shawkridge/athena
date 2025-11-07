/**
 * Knowledge Graph Operations
 *
 * Functions for managing entities, relationships, and communities.
 *
 * @packageDocumentation
 */

export interface Entity {
  id: string;
  name: string;
  type: string;
  description: string;
  confidence: number;
  attributes: Record<string, unknown>;
}

export interface Relationship {
  id: string;
  source: string;
  target: string;
  type: string;
  strength: number;
  metadata: Record<string, unknown>;
}

export interface Community {
  id: string;
  entities: string[];
  cohesion: number;
  size: number;
}

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Search entities
 */
export async function searchEntities(query: string, limit: number = 10): Promise<Entity[]> {
  return (await callMCPTool('graph/searchEntities', {
    query,
    limit,
  })) as Entity[];
}

/**
 * Get entity by ID
 */
export async function getEntity(id: string): Promise<Entity | null> {
  return (await callMCPTool('graph/getEntity', {
    id,
  })) as Entity | null;
}

/**
 * Get relationships for an entity
 */
export async function getRelationships(
  entityId: string,
  type?: string,
  limit: number = 20
): Promise<Relationship[]> {
  return (await callMCPTool('graph/getRelationships', {
    entityId,
    type,
    limit,
  })) as Relationship[];
}

/**
 * Find communities in the graph
 */
export async function getCommunities(level?: number): Promise<Community[]> {
  return (await callMCPTool('graph/getCommunities', {
    level: level ?? 1,
  })) as Community[];
}

/**
 * Search relationships
 */
export async function searchRelationships(
  query: string,
  limit: number = 20
): Promise<Relationship[]> {
  return (await callMCPTool('graph/searchRelationships', {
    query,
    limit,
  })) as Relationship[];
}

/**
 * Analyze entity connections
 */
export async function analyzeEntity(id: string): Promise<{
  entity: Entity;
  relatedEntities: Entity[];
  relationshipCount: number;
  communityId: string;
  centrality: number;
}> {
  return (await callMCPTool('graph/analyzeEntity', {
    id,
  })) as {
    entity: Entity;
    relatedEntities: Entity[];
    relationshipCount: number;
    communityId: string;
    centrality: number;
  };
}

/**
 * Find shortest path between entities
 */
export async function findPath(sourceId: string, targetId: string): Promise<string[]> {
  const result = (await callMCPTool('graph/findPath', {
    sourceId,
    targetId,
  })) as { path: string[] };

  return result.path;
}

/**
 * Create an entity
 */
export async function createEntity(
  name: string,
  type: string,
  description?: string
): Promise<string> {
  const result = (await callMCPTool('graph/createEntity', {
    name,
    type,
    description,
  })) as { id: string };

  return result.id;
}

/**
 * Create a relationship
 */
export async function createRelationship(
  sourceId: string,
  targetId: string,
  type: string,
  strength?: number
): Promise<string> {
  const result = (await callMCPTool('graph/createRelationship', {
    sourceId,
    targetId,
    type,
    strength: strength ?? 0.5,
  })) as { id: string };

  return result.id;
}

export const operations = {
  searchEntities: {
    name: 'searchEntities',
    description: 'Search for entities',
    category: 'read',
  },
  getEntity: { name: 'getEntity', description: 'Get entity by ID', category: 'read' },
  getRelationships: {
    name: 'getRelationships',
    description: 'Get relationships for entity',
    category: 'read',
  },
  getCommunities: {
    name: 'getCommunities',
    description: 'Find communities in graph',
    category: 'read',
  },
  searchRelationships: {
    name: 'searchRelationships',
    description: 'Search relationships',
    category: 'read',
  },
  analyzeEntity: {
    name: 'analyzeEntity',
    description: 'Analyze entity connections',
    category: 'read',
  },
  findPath: { name: 'findPath', description: 'Find path between entities', category: 'read' },
  createEntity: { name: 'createEntity', description: 'Create entity', category: 'write' },
  createRelationship: {
    name: 'createRelationship',
    description: 'Create relationship',
    category: 'write',
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
