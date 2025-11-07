/**
 * Phase 4.3: Query Optimization Engine
 *
 * Analyzes queries and automatically selects optimal execution strategy.
 * Estimates cost, predicts performance, and rewrites for better efficiency.
 */

/**
 * Query analysis result
 */
interface QueryAnalysis {
  complexity: 'simple' | 'moderate' | 'complex';
  estimatedCost: number;
  suggestedStrategy: string;
  optimizations: string[];
  estimatedLatencyMs: number;
  confidence: number;
}

/**
 * Optimized query plan
 */
interface QueryPlan {
  operation: string;
  filters: Array<{
    field: string;
    selectivity: number;  // 0-1, lower = more selective
    index?: string;
  }>;
  limit?: number;
  sort?: {
    field: string;
    direction: 'asc' | 'desc';
  };
  estimatedRows: number;
  estimatedCostMs: number;
  strategy: 'vector' | 'keyword' | 'hybrid' | 'graph' | 'temporal';
}

/**
 * Query Optimizer
 *
 * Analyzes and optimizes queries for better performance
 */
export class QueryOptimizer {
  private costModel = new QueryCostModel();
  private strategySelector = new StrategySelector();
  private queryRewriter = new QueryRewriter();

  /**
   * Analyze a query and provide optimization recommendations
   */
  analyze(query: string, context?: Record<string, unknown>): QueryAnalysis {
    const complexity = this.analyzeComplexity(query);
    const estimatedCost = this.costModel.estimate(query, context);
    const suggestedStrategy = this.strategySelector.select(query, context);
    const optimizations = this.findOptimizations(query, context);
    const estimatedLatencyMs = this.estimateLatency(estimatedCost, suggestedStrategy);

    return {
      complexity,
      estimatedCost,
      suggestedStrategy,
      optimizations,
      estimatedLatencyMs,
      confidence: 0.85
    };
  }

  /**
   * Create an optimized query plan
   */
  createPlan(
    operation: string,
    query: string,
    params?: Record<string, unknown>
  ): QueryPlan {
    const filters = this.extractFilters(query, params);
    const limit = params?.limit as number || 10;
    const sort = (params?.sort as any) || undefined;

    // Sort filters by selectivity (most selective first)
    filters.sort((a, b) => a.selectivity - b.selectivity);

    const strategy = this.selectStrategy(operation, query);
    const estimatedRows = this.estimateRowsReturned(filters, limit);
    const estimatedCostMs = this.costModel.estimatePlan(filters, strategy);

    return {
      operation,
      filters,
      limit,
      sort,
      estimatedRows,
      estimatedCostMs,
      strategy
    };
  }

  /**
   * Rewrite query for better performance
   */
  rewrite(query: string, context?: Record<string, unknown>): string {
    return this.queryRewriter.rewrite(query, context);
  }

  /**
   * Check if query can use index
   */
  canUseIndex(field: string, operation: string): boolean {
    const indexedFields: Record<string, string[]> = {
      'episodic': ['timestamp', 'tags', 'confidence', 'source'],
      'semantic': ['topics', 'confidence', 'usefulness'],
      'graph': ['entityId', 'relationType', 'communityId'],
      'prospective': ['status', 'priority', 'deadline']
    };

    const layer = operation.split('/')[0];
    const fields = indexedFields[layer] || [];
    return fields.includes(field);
  }

  /**
   * Analyze query complexity
   */
  private analyzeComplexity(query: string): 'simple' | 'moderate' | 'complex' {
    const wordCount = query.split(/\s+/).length;
    const hasAnd = /\bAND\b/i.test(query);
    const hasOr = /\bOR\b/i.test(query);
    const hasNot = /\bNOT\b/i.test(query);
    const hasGrouping = /\([^)]+\)/.test(query);

    let score = 0;
    if (wordCount > 10) score++;
    if (hasAnd) score++;
    if (hasOr) score++;
    if (hasNot) score++;
    if (hasGrouping) score++;

