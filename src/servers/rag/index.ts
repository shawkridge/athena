/**
 * RAG (Retrieval-Augmented Generation) Operations
 *
 * Functions for advanced semantic search, retrieval, and synthesis.
 *
 * @packageDocumentation
 */

export interface RetrievedContext {
  source: string;
  content: string;
  relevance: number;
  timestamp: number;
}

export interface HybridRetrievalResult {
  results: RetrievedContext[];
  synthesisPrompt?: string;
  totalRelevance: number;
}

declare const callMCPTool: (operation: string, params: unknown) => Promise<unknown>;

/**
 * Retrieve relevant context
 */
export async function retrieve(
  query: string,
  limit: number = 5,
  strategy?: string
): Promise<RetrievedContext[]> {
  const result = (await callMCPTool('rag/retrieve', {
    query,
    limit,
    strategy: strategy ?? 'hybrid',
  })) as HybridRetrievalResult;

  return result.results;
}

/**
 * Semantic search with RAG
 */
export async function search(
  query: string,
  limit: number = 10,
  useReranking?: boolean
): Promise<RetrievedContext[]> {
  const result = (await callMCPTool('rag/search', {
    query,
    limit,
    useReranking: useReranking ?? true,
  })) as HybridRetrievalResult;

  return result.results;
}

/**
 * Hybrid search across all memory layers
 */
export async function hybridSearch(
  query: string,
  limit: number = 10,
  weights?: Record<string, number>
): Promise<RetrievedContext[]> {
  const result = (await callMCPTool('rag/hybridSearch', {
    query,
    limit,
    weights: weights ?? {
      episodic: 0.3,
      semantic: 0.4,
      graph: 0.2,
      procedural: 0.1,
    },
  })) as HybridRetrievalResult;

  return result.results;
}

/**
 * Semantic search
 */
export async function semanticSearch(
  query: string,
  limit: number = 10
): Promise<RetrievedContext[]> {
  const result = (await callMCPTool('rag/semanticSearch', {
    query,
    limit,
  })) as HybridRetrievalResult;

  return result.results;
}

/**
 * BM25 keyword search
 */
export async function bm25Search(
  query: string,
  limit: number = 10
): Promise<RetrievedContext[]> {
  const result = (await callMCPTool('rag/bm25Search', {
    query,
    limit,
  })) as HybridRetrievalResult;

  return result.results;
}

/**
 * Reflective search (iterative query refinement)
 */
export async function reflectiveSearch(
  query: string,
  iterations?: number,
  limit?: number
): Promise<RetrievedContext[]> {
  const result = (await callMCPTool('rag/reflectiveSearch', {
    query,
    iterations: iterations ?? 2,
    limit: limit ?? 10,
  })) as HybridRetrievalResult;

  return result.results;
}

/**
 * Query expansion (HyDE - Hypothetical Document Embeddings)
 */
export async function queryExpansion(query: string): Promise<string[]> {
  const result = (await callMCPTool('rag/queryExpansion', {
    query,
  })) as { expandedQueries: string[] };

  return result.expandedQueries;
}

/**
 * Get synthesis prompt from retrieved context
 */
export async function getSynthesisPrompt(
  query: string,
  context?: RetrievedContext[]
): Promise<string> {
  const result = (await callMCPTool('rag/getSynthesisPrompt', {
    query,
    context,
  })) as { prompt: string };

  return result.prompt;
}

/**
 * Retrieve with reranking
 */
export async function retrieveWithReranking(
  query: string,
  limit: number = 5
): Promise<RetrievedContext[]> {
  const result = (await callMCPTool('rag/retrieveWithReranking', {
    query,
    limit,
  })) as HybridRetrievalResult;

  return result.results;
}

/**
 * Get retrieval statistics
 */
export async function getStats(): Promise<{
  totalQueries: number;
  averageLatency: number;
  averageRelevance: number;
  strategyUsage: Record<string, number>;
}> {
  return (await callMCPTool('rag/getStats', {})) as {
    totalQueries: number;
    averageLatency: number;
    averageRelevance: number;
    strategyUsage: Record<string, number>;
  };
}

export const operations = {
  retrieve: { name: 'retrieve', description: 'Retrieve relevant context', category: 'read' },
  search: { name: 'search', description: 'Search with RAG', category: 'read' },
  hybridSearch: { name: 'hybridSearch', description: 'Hybrid search', category: 'read' },
  semanticSearch: {
    name: 'semanticSearch',
    description: 'Semantic search',
    category: 'read',
  },
  bm25Search: { name: 'bm25Search', description: 'BM25 search', category: 'read' },
  reflectiveSearch: {
    name: 'reflectiveSearch',
    description: 'Reflective search',
    category: 'read',
  },
  queryExpansion: {
    name: 'queryExpansion',
    description: 'Query expansion',
    category: 'read',
  },
  getSynthesisPrompt: {
    name: 'getSynthesisPrompt',
    description: 'Get synthesis prompt',
    category: 'read',
  },
  retrieveWithReranking: {
    name: 'retrieveWithReranking',
    description: 'Retrieve with reranking',
    category: 'read',
  },
  getStats: { name: 'getStats', description: 'Get retrieval stats', category: 'read' },
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
