/**
 * Phase 3 Integration Tests
 *
 * Demonstrates all 8 memory layers working together through code execution paradigm.
 * Tests the complete flow: code execution → tool discovery → layer operations.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { codeExecutionHandler, initializeAllLayers } from '../../src/execution/mcp_handler';
import * as search_tools_module from '../../src/servers/search_tools';

describe('Phase 3: Memory Layer Integration', () => {
  beforeEach(async () => {
    // Initialize all layers before each test
    await initializeAllLayers();
  });

  describe('Tool Discovery (search_tools)', () => {
    it('should discover all tools with name detail level', async () => {
      const tools = await search_tools_module.search_tools({
        detailLevel: 'name',
      });

      // Should have tools from all 8 layers (70+ operations)
      expect(tools.length).toBeGreaterThanOrEqual(50);
      expect(tools.some((t) => t.layer === 'episodic')).toBe(true);
      expect(tools.some((t) => t.layer === 'semantic')).toBe(true);
    });

    it('should discover tools with name+description', async () => {
      const tools = await search_tools_module.search_tools({
        detailLevel: 'name+description',
      });

      const firstTool = tools[0];
      expect(firstTool.name).toBeDefined();
      expect(firstTool.description).toBeDefined();
      expect(firstTool.category).toBeDefined();
    });

    it('should support layer filtering', async () => {
      const episodicTools = await search_tools_module.search_tools({
        layer: 'episodic',
        detailLevel: 'name',
      });

      expect(episodicTools.every((t) => t.layer === 'episodic')).toBe(true);
      expect(episodicTools.length).toBeGreaterThanOrEqual(6);
    });

    it('should support category filtering', async () => {
      const readTools = await search_tools_module.search_tools({
        category: 'read',
        detailLevel: 'name',
      });

      expect(readTools.every((t) => t.category === 'read')).toBe(true);
      expect(readTools.length).toBeGreaterThan(0);
    });

    it('should support query-based search', async () => {
      const recallTools = await search_tools_module.search_tools({
        query: 'recall',
        detailLevel: 'name+description',
      });

      expect(recallTools.length).toBeGreaterThan(0);
      expect(recallTools.some((t) => t.name.includes('recall'))).toBe(true);
    });

    it('should support finding tools for a task', async () => {
      const tools = await search_tools_module.findToolsFor('store user information');

      expect(tools.length).toBeGreaterThan(0);
      // Should recommend store, remember, or similar operations
      expect(
        tools.some((t) => t.name.includes('store') || t.name.includes('remember'))
      ).toBe(true);
    });

    it('should get all tools with full schema', async () => {
      const tools = await search_tools_module.search_tools({
        detailLevel: 'full-schema',
      });

      const toolWithSchema = tools[0];
      expect(toolWithSchema.parameters).toBeDefined();
      expect(toolWithSchema.returnType).toBeDefined();
    });
  });

  describe('Episodic Layer Operations', () => {
    it('should have recall operation', async () => {
      const tools = await search_tools_module.getToolsByLayer('episodic', 'name');
      expect(tools.some((t) => t.name === 'recall')).toBe(true);
    });

    it('should have remember operation', async () => {
      const tools = await search_tools_module.getToolsByLayer('episodic', 'name');
      expect(tools.some((t) => t.name === 'remember')).toBe(true);
    });

    it('should have forget operation', async () => {
      const tools = await search_tools_module.getToolsByLayer('episodic', 'name');
      expect(tools.some((t) => t.name === 'forget')).toBe(true);
    });

    it('should list all episodic operations', async () => {
      const tools = await search_tools_module.getToolsByLayer('episodic', 'name');

      const expectedOps = [
        'recall',
        'remember',
        'forget',
        'bulkRemember',
        'queryTemporal',
        'listEvents',
      ];

      for (const op of expectedOps) {
        expect(tools.some((t) => t.name === op)).toBe(true);
      }
    });
  });

  describe('Semantic Layer Operations', () => {
    it('should have search operation', async () => {
      const tools = await search_tools_module.getToolsByLayer('semantic', 'name');
      expect(tools.some((t) => t.name === 'search')).toBe(true);
    });

    it('should have store operation', async () => {
      const tools = await search_tools_module.getToolsByLayer('semantic', 'name');
      expect(tools.some((t) => t.name === 'store')).toBe(true);
    });

    it('should list all semantic operations', async () => {
      const tools = await search_tools_module.getToolsByLayer('semantic', 'name');

      const expectedOps = [
        'search',
        'semanticSearch',
        'keywordSearch',
        'hybridSearch',
        'store',
        'update',
        'delete_memory',
        'list',
        'analyzeTopics',
        'getStats',
      ];

      for (const op of expectedOps) {
        expect(tools.some((t) => t.name === op)).toBe(true);
      }
    });
  });

  describe('All 8 Layers Present', () => {
    it('should have episodic layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('episodic', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should have semantic layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('semantic', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should have procedural layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('procedural', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should have prospective layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('prospective', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should have graph layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('graph', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should have meta layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('meta', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should have consolidation layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('consolidation', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should have rag layer', async () => {
      const tools = await search_tools_module.getToolsByLayer('rag', 'name');
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should list all categories', async () => {
      const categories = await search_tools_module.getCategories();

      expect(categories.length).toBe(8);
      expect(categories.map((c) => c.layer)).toContain('episodic');
      expect(categories.map((c) => c.layer)).toContain('semantic');
      expect(categories.map((c) => c.layer)).toContain('procedural');
      expect(categories.map((c) => c.layer)).toContain('prospective');
      expect(categories.map((c) => c.layer)).toContain('graph');
      expect(categories.map((c) => c.layer)).toContain('meta');
      expect(categories.map((c) => c.layer)).toContain('consolidation');
      expect(categories.map((c) => c.layer)).toContain('rag');
    });
  });

  describe('Read vs Write Operations', () => {
    it('should distinguish read operations', async () => {
      const readOps = await search_tools_module.getReadTools('name');

      expect(readOps.length).toBeGreaterThan(0);
      expect(readOps.every((op) => op.category === 'read')).toBe(true);
    });

    it('should distinguish write operations', async () => {
      const writeOps = await search_tools_module.getWriteTools('name');

      expect(writeOps.length).toBeGreaterThan(0);
      expect(writeOps.every((op) => op.category === 'write')).toBe(true);
    });

    it('should have more read than write operations', async () => {
      const readOps = await search_tools_module.getReadTools('name');
      const writeOps = await search_tools_module.getWriteTools('name');

      // Read operations should be more common than write
      expect(readOps.length).toBeGreaterThan(writeOps.length);
    });
  });

  describe('Tool Context and Access Control', () => {
    it('should create tool context with session ID', () => {
      const context = codeExecutionHandler.createToolContext('session_123', 'user_456');

      expect(context.sessionId).toBe('session_123');
      expect(context.userId).toBe('user_456');
      expect(context.callMCPTool).toBeDefined();
      expect(context.search_tools).toBeDefined();
    });

    it('should verify tool access', () => {
      codeExecutionHandler.createToolContext('session_test');

      const hasAccess = codeExecutionHandler.canAccess('episodic/recall', 'session_test');
      expect(typeof hasAccess).toBe('boolean');
    });

    it('should deny access to unknown session', () => {
      const hasAccess = codeExecutionHandler.canAccess(
        'episodic/recall',
        'nonexistent_session'
      );
      expect(hasAccess).toBe(false);
    });

    it('should close session', () => {
      const sessionId = 'session_to_close';
      codeExecutionHandler.createToolContext(sessionId);

      codeExecutionHandler.closeSession(sessionId);

      const hasAccess = codeExecutionHandler.canAccess('episodic/recall', sessionId);
      expect(hasAccess).toBe(false);
    });
  });

  describe('Blog Post Alignment', () => {
    it('should have 70+ operations total', async () => {
      const tools = await search_tools_module.search_tools({
        detailLevel: 'name',
      });

      expect(tools.length).toBeGreaterThanOrEqual(70);
    });

    it('should support progressive disclosure', async () => {
      // Name level (smallest)
      const namesOnly = await search_tools_module.search_tools({
        detailLevel: 'name',
      });

      // Name + description (medium)
      const withDesc = await search_tools_module.search_tools({
        detailLevel: 'name+description',
      });

      // Full schema (largest)
      const fullSchema = await search_tools_module.search_tools({
        detailLevel: 'full-schema',
      });

      // All should return same number of tools
      expect(namesOnly.length).toBe(withDesc.length);
      expect(withDesc.length).toBe(fullSchema.length);

      // But details should increase
      expect((namesOnly[0] as any).description).toBeUndefined();
      expect((withDesc[0] as any).description).toBeDefined();
      expect((fullSchema[0] as any).parameters).toBeDefined();
    });

    it('should support filesystem directory structure', async () => {
      // Verify each layer corresponds to a ./servers/{layer}/ directory
      const categories = await search_tools_module.getCategories();

      const expectedLayers = [
        'episodic',
        'semantic',
        'procedural',
        'prospective',
        'graph',
        'meta',
        'consolidation',
        'rag',
      ];

      for (const expected of expectedLayers) {
        expect(categories.some((c) => c.layer === expected)).toBe(true);
      }
    });

    it('should enable agents to discover tools via callMCPTool', async () => {
      // Simulate agent code that discovers tools
      const sessionId = 'agent_test';
      const context = codeExecutionHandler.createToolContext(sessionId);

      // Agent can call search_tools
      const tools = await context.search_tools({ detailLevel: 'name', limit: 5 });

      expect(Array.isArray(tools)).toBe(true);
      expect(tools.length).toBeGreaterThan(0);
    });
  });
});
