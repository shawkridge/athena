/**
 * Tool Discovery Utility
 *
 * Provides functions for agents to discover available tools and operations
 * with different levels of detail (name-only, with description, or full schema).
 *
 * This implements the blog post's tool discovery pattern, allowing agents to:
 * 1. Query available tools by category or name
 * 2. Get different detail levels for progressive disclosure
 * 3. Inspect tool signatures and parameters
 * 4. Find tools by capability
 *
 * @packageDocumentation
 */

import * as episodic from './episodic/index';
import * as semantic from './semantic/index';
import * as procedural from './procedural/index';
import * as prospective from './prospective/index';
import * as graph from './graph/index';
import * as meta from './meta/index';
import * as consolidation from './consolidation/index';
import * as rag from './rag/index';

/**
 * Tool information at different detail levels
 */
export interface ToolInfo {
  layer: string;
  name: string;
  description?: string;
  category?: 'read' | 'write';
  parameters?: Record<string, { type: string; description?: string; required?: boolean }>;
  returnType?: string;
}

/**
 * Detail level for tool discovery
 */
export type DetailLevel = 'name' | 'name+description' | 'full-schema';

/**
 * Tool category filter
 */
export type ToolCategory = 'read' | 'write' | 'all';

/**
 * All available layers
 */
const LAYERS = {
  episodic: { module: episodic, displayName: 'Episodic Memory' },
  semantic: { module: semantic, displayName: 'Semantic Memory' },
  procedural: { module: procedural, displayName: 'Procedural Memory' },
  prospective: { module: prospective, displayName: 'Prospective Memory' },
  graph: { module: graph, displayName: 'Knowledge Graph' },
  meta: { module: meta, displayName: 'Meta-Memory' },
  consolidation: { module: consolidation, displayName: 'Consolidation' },
  rag: { module: rag, displayName: 'RAG' },
} as const;

/**
 * Search available tools
 *
 * Queries available tools with optional filtering and detail level control.
 * Perfect for agents to discover what they can do.
 *
 * @param options - Search options
 * @returns Array of tool information
 *
 * @example
 * // Get all tools at name level (1KB)
 * const tools = await search_tools({ detailLevel: 'name' });
 *
 * @example
 * // Get write operations in episodic layer
 * const writeOps = await search_tools({
 *   layer: 'episodic',
 *   category: 'write',
 *   detailLevel: 'name+description'
 * });
 *
 * @example
 * // Search for tools matching a query
 * const searchTools = await search_tools({
 *   query: 'recall',
 *   detailLevel: 'full-schema'
 * });
 */
export async function search_tools(options?: {
  detailLevel?: DetailLevel;
  layer?: string;
  category?: ToolCategory;
  query?: string;
}): Promise<ToolInfo[]> {
  const detailLevel = options?.detailLevel ?? 'name+description';
  const layerFilter = options?.layer;
  const categoryFilter = options?.category ?? 'all';
  const queryFilter = options?.query?.toLowerCase();

  const results: ToolInfo[] = [];

  // Iterate through all layers
  for (const [layerName, layerInfo] of Object.entries(LAYERS)) {
    if (layerFilter && layerFilter !== layerName) {
      continue;
    }

    const module = layerInfo.module;

    if (!module.getOperations) {
      continue;
    }

    const operations = module.getOperations();

    for (const op of operations) {
      // Category filter
      if (categoryFilter !== 'all' && op.category !== categoryFilter) {
        continue;
      }

      // Query filter
      if (queryFilter && !op.name.toLowerCase().includes(queryFilter)) {
        continue;
      }

      const tool: ToolInfo = {
        layer: layerName,
        name: op.name,
      };

      // Add details based on detail level
      if (detailLevel === 'name+description' || detailLevel === 'full-schema') {
        tool.description = op.description;
        tool.category = op.category as 'read' | 'write';
      }

      if (detailLevel === 'full-schema') {
        tool.parameters = op.parameters || {};
        tool.returnType = op.returnType || 'unknown';
      }

      results.push(tool);
    }
  }

  return results;
}

/**
 * Get all tools with their full schemas
 *
 * Returns complete information about all available tools.
 * Large payload (~50KB), use selectively.
 *
 * @returns All tools with full schemas
 *
 * @example
 * const allTools = await getAllTools();
 * console.log(`Total tools: ${allTools.length}`);
 */
export async function getAllTools(): Promise<ToolInfo[]> {
  return await search_tools({ detailLevel: 'full-schema' });
}

/**
 * Get tools by layer
 *
 * Returns all tools in a specific memory layer.
 *
 * @param layerName - Layer name (episodic, semantic, etc.)
 * @param detailLevel - Detail level
 * @returns Tools in that layer
 *
 * @example
 * const episodicTools = await getToolsByLayer('episodic', 'name+description');
 */
export async function getToolsByLayer(
  layerName: string,
  detailLevel: DetailLevel = 'name+description'
): Promise<ToolInfo[]> {
  return await search_tools({ layer: layerName, detailLevel });
}