    if (score <= 1) return 'simple';
    if (score <= 3) return 'moderate';
    return 'complex';
  }

  /**
   * Find optimization opportunities
   */
  private findOptimizations(query: string, context?: Record<string, unknown>): string[] {
    const optimizations: string[] = [];

    // Check for full-text search opportunities
    if (query.length > 100) {
      optimizations.push('Use semantic search for long queries');
    }

    // Check for boolean search
    if (/\b(AND|OR|NOT)\b/i.test(query)) {
      optimizations.push('Use keyword search for boolean queries');
    }

    // Check for range queries
    if (/\b(between|before|after|from|to)\b/i.test(query)) {
      optimizations.push('Use temporal queries for date ranges');
    }

    // Check for entity queries
    if (/\b(find|get|search|locate)\b/i.test(query)) {
      optimizations.push('Use graph queries for entity relationships');
    }

    // Check for aggregations
    if (/\b(count|sum|avg|max|min)\b/i.test(query)) {
      optimizations.push('Use aggregation pipelines');
    }

    return optimizations;
  }

  /**
   * Estimate latency based on cost and strategy
   */
  private estimateLatency(cost: number, strategy: string): number {
    const baseCosts: Record<string, number> = {
      'vector': 100,      // Vector search slower
      'keyword': 50,      // Keyword faster
      'hybrid': 120,      // Hybrid most expensive
      'graph': 80,        // Graph moderate
      'temporal': 60      // Temporal fast
    };

    const baseCost = baseCosts[strategy] || 100;
    return baseCost + (cost * 0.5);
  }

  /**
   * Extract filters from query
   */
  private extractFilters(
    query: string,
    params?: Record<string, unknown>
  ): Array<{field: string; selectivity: number; index?: string}> {
    const filters: Array<{field: string; selectivity: number; index?: string}> = [];

    // Extract from params
    if (params) {
      if (params.confidence) {
        filters.push({
          field: 'confidence',
          selectivity: 0.3,  // Moderately selective
          index: 'idx_confidence'
        });
      }
      if (params.tags) {
        filters.push({
          field: 'tags',
          selectivity: 0.4,
          index: 'idx_tags'
        });
      }
      if (params.timestamp) {
        filters.push({
          field: 'timestamp',
          selectivity: 0.2,  // Very selective
          index: 'idx_timestamp'
        });
      }
    }

    // Extract from query string
    if (query.includes('confidence')) {
      filters.push({
        field: 'confidence',
        selectivity: 0.3,
        index: 'idx_confidence'
      });
    }
    if (query.includes('tag')) {
      filters.push({
        field: 'tags',
        selectivity: 0.4,
        index: 'idx_tags'
      });
    }
    if (query.includes('time') || query.includes('date')) {
      filters.push({
        field: 'timestamp',
        selectivity: 0.2,
        index: 'idx_timestamp'
      });
    }

    return filters;
  }

  /**
   * Select optimal strategy for operation
   */
  private selectStrategy(
    operation: string,
    query: string
  ): 'vector' | 'keyword' | 'hybrid' | 'graph' | 'temporal' {
    if (operation.includes('temporal') || operation.includes('date')) {
      return 'temporal';
    }
    if (operation.includes('entity') || operation.includes('graph')) {
      return 'graph';
    }
    if (/\b(AND|OR|NOT)\b/i.test(query)) {
      return 'keyword';
    }
    if (query.length > 50) {
      return 'vector';
    }
    return 'hybrid';
  }

  /**
   * Estimate rows returned
   */
  private estimateRowsReturned(
    filters: Array<{field: string; selectivity: number}>,
    limit: number
  ): number {
    // Base estimate: 1000 matching rows
    let estimate = 1000;

    // Apply filter selectivity
    for (const filter of filters) {
      estimate *= (1 - filter.selectivity);
    }

    // Apply limit
    return Math.min(Math.max(estimate, 1), limit);
  }
}

