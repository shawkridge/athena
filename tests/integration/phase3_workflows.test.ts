/**
 * Phase 3 Workflow Integration Tests
 *
 * Tests for complete cross-layer workflows demonstrating how agents
 * use multiple memory layers together through code execution.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { codeExecutionHandler, initializeAllLayers } from '../../src/execution/mcp_handler';
import * as search_tools_module from '../../src/servers/search_tools';

describe('Phase 3: Cross-Layer Workflows', () => {
  beforeEach(async () => {
    await initializeAllLayers();
  });

  describe('Workflow 1: Learn from Experience', () => {
    it('should support episodic → semantic → procedural workflow', async () => {
      const sessionId = 'workflow_learn_test';
      codeExecutionHandler.createToolContext(sessionId);

      // Step 1: Agent stores episodic memory (event)
      const episodicTools = await search_tools_module.getToolsByLayer('episodic', 'name');
      expect(episodicTools.some((t) => t.name === 'remember')).toBe(true);

      // Step 2: Agent consolidates to semantic memory
      const semanticTools = await search_tools_module.getToolsByLayer('semantic', 'name');
      expect(semanticTools.some((t) => t.name === 'store')).toBe(true);

      // Step 3: Agent extracts procedure
      const proceduralTools = await search_tools_module.getToolsByLayer('procedural', 'name');
      expect(proceduralTools.some((t) => t.name === 'extract')).toBe(true);

      // All three layers available in same session
      const tools = await search_tools_module.search_tools();
      const hasEpisodic = tools.some((t) => t.layer === 'episodic');
      const hasSemantic = tools.some((t) => t.layer === 'semantic');
      const hasProcedural = tools.some((t) => t.layer === 'procedural');

      expect(hasEpisodic && hasSemantic && hasProcedural).toBe(true);
    });

    it('should support episodic events flowing to consolidation', async () => {
      const episodicTools = await search_tools_module.getToolsByLayer('episodic', 'name');
      const consolidationTools = await search_tools_module.getToolsByLayer('consolidation', 'name');

      expect(episodicTools.length).toBeGreaterThan(0);
      expect(consolidationTools.length).toBeGreaterThan(0);

      // Consolidation has access to episodic data
      const consolidateOp = consolidationTools.find((t) => t.name === 'consolidate');
      expect(consolidateOp).toBeDefined();
    });
  });

  describe('Workflow 2: Task Management with Context', () => {
    it('should support prospective + episodic + meta workflow', async () => {
      const prospectiveTools = await search_tools_module.getToolsByLayer('prospective', 'name');
      const episodicTools = await search_tools_module.getToolsByLayer('episodic', 'name');
      const metaTools = await search_tools_module.getToolsByLayer('meta', 'name');

      // Create task (prospective)
      expect(prospectiveTools.some((t) => t.name === 'createTask')).toBe(true);

      // Record context (episodic)
      expect(episodicTools.some((t) => t.name === 'remember')).toBe(true);

      // Check health (meta)
      expect(metaTools.some((t) => t.name === 'memoryHealth')).toBe(true);

      // All available together
      const allTools = await search_tools_module.search_tools();
      expect(allTools.some((t) => t.layer === 'prospective')).toBe(true);
      expect(allTools.some((t) => t.layer === 'episodic')).toBe(true);
      expect(allTools.some((t) => t.layer === 'meta')).toBe(true);
    });

    it('should support task completion tracking', async () => {
      const prospectiveTools = await search_tools_module.getToolsByLayer('prospective', 'name+description');

      const createTask = prospectiveTools.find((t) => t.name === 'createTask');
      const updateTask = prospectiveTools.find((t) => t.name === 'updateTask');
      const completeTask = prospectiveTools.find((t) => t.name === 'completeTask');

      expect(createTask?.description).toBeDefined();
      expect(updateTask?.description).toBeDefined();
      expect(completeTask?.description).toBeDefined();
    });
  });

  describe('Workflow 3: Knowledge Discovery', () => {
    it('should support semantic → graph → rag workflow', async () => {
      const semanticTools = await search_tools_module.getToolsByLayer('semantic', 'name');
      const graphTools = await search_tools_module.getToolsByLayer('graph', 'name');
      const ragTools = await search_tools_module.getToolsByLayer('rag', 'name');

      // Search semantic memory
      expect(semanticTools.some((t) => t.name === 'search')).toBe(true);

      // Analyze relationships
      expect(graphTools.some((t) => t.name === 'analyzeEntity')).toBe(true);

      // Retrieve with RAG
      expect(ragTools.some((t) => t.name === 'retrieve')).toBe(true);

      // All available in knowledge discovery workflow
      const allTools = await search_tools_module.search_tools();
      const hasSemanticSearch = allTools.some((t) => t.layer === 'semantic' && t.name === 'search');
      const hasGraphAnalyze = allTools.some((t) => t.layer === 'graph' && t.name === 'analyzeEntity');
      const hasRagRetrieve = allTools.some((t) => t.layer === 'rag' && t.name === 'retrieve');

      expect(hasSemanticSearch && hasGraphAnalyze && hasRagRetrieve).toBe(true);
    });

    it('should support multi-strategy search (semantic + keyword + vector)', async () => {
      const ragTools = await search_tools_module.getToolsByLayer('rag', 'name+description');

      const semanticSearch = ragTools.find((t) => t.name === 'semanticSearch');
      const keywordSearch = ragTools.find((t) => t.name === 'keywordSearch');
      const hybridSearch = ragTools.find((t) => t.name === 'hybridSearch');

      expect(semanticSearch).toBeDefined();
      expect(keywordSearch).toBeDefined();
      expect(hybridSearch).toBeDefined();

      // All three strategies should be available
      expect(semanticSearch?.description).toContain('semantic');
      expect(keywordSearch?.description).toContain('keyword');
      expect(hybridSearch?.description).toContain('hybrid');
    });
  });

  describe('Workflow 4: Memory Health Monitoring', () => {
    it('should support meta layer monitoring of all layers', async () => {
      const metaTools = await search_tools_module.getToolsByLayer('meta', 'name');

      const health = metaTools.find((t) => t.name === 'memoryHealth');
      const expertise = metaTools.find((t) => t.name === 'getExpertise');
      const load = metaTools.find((t) => t.name === 'getCognitiveLoad');
      const quality = metaTools.find((t) => t.name === 'getQualityMetrics');

      expect(health).toBeDefined();
      expect(expertise).toBeDefined();
      expect(load).toBeDefined();
      expect(quality).toBeDefined();

      // Meta layer has 9 operations
      expect(metaTools.length).toBe(9);
    });

    it('should support attention and quality tracking', async () => {
      const metaTools = await search_tools_module.getToolsByLayer('meta', 'name');

      const attentionOps = metaTools.filter((t) => t.name.includes('Attention'));
      const qualityOps = metaTools.filter((t) => t.name.includes('Quality'));
      const statsOps = metaTools.filter((t) => t.name.includes('Stats'));

      expect(attentionOps.length).toBeGreaterThan(0);
      expect(qualityOps.length).toBeGreaterThan(0);
      expect(statsOps.length).toBeGreaterThan(0);
    });
  });

  describe('Workflow 5: Consolidation Cycle', () => {
    it('should support consolidation workflow', async () => {
      const consolidationTools = await search_tools_module.getToolsByLayer('consolidation', 'name');

      const consolidate = consolidationTools.find((t) => t.name === 'consolidate');
      const patterns = consolidationTools.find((t) => t.name === 'analyzePatterns');
      const status = consolidationTools.find((t) => t.name === 'getStatus');
      const history = consolidationTools.find((t) => t.name === 'getHistory');

      expect(consolidate).toBeDefined();
      expect(patterns).toBeDefined();
      expect(status).toBeDefined();
      expect(history).toBeDefined();

      // All consolidation operations available
      expect(consolidationTools.length).toBe(7);
    });

    it('should support consolidation strategy configuration', async () => {
      const consolidationTools = await search_tools_module.getToolsByLayer(
        'consolidation',
        'name+description'
      );

      const configStrategy = consolidationTools.find((t) => t.name === 'configureStrategy');
      expect(configStrategy).toBeDefined();
      expect(configStrategy?.description).toContain('strategy');
    });
  });

  describe('Tool Composition Patterns', () => {
    it('should support chaining read operations', async () => {
      const allTools = await search_tools_module.search_tools({
        category: 'read',
        detailLevel: 'name',
      });

      // Should have many read operations
      expect(allTools.length).toBeGreaterThan(40);

      // Read operations from multiple layers
      const episodicReads = allTools.filter((t) => t.layer === 'episodic');
      const semanticReads = allTools.filter((t) => t.layer === 'semantic');
      const graphReads = allTools.filter((t) => t.layer === 'graph');

      expect(episodicReads.length).toBeGreaterThan(0);
      expect(semanticReads.length).toBeGreaterThan(0);
      expect(graphReads.length).toBeGreaterThan(0);
    });

    it('should support write operations for data modification', async () => {
      const allTools = await search_tools_module.search_tools({
        category: 'write',
        detailLevel: 'name',
      });

      // Should have write operations
      expect(allTools.length).toBeGreaterThan(10);

      // Write operations across layers
      const episodicWrites = allTools.filter((t) => t.layer === 'episodic');
      const semanticWrites = allTools.filter((t) => t.layer === 'semantic');
      const prospectiveWrites = allTools.filter((t) => t.layer === 'prospective');

      expect(episodicWrites.length).toBeGreaterThan(0);
      expect(semanticWrites.length).toBeGreaterThan(0);
      expect(prospectiveWrites.length).toBeGreaterThan(0);
    });

    it('should support mixed read-write workflows', async () => {
      const readTools = await search_tools_module.getReadTools('name');
      const writeTools = await search_tools_module.getWriteTools('name');

      // Both available for flexible workflows
      expect(readTools.length).toBeGreaterThan(0);
      expect(writeTools.length).toBeGreaterThan(0);

      // Read operations should outnumber write
      expect(readTools.length).toBeGreaterThan(writeTools.length);
    });
  });

  describe('Error Scenarios', () => {
    it('should gracefully handle invalid session', async () => {
      const canAccess = codeExecutionHandler.canAccess('episodic/recall', 'invalid_session');
      expect(canAccess).toBe(false);
    });

    it('should support session isolation', async () => {
      const session1 = 'isolated_session_1';
      const session2 = 'isolated_session_2';

      codeExecutionHandler.createToolContext(session1);
      codeExecutionHandler.createToolContext(session2);

      // Both sessions have independent tool access
      expect(codeExecutionHandler.canAccess('episodic/recall', session1)).toBe(true);
      expect(codeExecutionHandler.canAccess('episodic/recall', session2)).toBe(true);

      // Close one session
      codeExecutionHandler.closeSession(session1);

      // Session 1 no longer has access
      expect(codeExecutionHandler.canAccess('episodic/recall', session1)).toBe(false);

      // Session 2 still has access
      expect(codeExecutionHandler.canAccess('episodic/recall', session2)).toBe(true);

      // Clean up
      codeExecutionHandler.closeSession(session2);
    });

    it('should track multiple concurrent sessions', async () => {
      const sessions = ['concurrent_1', 'concurrent_2', 'concurrent_3'];

      for (const sessionId of sessions) {
        codeExecutionHandler.createToolContext(sessionId);
        expect(codeExecutionHandler.canAccess('semantic/search', sessionId)).toBe(true);
      }

      // All sessions independently valid
      for (const sessionId of sessions) {
        expect(codeExecutionHandler.canAccess('episodic/recall', sessionId)).toBe(true);
      }

      // Clean up
      for (const sessionId of sessions) {
        codeExecutionHandler.closeSession(sessionId);
      }
    });
  });

  describe('Performance Characteristics', () => {
    it('should perform tool discovery in reasonable time', async () => {
      const start = performance.now();

      const tools = await search_tools_module.search_tools({
        detailLevel: 'name',
      });

      const elapsed = performance.now() - start;

      // Should be very fast for name-only discovery
      expect(elapsed).toBeLessThan(100); // Less than 100ms
      expect(tools.length).toBeGreaterThan(0);
    });

    it('should handle large detail levels efficiently', async () => {
      const start = performance.now();

      const tools = await search_tools_module.search_tools({
        detailLevel: 'full-schema',
      });

      const elapsed = performance.now() - start;

      // Full schema should still be relatively fast
      expect(elapsed).toBeLessThan(500); // Less than 500ms
      expect(tools.length).toBeGreaterThan(0);

      // Verify full schema includes parameters
      const toolWithSchema = tools[0];
      expect(toolWithSchema.parameters).toBeDefined();
    });

    it('should filter operations efficiently', async () => {
      const start = performance.now();

      const readOps = await search_tools_module.getReadTools('name');

      const elapsed = performance.now() - start;

      // Filtering should be fast
      expect(elapsed).toBeLessThan(100);
      expect(readOps.every((op) => op.category === 'read')).toBe(true);
    });

    it('should support task-based discovery efficiently', async () => {
      const start = performance.now();

      const tools = await search_tools_module.findToolsFor('store user information');

      const elapsed = performance.now() - start;

      // Task-based discovery should be reasonably fast
      expect(elapsed).toBeLessThan(200);
      expect(tools.length).toBeGreaterThan(0);
    });
  });
});