/**
 * Get read-only tools
 *
 * Returns all read operations (safe for exploration, no side effects).
 *
 * @param detailLevel - Detail level
 * @returns All read tools
 *
 * @example
 * const readOps = await getReadTools('name');
 */
export async function getReadTools(detailLevel: DetailLevel = 'name'): Promise<ToolInfo[]> {
  return await search_tools({ category: 'read', detailLevel });
}

/**
 * Get write tools
 *
 * Returns all write operations (modify state).
 *
 * @param detailLevel - Detail level
 * @returns All write tools
 */
export async function getWriteTools(detailLevel: DetailLevel = 'name'): Promise<ToolInfo[]> {
  return await search_tools({ category: 'write', detailLevel });
}

/**
 * Find tools for a specific task
 *
 * Suggests relevant tools based on task description.
 * Uses heuristic matching on tool names and descriptions.
 *
 * @param task - Task description
 * @returns Relevant tools
 *
 * @example
 * const tools = await findToolsFor('store user information');
 */
export async function findToolsFor(task: string): Promise<ToolInfo[]> {
  const lowerTask = task.toLowerCase();
  const keywords = lowerTask.split(/\s+/);

  const allTools = await search_tools({
    detailLevel: 'name+description',
  });

  // Score tools by keyword matching
  const scored = allTools.map((tool) => {
    const toolText = `${tool.name} ${tool.description}`.toLowerCase();
    let score = 0;

    for (const keyword of keywords) {
      if (toolText.includes(keyword)) {
        score++;
      }
    }

    return { tool, score };
  });

  // Return top matches
  return scored
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .map((item) => item.tool);
}

/**
 * Get tool complexity estimate
 *
 * Returns estimated complexity/cost of using a tool.
 *
 * @param toolName - Tool name
 * @returns Complexity estimate
 */
export async function getToolComplexity(
  toolName: string
): Promise<{
  complexity: 'simple' | 'moderate' | 'complex';
  estimatedTime: string;
  requiredContext: string[];
}> {
  const complexityMap: Record<string, string> = {
    // Simple (quick, low context)
    'recall': 'simple',
    'remember': 'simple',
    'search': 'simple',
    'get': 'simple',
    'list': 'simple',

    // Moderate (require some context)
    'forget': 'moderate',
    'update': 'moderate',
    'bulkRemember': 'moderate',
    'consolidate': 'moderate',
    'analyzeTopics': 'moderate',

    // Complex (high context, long computation)
    'reflectiveSearch': 'complex',
    'hybridSearch': 'complex',
    'analyzeEntity': 'complex',
    'findPath': 'complex',
  };

  const complexity = complexityMap[toolName] || 'moderate';

  const timeMap: Record<string, string> = {
    simple: '50-100ms',
    moderate: '100-300ms',
    complex: '300-1000ms',
  };

  const requiredMap: Record<string, string[]> = {
    simple: [],
    moderate: ['access to database'],
    complex: ['access to database', 'embeddings', 'graph index'],
  };

  return {
    complexity: complexity as 'simple' | 'moderate' | 'complex',
    estimatedTime: timeMap[complexity],
    requiredContext: requiredMap[complexity],
  };
}

/**
 * Get available tool categories
 *
 * Returns list of all available memory layers and their tool counts.
 *
 * @returns Category information
 *
 * @example
 * const categories = await getCategories();
 * categories.forEach(cat => {
 *   console.log(`${cat.layer}: ${cat.toolCount} tools`);
 * });
 */
export async function getCategories(): Promise<
  Array<{
    layer: string;
    displayName: string;
    toolCount: number;
    readOps: number;
    writeOps: number;
  }>
> {
  const categories = [];

  for (const [layerName, layerInfo] of Object.entries(LAYERS)) {
    const module = layerInfo.module;

    if (!module.getOperations) {
      continue;
    }

    const operations = module.getOperations();
    const readOps = operations.filter((op) => op.category === 'read').length;
    const writeOps = operations.filter((op) => op.category === 'write').length;

    categories.push({
      layer: layerName,
      displayName: layerInfo.displayName,
      toolCount: operations.length,
      readOps,
      writeOps,
    });
  }

  return categories;
}

/**
 * Get tool quick reference
 *
 * Returns a compact reference for all tools.
 * Perfect for agent context injection.
 *
 * @returns Quick reference string
 *
 * @example
 * const ref = await getQuickReference();
 * // Include in agent prompt
 */
export async function getQuickReference(): Promise<string> {
  const categories = await getCategories();

  let ref = '# Available Tools Quick Reference\n\n';

  for (const cat of categories) {
    ref += `## ${cat.displayName} (${cat.toolCount} tools)\n`;
    ref += `- Read operations: ${cat.readOps}\n`;
    ref += `- Write operations: ${cat.writeOps}\n\n`;
  }

  return ref;
}