/**
 * Query Cost Model
 *
 * Estimates query execution cost
 */
class QueryCostModel {
  /**
   * Estimate cost of a query
   */
  estimate(query: string, context?: Record<string, unknown>): number {
    let cost = 100;  // Base cost

    // Increase cost for complex queries
    const wordCount = query.split(/\s+/).length;
    cost += wordCount * 5;

    // Increase cost for boolean operations
    if (/\b(AND|OR)\b/i.test(query)) {
      cost += 50;
    }

    // Increase cost for negation
    if (/\bNOT\b/i.test(query)) {
      cost += 100;
    }

    // Account for context parameters
    if (context?.limit) {
      cost += 10;  // Limit has minimal cost
    }

    return cost;
  }

  /**
   * Estimate cost of a query plan
   */
  estimatePlan(
    filters: Array<{field: string; selectivity: number; index?: string}>,
    strategy: string
  ): number {
    let cost = this.baseStrategyCoste(strategy);

    // Add cost for each filter
    for (const filter of filters) {
      if (filter.index) {
        cost += 10;  // Index lookup is cheap
      } else {
        cost += 50;  // Full scan is expensive
      }
    }

    return cost;
  }

  /**
   * Base cost for strategy
   */
  private baseStrategyCoste(strategy: string): number {
    const costs: Record<string, number> = {
      'vector': 150,
      'keyword': 50,
      'hybrid': 180,
      'graph': 100,
      'temporal': 80
    };

    return costs[strategy] || 100;
  }
}

/**
 * Strategy Selector
 *
 * Selects best search strategy for a query
 */
class StrategySelector {
  /**
   * Select best strategy
   */
  select(query: string, context?: Record<string, unknown>): string {
    const wordCount = query.split(/\s+/).length;
    const hasBoolean = /\b(AND|OR|NOT)\b/i.test(query);

    // Short, simple → keyword search
    if (wordCount <= 3 && !hasBoolean) {
      return 'keyword';
    }

    // Long, natural language → vector search
    if (wordCount > 10) {
      return 'vector';
    }

    // Boolean, complex → hybrid
    if (hasBoolean) {
      return 'hybrid';
    }

    // Entity-based → graph
    if (query.includes('entity') || query.includes('relate')) {
      return 'graph';
    }

    // Temporal → temporal
    if (query.includes('time') || query.includes('date')) {
      return 'temporal';
    }

    // Default: hybrid
    return 'hybrid';
  }
}

/**
 * Query Rewriter
 *
 * Rewrites queries for better performance
 */
class QueryRewriter {
  /**
   * Rewrite query
   */
  rewrite(query: string, context?: Record<string, unknown>): string {
    let rewritten = query;

    // Expand abbreviations
    rewritten = rewritten.replace(/\bdb\b/gi, 'database');
    rewritten = rewritten.replace(/\bapi\b/gi, 'application programming interface');

    // Remove redundant words
    rewritten = rewritten.replace(/\b(a|an|the)\b/gi, ' ');

    // Normalize operators
    rewritten = rewritten.replace(/\s+and\s+/gi, ' AND ');
    rewritten = rewritten.replace(/\s+or\s+/gi, ' OR ');

    // Clean up whitespace
    rewritten = rewritten.replace(/\s+/g, ' ').trim();

    return rewritten;
  }
}

/**
 * Create an optimizer instance
 */
export const createOptimizer = () => new QueryOptimizer();

/**
 * Optimize a single query
 */
export function optimizeQuery(query: string, context?: Record<string, unknown>) {
  const optimizer = new QueryOptimizer();
  return {
    analysis: optimizer.analyze(query, context),
    rewritten: optimizer.rewrite(query, context)
  };
}

/**
 * Get query plan
 */
export function getQueryPlan(
  operation: string,
  query: string,
  params?: Record<string, unknown>
) {
  const optimizer = new QueryOptimizer();
  return optimizer.createPlan(operation, query, params);
}
